# 编程提示词：本地演示用 Mock 微信聊天记录功能

## 角色设定

你是一个谨慎的全栈编程助手。你正在修改一个已有项目，而不是从零创建项目。

项目根目录是：

```text
C:\Users\35696\Desktop\law-project
```

主要要修改的是这个子项目：

```text
C:\Users\35696\Desktop\law-project\lvzhijie
```

后端是 FastAPI + Pydantic，目录是：

```text
lvzhijie/backend
```

前端是 Vue 3 + TypeScript + Vite，目录是：

```text
lvzhijie/frontend
```

## 重要限制

必须遵守下面的限制：

1. 本功能只用于本地演示、开发、测试，不要连接真实微信，不要宣称数据来自真实微信。
2. 不要删除、重写或破坏现有功能。
3. 不要改变“微信接入”页面的整体布局。现有布局是左侧会话列表，右侧聊天记录和发送框，必须保留。
4. 可以增强聊天气泡内部的渲染能力，让它支持文本、图片、文件。
5. 必须支持多个会话。用户可以在微信接入页左侧切换不同会话，右侧必须渲染当前会话的聊天记录。
6. 必须在设置中增加一个“演示聊天记录”功能入口。进入后可以新建对话、选择对话、编辑假的聊天记录。
7. 演示聊天记录功能中必须有两个发送框：
   - 客户发送：保存为客户入站消息。
   - 我的发送：保存为本人出站消息。
8. 两个发送框都必须支持文本、图片、文件上传。
9. 发送后要保存到本地 JSON 文件和本地资源目录。
10. 保存后必须能在“微信接入”页面看到并正常渲染。
11. 不要引入数据库。继续使用本地 JSON 文件。
12. 不要引入新的大型前端 UI 库。
13. 不要把上传文件保存到前端目录。文件必须由后端保存到后端的 mock 数据目录。
14. 不要把真实绝对路径返回给前端。附件 URL 必须是可以被浏览器访问的 HTTP 路径。

## 当前项目已知结构

请先阅读这些文件，确认现状后再改：

```text
lvzhijie/backend/app/main.py
lvzhijie/backend/app/models.py
lvzhijie/backend/app/store.py
lvzhijie/backend/app/openclaw_adapter.py
lvzhijie/backend/app/data/store.json
lvzhijie/frontend/src/views/WechatView.vue
lvzhijie/frontend/src/views/OpenClawView.vue
lvzhijie/frontend/src/services/api.ts
lvzhijie/frontend/src/types/index.ts
lvzhijie/frontend/src/main.ts
lvzhijie/frontend/src/components/Sidebar.vue
lvzhijie/frontend/src/styles/app.css
```

当前已有接口大致如下：

```text
GET  /api/wechat/conversations
GET  /api/wechat/conversations/{conversation_id}/messages
POST /api/wechat/conversations/{conversation_id}/send
POST /api/openclaw/sync
GET  /api/openclaw/connection
PUT  /api/openclaw/connection
GET  /api/openclaw/status
```

当前前端微信接入页 `WechatView.vue` 已经能：

1. 加载会话列表。
2. 点击会话。
3. 加载该会话消息。
4. 发送文本消息。
5. 绑定案件或一键建案。

当前消息只渲染：

```vue
<div>{{ message.content }}</div>
```

你要把它增强为支持文本、图片、文件，但不要重做整个页面。

## 目标功能总览

实现一个本地 Mock 微信数据源。数据保存在后端目录：

```text
lvzhijie/backend/app/data/mock_wechat
```

目录结构必须是：

```text
mock_wechat/
  conversations.json
  messages/
    conv_demo.json
    conv_xxxxxx.json
  assets/
    上传的图片或文件
```

含义：

1. `conversations.json` 保存所有假会话。
2. `messages/{conversation_id}.json` 保存某个会话的所有消息。
3. `assets/` 保存上传的图片和文件。

微信接入页仍然调用原来的接口：

```text
GET /api/wechat/conversations
GET /api/wechat/conversations/{conversation_id}/messages
```

当 `openclaw_connection.transport_mode` 是 `"mock"` 时，后端应该从 `mock_wechat` 目录读取假数据，并返回给前端。

设置页新增“演示聊天记录”功能。用户可以在这个功能中创建假会话、用两个发送框添加消息、上传附件。添加后保存到 `mock_wechat` 目录，并同步到微信接入页可见。

## 数据结构设计

### conversations.json

文件路径：

```text
lvzhijie/backend/app/data/mock_wechat/conversations.json
```

格式示例：

```json
[
  {
    "id": "conv_demo",
    "openclaw_conversation_id": "mock_conv_demo",
    "contact_id": "contact_demo",
    "case_id": "case_demo",
    "status": "open",
    "auto_reply_source": "openclaw",
    "last_message_at": "2026-06-01T10:30:00+08:00",
    "unread_count": 1,
    "contact": {
      "id": "contact_demo",
      "openclaw_contact_id": "mock_contact_demo",
      "display_name": "张先生",
      "remark": "劳动争议咨询",
      "avatar_url": null,
      "last_seen_at": "2026-06-01T10:30:00+08:00"
    }
  }
]
```

规则：

1. 每个会话必须有唯一 `id`。
2. `contact` 必须存在。
3. `contact.display_name` 是前端显示的联系人名称。
4. `contact.remark` 是备注。
5. `last_message_at` 要在每次添加消息后更新。
6. `openclaw_conversation_id` 可以是假的，但必须稳定。
7. `auto_reply_source` 保持 `"openclaw"`，这样现有前端标签不用大改。

### 单个会话消息文件

文件路径示例：

```text
lvzhijie/backend/app/data/mock_wechat/messages/conv_demo.json
```

格式示例：

```json
[
  {
    "id": "msg_001",
    "conversation_id": "conv_demo",
    "sender": "wechat_user",
    "direction": "inbound",
    "type": "text",
    "content": "公司拖欠我两个月工资，还让我自己离职，我该怎么办？",
    "attachments": [],
    "status": "synced",
    "openclaw_message_id": null,
    "created_at": "2026-06-01T10:20:00+08:00",
    "raw_payload": null
  },
  {
    "id": "msg_002",
    "conversation_id": "conv_demo",
    "sender": "wechat_user",
    "direction": "inbound",
    "type": "image",
    "content": "这是工资流水截图。",
    "attachments": [
      {
        "name": "工资流水截图.png",
        "url": "/mock-wechat-assets/工资流水截图.png",
        "mime_type": "image/png",
        "size": 123456
      }
    ],
    "status": "synced",
    "openclaw_message_id": null,
    "created_at": "2026-06-01T10:25:00+08:00",
    "raw_payload": null
  },
  {
    "id": "msg_003",
    "conversation_id": "conv_demo",
    "sender": "owner",
    "direction": "outbound",
    "type": "file",
    "content": "我先看一下你发来的合同。",
    "attachments": [
      {
        "name": "劳动合同.pdf",
        "url": "/mock-wechat-assets/劳动合同.pdf",
        "mime_type": "application/pdf",
        "size": 456789
      }
    ],
    "status": "sent_via_openclaw",
    "openclaw_message_id": null,
    "created_at": "2026-06-01T10:30:00+08:00",
    "raw_payload": null
  }
]
```

消息字段规则：

1. `sender` 只能是：
   - `"wechat_user"`：客户。
   - `"owner"`：我。
   - `"openclaw_auto"`：自动回复。
   - `"system"`：系统。
2. `direction` 只能是：
   - `"inbound"`：客户发来。
   - `"outbound"`：我发出。
   - `"internal"`：内部消息。
3. 两个发送框只需要支持：
   - 客户发送：`sender = "wechat_user"`，`direction = "inbound"`，`status = "synced"`。
   - 我的发送：`sender = "owner"`，`direction = "outbound"`，`status = "sent_via_openclaw"`。
4. `type` 只能是：
   - `"text"`：只有文本。
   - `"image"`：只有图片或主要是图片。
   - `"file"`：只有文件或主要是文件。
   - `"mixed"`：文本 + 图片/文件混合。
5. `content` 必须保留，即使有附件也要有。没有文本时用空字符串。
6. `attachments` 必须是数组。没有附件时是 `[]`。
7. 每个附件必须有：
   - `name`
   - `url`
   - `mime_type`
   - `size`
8. 图片通过 `mime_type` 判断，`mime_type` 以 `"image/"` 开头就按图片渲染。
9. 非图片附件按文件卡片或链接渲染。

## 后端实现要求

### 1. 修改 models.py

文件：

```text
lvzhijie/backend/app/models.py
```

新增附件模型：

```python
class WechatAttachment(BaseModel):
    name: str
    url: str
    mime_type: str | None = None
    size: int | None = None
```

修改 `WechatMessage`：

```python
class WechatMessage(BaseModel):
    id: str = Field(default_factory=lambda: new_id("msg"))
    conversation_id: str
    sender: Literal["wechat_user", "openclaw_auto", "owner", "system"]
    direction: Literal["inbound", "outbound", "internal"]
    type: Literal["text", "image", "file", "mixed"] = "text"
    content: str
    attachments: list[WechatAttachment] = Field(default_factory=list)
    status: Literal[
        "synced",
        "openclaw_auto_replied",
        "draft",
        "sent_via_openclaw",
        "failed",
        "ignored",
    ] = "synced"
    openclaw_message_id: str | None = None
    created_at: str = Field(default_factory=now_iso)
    raw_payload: dict[str, Any] | None = None
```

注意：

1. `type` 和 `attachments` 必须有默认值，这样旧的 `store.json` 消息不会报错。
2. 不要删除已有字段。
3. 不要改 `content` 字段名，因为案件推理和搜索还依赖它。

### 2. 新建 mock_wechat_store.py

新建文件：

```text
lvzhijie/backend/app/mock_wechat_store.py
```

这个文件负责读写 `mock_wechat` 目录。

建议实现一个类：

```python
class MockWechatStore:
    def __init__(self, root: Path) -> None:
        ...
```

必须实现这些能力：

```python
list_conversations() -> list[dict[str, object]]
create_conversation(display_name: str, remark: str = "", avatar_url: str | None = None) -> dict[str, object]
update_conversation(conversation_id: str, payload: dict[str, object]) -> dict[str, object]
delete_conversation(conversation_id: str) -> bool
list_messages(conversation_id: str) -> list[dict[str, object]]
append_message(conversation_id: str, sender: str, content: str, attachments: list[dict[str, object]]) -> dict[str, object]
delete_message(conversation_id: str, message_id: str) -> bool
save_upload(upload: UploadFile) -> dict[str, object]
sync_to_json_store(store: JsonStore) -> None
```

实现细节：

1. 初始化时创建目录：

```text
mock_wechat/
mock_wechat/messages/
mock_wechat/assets/
```

2. 如果 `conversations.json` 不存在，创建一个默认会话，避免页面空白。
3. 如果某个会话没有消息文件，创建空数组文件。
4. 读 JSON 时，如果文件不存在或内容为空，返回空数组，不要让接口崩溃。
5. 写 JSON 时使用 `ensure_ascii=False` 和 `indent=2`。
6. 文件名要防止路径穿越。上传文件保存时必须只取安全文件名，不允许使用用户传入路径。
7. 上传文件如果重名，必须加唯一前缀，例如：

```text
asset_8f33aab991e2_劳动合同.pdf
```

8. 返回给前端的附件 URL 必须是：

```text
/mock-wechat-assets/{保存后的文件名}
```

9. `append_message` 要自动设置：
   - `id`
   - `conversation_id`
   - `direction`
   - `type`
   - `status`
   - `created_at`
   - `attachments`
10. `append_message` 根据 `sender` 判断方向：
   - `wechat_user` -> `inbound`
   - `owner` -> `outbound`
   - 其他 -> `internal`
11. `append_message` 根据内容和附件判断 `type`：
   - 无附件 -> `text`
   - 附件全部是图片，且文本为空或不重要 -> `image`
   - 附件存在且没有图片 -> `file`
   - 文本和附件都有，或图片文件混合 -> `mixed`
12. 每次添加消息后更新对应会话的 `last_message_at`。
13. `sync_to_json_store(store)` 要把 mock 数据同步到现有 `JsonStore` 的这些 key：
   - `wechat_contacts`
   - `wechat_conversations`
   - `wechat_messages`

`sync_to_json_store(store)` 的目的：

现有很多接口，例如绑定案件、一键建案、案件详情，仍然依赖 `store.json` 里的 `wechat_conversations` 和 `wechat_messages`。为了兼容旧逻辑，mock 文件是源数据，`store.json` 是镜像数据。每次读取 mock 会话或消息前，可以同步一次。

同步规则：

1. 不要删除非 mock 的历史数据，除非它的 id 和 mock 数据冲突。
2. 对 mock 会话、联系人、消息，用 id 覆盖更新。
3. 如果 mock 会话已有 `case_id`，同步到 `store.json`。
4. 如果 `store.json` 中某个同 id 会话绑定了 `case_id`，但 mock 文件里的 `case_id` 是空，可以保留 store 中的 `case_id`，避免绑定案件后丢失。

### 3. 修改 main.py

文件：

```text
lvzhijie/backend/app/main.py
```

#### 3.1 挂载静态资源

添加导入：

```python
from fastapi.staticfiles import StaticFiles
```

创建 mock store：

```python
from app.mock_wechat_store import MockWechatStore

mock_wechat = MockWechatStore(Path(__file__).parent / "data" / "mock_wechat")
```

挂载附件静态目录：

```python
app.mount(
    "/mock-wechat-assets",
    StaticFiles(directory=Path(__file__).parent / "data" / "mock_wechat" / "assets"),
    name="mock-wechat-assets",
)
```

注意：要确保目录在 mount 前已经创建。

#### 3.2 增加 helper

增加函数：

```python
def using_mock_wechat() -> bool:
    return connection().transport_mode == "mock"


def sync_mock_wechat_if_needed() -> None:
    if using_mock_wechat():
        mock_wechat.sync_to_json_store(store)
```

#### 3.3 修改已有微信接口

修改：

```python
@app.get("/api/wechat/conversations")
```

逻辑：

1. 如果是 mock 模式，先调用 `sync_mock_wechat_if_needed()`。
2. 然后继续使用现有逻辑从 `store` 返回会话列表。
3. 不要改前端调用路径。

修改：

```python
@app.get("/api/wechat/conversations/{conversation_id}/messages")
```

逻辑：

1. 如果是 mock 模式，先同步。
2. 然后继续从 `store` 返回该会话消息。
3. 返回消息必须按 `created_at` 排序。

修改：

```python
@app.post("/api/wechat/conversations/{conversation_id}/send")
```

逻辑：

1. 如果是 mock 模式，不要调用真实 OpenClaw。
2. 把这条消息追加到 `mock_wechat/messages/{conversation_id}.json`。
3. sender 用 `"owner"`。
4. content 用请求里的文本。
5. attachments 用空数组。
6. 同步到 `store`。
7. 返回新消息。
8. 如果不是 mock 模式，保留现有逻辑。

#### 3.4 修改 openclaw sync

修改：

```python
@app.post("/api/openclaw/sync")
```

逻辑：

1. 如果是 mock 模式：
   - 调用 `mock_wechat.sync_to_json_store(store)`。
   - 返回类似：

```python
{
    "ok": True,
    "sessions": 会话数量,
    "messages": 消息数量,
    "errors": [],
    "last_sync_at": now_iso(),
}
```

2. 如果不是 mock 模式，保留现有 OpenClaw 同步逻辑。

#### 3.5 新增设置页专用 API

新增接口：

```text
GET    /api/mock-wechat/conversations
POST   /api/mock-wechat/conversations
PUT    /api/mock-wechat/conversations/{conversation_id}
DELETE /api/mock-wechat/conversations/{conversation_id}

GET    /api/mock-wechat/conversations/{conversation_id}/messages
POST   /api/mock-wechat/conversations/{conversation_id}/messages
DELETE /api/mock-wechat/conversations/{conversation_id}/messages/{message_id}
```

`GET /api/mock-wechat/conversations`

返回 `conversations.json` 中的会话，格式要带 `contact`。

`POST /api/mock-wechat/conversations`

请求 JSON：

```json
{
  "display_name": "李女士",
  "remark": "合同纠纷咨询",
  "avatar_url": null
}
```

返回创建后的会话。

`PUT /api/mock-wechat/conversations/{conversation_id}`

可更新：

```json
{
  "display_name": "李女士",
  "remark": "合同纠纷咨询",
  "avatar_url": null,
  "case_id": null,
  "unread_count": 0
}
```

返回更新后的会话。

`DELETE /api/mock-wechat/conversations/{conversation_id}`

删除会话，并删除该会话消息文件。不要删除附件文件，因为附件可能被别的消息引用。返回：

```json
{ "ok": true }
```

`GET /api/mock-wechat/conversations/{conversation_id}/messages`

返回对应消息 JSON。

`POST /api/mock-wechat/conversations/{conversation_id}/messages`

必须使用 `multipart/form-data`，字段：

```text
sender = wechat_user 或 owner
content = 文本，可以为空
files = 一个或多个上传文件，可以没有
```

后端：

1. 保存上传文件到 `mock_wechat/assets/`。
2. 创建附件数组。
3. 追加消息到 `messages/{conversation_id}.json`。
4. 同步到 `store`。
5. 返回新消息。

如果 `content` 为空并且没有文件，返回 422。

`DELETE /api/mock-wechat/conversations/{conversation_id}/messages/{message_id}`

删除单条消息，返回：

```json
{ "ok": true }
```

删除消息时不删除附件文件。

## 前端实现要求

### 1. 修改 types/index.ts

文件：

```text
lvzhijie/frontend/src/types/index.ts
```

新增：

```ts
export type WechatAttachment = {
  name: string;
  url: string;
  mime_type?: string | null;
  size?: number | null;
};
```

修改 `WechatMessage`：

```ts
export type WechatMessage = {
  id: string;
  conversation_id: string;
  sender: "wechat_user" | "openclaw_auto" | "owner" | "system";
  direction: "inbound" | "outbound" | "internal";
  type?: "text" | "image" | "file" | "mixed";
  content: string;
  attachments?: WechatAttachment[];
  status: string;
  created_at: string;
};
```

注意：`type` 和 `attachments` 要是可选，兼容旧接口。

新增 mock 会话创建请求类型也可以，但不是必须。

### 2. 修改 services/api.ts

文件：

```text
lvzhijie/frontend/src/services/api.ts
```

保留现有 API，不要删。

新增：

```ts
mockWechatConversations: () => request<WechatConversation[]>("/api/mock-wechat/conversations"),
createMockWechatConversation: (payload: { display_name: string; remark?: string; avatar_url?: string | null }) =>
  request<WechatConversation>("/api/mock-wechat/conversations", {
    method: "POST",
    body: JSON.stringify(payload),
  }),
updateMockWechatConversation: (conversationId: string, payload: Record<string, unknown>) =>
  request<WechatConversation>(`/api/mock-wechat/conversations/${conversationId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  }),
deleteMockWechatConversation: (conversationId: string) =>
  request<Record<string, unknown>>(`/api/mock-wechat/conversations/${conversationId}`, {
    method: "DELETE",
  }),
mockWechatMessages: (conversationId: string) =>
  request<WechatMessage[]>(`/api/mock-wechat/conversations/${conversationId}/messages`),
createMockWechatMessage: (conversationId: string, form: FormData) =>
  request<WechatMessage>(`/api/mock-wechat/conversations/${conversationId}/messages`, {
    method: "POST",
    body: form,
  }),
deleteMockWechatMessage: (conversationId: string, messageId: string) =>
  request<Record<string, unknown>>(`/api/mock-wechat/conversations/${conversationId}/messages/${messageId}`, {
    method: "DELETE",
  }),
```

注意：

1. `createMockWechatMessage` 使用 `FormData`，不要手动设置 `"Content-Type"`。
2. 当前 `request` 函数已经能识别 `FormData`，不要破坏它。

### 3. 修改 WechatView.vue

文件：

```text
lvzhijie/frontend/src/views/WechatView.vue
```

只增强消息渲染，不要重写页面。

找到当前渲染消息的位置：

```vue
<div>{{ message.content }}</div>
<div class="message-meta">
  {{ senderLabel(message.sender) }} · {{ statusLabel(message.status) }}
</div>
```

替换为支持附件的渲染。

建议模板：

```vue
<div v-if="message.content" class="message-text">{{ message.content }}</div>
<div v-if="message.attachments?.length" class="message-attachments">
  <template v-for="attachment in message.attachments" :key="attachment.url">
    <a
      v-if="isImageAttachment(attachment)"
      :href="attachment.url"
      target="_blank"
      rel="noreferrer"
      class="message-image-link"
    >
      <img :src="attachment.url" :alt="attachment.name" class="message-image" />
    </a>
    <a
      v-else
      :href="attachment.url"
      target="_blank"
      rel="noreferrer"
      class="message-file"
    >
      <span class="message-file-name">{{ attachment.name }}</span>
      <span class="message-file-meta">{{ formatFileSize(attachment.size) }}</span>
    </a>
  </template>
</div>
<div class="message-meta">
  {{ senderLabel(message.sender) }} · {{ statusLabel(message.status) }}
</div>
```

在 `<script setup>` 中新增：

```ts
import type { WechatAttachment } from "@/types";

function isImageAttachment(attachment: WechatAttachment) {
  return attachment.mime_type?.startsWith("image/") || /\.(png|jpe?g|gif|webp|bmp|svg)$/i.test(attachment.name);
}

function formatFileSize(size?: number | null) {
  if (!size || size <= 0) return "文件";
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / 1024 / 1024).toFixed(1)} MB`;
}
```

修改搜索逻辑。当前搜索只搜 `message.content`。要加入附件名：

```ts
return messages.value.filter((message) => {
  const attachmentText = (message.attachments ?? []).map((item) => item.name).join(" ");
  return `${message.content} ${attachmentText}`.toLowerCase().includes(text);
});
```

### 4. 修改 app.css

文件：

```text
lvzhijie/frontend/src/styles/app.css
```

追加少量样式，不要大改整体设计。

建议加入：

```css
.message-text {
  white-space: pre-wrap;
  word-break: break-word;
}

.message-attachments {
  display: grid;
  gap: 6px;
  margin-top: 6px;
}

.message-image-link {
  display: inline-block;
  max-width: 240px;
}

.message-image {
  display: block;
  max-width: 240px;
  max-height: 220px;
  border-radius: 6px;
  border: 1px solid var(--border);
  object-fit: contain;
  background: white;
}

.message-file {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  max-width: 280px;
  min-height: 36px;
  padding: 7px 8px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: white;
  color: var(--text);
  text-decoration: none;
}

.message-file:hover {
  border-color: var(--border-strong);
  background: #f8fafc;
}

.message-file-name {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.message-file-meta {
  flex: 0 0 auto;
  color: var(--muted);
  font-size: 10px;
}
```

### 5. 新增 MockWechatView.vue

新建文件：

```text
lvzhijie/frontend/src/views/MockWechatView.vue
```

页面用途：设置中的演示聊天记录编辑器。

必须包含这些区域：

1. 顶部 `PageHeader`
   - 标题：`演示聊天记录`
   - 描述：`通过本地 JSON 和上传文件模拟微信会话，用于演示与测试。`
   - 按钮：
     - `同步到微信接入`
     - `打开微信接入`
2. 左侧会话列表
   - 显示所有假会话。
   - 点击后切换当前会话。
   - 选中样式复用 `list-item active`。
3. 新建对话表单
   - 客户名称。
   - 备注。
   - 新建按钮。
4. 右侧聊天预览
   - 显示当前会话消息。
   - 渲染方式要和 `WechatView.vue` 一致，支持文本、图片、文件。
   - 每条消息最好有删除按钮。
5. 两个发送框
   - 客户发送。
   - 我的发送。
   - 每个发送框包括：
     - 文本输入，建议用 textarea。
     - 文件上传 input，允许多文件。
     - 发送按钮。

发送框逻辑：

客户发送：

```ts
sender = "wechat_user"
```

我的发送：

```ts
sender = "owner"
```

上传文件：

```ts
const form = new FormData();
form.append("sender", sender);
form.append("content", content);
for (const file of files) {
  form.append("files", file);
}
await api.createMockWechatMessage(selectedId.value, form);
```

发送成功后：

1. 清空对应文本框。
2. 清空对应文件 input。可以给 input 绑定 `ref` 后手动设置 `value = ""`。
3. 重新加载当前会话消息。
4. 重新加载会话列表，因为 `last_message_at` 变了。

删除消息后也要重新加载消息。

如果没有选中会话，发送按钮禁用。

如果文本为空且没有文件，发送按钮禁用。

页面布局建议复用现有类：

```vue
<section class="page-content">
  <div class="split">
    <section class="panel">左侧会话和新建表单</section>
    <section class="panel">右侧预览和发送框</section>
  </div>
</section>
```

不要做花哨设计。保持和现有系统一致。

### 6. 修改 main.ts

文件：

```text
lvzhijie/frontend/src/main.ts
```

导入新页面：

```ts
import MockWechatView from "./views/MockWechatView.vue";
```

新增路由：

```ts
{ path: "/settings/mock-wechat", component: MockWechatView },
```

### 7. 修改 OpenClawView.vue

文件：

```text
lvzhijie/frontend/src/views/OpenClawView.vue
```

在现有设置页中添加一个 panel，作为入口。不要删除原来的配置表单。

建议添加：

```vue
<section class="panel">
  <h2 class="panel-title">演示聊天记录</h2>
  <p class="panel-subtitle">通过本地 JSON、图片和文件模拟微信会话，用于演示与测试。</p>
  <RouterLink class="button primary" to="/settings/mock-wechat">进入编辑器</RouterLink>
</section>
```

如果模板中使用 `RouterLink`，Vue 模板可以直接使用，不需要额外导入。

## 后端 API 细节

### CreateMockConversationRequest

可以在 `models.py` 新增请求模型：

```python
class MockConversationCreateRequest(BaseModel):
    display_name: str
    remark: str = ""
    avatar_url: str | None = None


class MockConversationUpdateRequest(BaseModel):
    display_name: str | None = None
    remark: str | None = None
    avatar_url: str | None = None
    case_id: str | None = None
    unread_count: int | None = None
```

或者把这两个模型放在 `main.py` 也可以，但推荐放在 `models.py`。

### POST mock message

FastAPI 接口写法参考：

```python
@app.post("/api/mock-wechat/conversations/{conversation_id}/messages")
async def create_mock_wechat_message(
    conversation_id: str,
    sender: str = Form(...),
    content: str = Form(default=""),
    files: list[UploadFile] = File(default=[]),
) -> WechatMessage:
    ...
```

注意：

1. 当前项目已经使用 `python-multipart`，可以处理文件上传。
2. 如果 `files` 默认值写法报类型问题，可以改用：

```python
files: list[UploadFile] | None = File(default=None)
```

然后内部：

```python
uploads = files or []
```

3. 校验 sender：

```python
if sender not in {"wechat_user", "owner"}:
    raise HTTPException(status_code=422, detail="sender must be wechat_user or owner")
```

4. 如果内容和文件都为空：

```python
if not content.strip() and not uploads:
    raise HTTPException(status_code=422, detail="Message content or files are required")
```

## 文件上传安全要求

保存上传文件时必须注意：

1. 不要使用上传文件的原始路径。
2. 只保留文件名。
3. 去掉危险字符，例如：
   - `/`
   - `\`
   - `:`
   - `*`
   - `?`
   - `"`
   - `<`
   - `>`
   - `|`
4. 文件名为空时用 `upload.bin`。
5. 给文件名加唯一前缀，避免覆盖。
6. 返回的附件对象示例：

```python
{
    "name": original_filename,
    "url": f"/mock-wechat-assets/{saved_filename}",
    "mime_type": upload.content_type,
    "size": len(content),
}
```

不要把本地绝对路径返回给前端。

## 兼容现有案件功能

必须保留这些功能：

1. 微信接入页会话列表。
2. 微信接入页切换会话。
3. 微信接入页搜索消息内容。
4. 微信接入页绑定已有案件。
5. 微信接入页一键建案。
6. 案件详情中显示绑定会话的消息。
7. 推理逻辑仍然可以读取 `message.content`。

为此：

1. 不要删除 `WechatMessage.content`。
2. mock 消息也要写入或同步到 `JsonStore` 的 `wechat_messages`。
3. mock 会话也要写入或同步到 `JsonStore` 的 `wechat_conversations`。
4. mock 联系人也要写入或同步到 `JsonStore` 的 `wechat_contacts`。

## 推荐实现顺序

请严格按顺序做：

### 第一步：后端模型兼容

1. 修改 `models.py`，增加 `WechatAttachment`。
2. 给 `WechatMessage` 增加 `type` 和 `attachments`。
3. 运行后端测试或至少启动导入检查，确保旧数据不报错。

### 第二步：Mock 数据读写

1. 新建 `mock_wechat_store.py`。
2. 实现目录初始化。
3. 实现读写 conversations。
4. 实现读写 messages。
5. 实现上传附件保存。
6. 实现同步到 `JsonStore`。

### 第三步：后端接口

1. 在 `main.py` 初始化 `mock_wechat`。
2. 挂载 `/mock-wechat-assets`。
3. 修改已有微信接口，使 mock 模式读取本地 JSON。
4. 新增 `/api/mock-wechat/...` 接口。
5. 修改 `/api/openclaw/sync` 的 mock 模式逻辑。

### 第四步：前端类型和 API

1. 修改 `types/index.ts`。
2. 修改 `services/api.ts`。

### 第五步：增强微信接入页渲染

1. 修改 `WechatView.vue`，让消息支持图片和文件。
2. 修改搜索逻辑，让搜索也能搜附件名。
3. 添加必要 CSS。

### 第六步：设置页编辑器

1. 新建 `MockWechatView.vue`。
2. 加路由 `/settings/mock-wechat`。
3. 在 `OpenClawView.vue` 添加入口 panel。

### 第七步：验证

必须验证：

1. 后端测试通过。
2. 前端构建通过。
3. 设置页可以新建会话。
4. 设置页客户发送文本后，微信接入页能看到。
5. 设置页我的发送文本后，微信接入页能看到并靠右显示。
6. 上传图片后，微信接入页能显示图片。
7. 上传 PDF 或其他文件后，微信接入页能显示文件链接。
8. 多个会话之间切换，消息不会串。
9. 点击“同步微信桥”在 mock 模式下不会报错。
10. 不在 mock 模式时，原 OpenClaw 逻辑仍然保留。

## 验证命令

后端：

```powershell
cd C:\Users\35696\Desktop\law-project\lvzhijie\backend
uv run pytest
```

如果没有 `uv`，尝试：

```powershell
cd C:\Users\35696\Desktop\law-project\lvzhijie\backend
python -m pytest
```

前端：

```powershell
cd C:\Users\35696\Desktop\law-project\lvzhijie\frontend
npm run build
```

启动前端：

```powershell
cd C:\Users\35696\Desktop\law-project\lvzhijie\frontend
npm run dev
```

启动后端：

```powershell
cd C:\Users\35696\Desktop\law-project\lvzhijie\backend
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

如果没有 `uv`：

```powershell
cd C:\Users\35696\Desktop\law-project\lvzhijie\backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## 手工测试流程

请按这个流程手工测试：

1. 打开系统设置或微信桥配置页。
2. 把传输模式改成“演示模式”。
3. 保存。
4. 进入“演示聊天记录”编辑器。
5. 新建一个对话：
   - 客户名称：`李女士`
   - 备注：`合同纠纷咨询`
6. 选中这个对话。
7. 在“客户发送”输入：

```text
你好，我想咨询一下合同违约的问题。
```

8. 点击发送。
9. 在“我的发送”输入：

```text
您好，请先把合同和对方违约的证据发我，我帮您初步梳理。
```

10. 点击发送。
11. 在“客户发送”上传一张图片，文本写：

```text
这是付款截图。
```

12. 点击发送。
13. 在“客户发送”上传一个 PDF 或 docx，文本写：

```text
这是合同文件。
```

14. 点击发送。
15. 打开“微信接入”页面。
16. 左侧必须能看到 `李女士` 会话。
17. 点击 `李女士`。
18. 右侧必须显示刚才的文本、图片、文件。
19. 图片必须直接显示缩略图。
20. 文件必须显示为可点击链接。
21. 再新建另一个对话，重复发送消息。
22. 在微信接入页切换两个会话，确认消息不会混在一起。

## 建议新增测试

后端建议新增测试文件：

```text
lvzhijie/backend/tests/test_mock_wechat.py
```

至少测试：

1. mock 模式下 `/api/openclaw/sync` 成功。
2. 可以创建 mock 会话。
3. 可以给 mock 会话添加客户消息。
4. 添加消息后 `/api/wechat/conversations` 能看到会话。
5. 添加消息后 `/api/wechat/conversations/{id}/messages` 能看到消息。
6. 文件上传后附件有 URL，且 URL 以 `/mock-wechat-assets/` 开头。
7. 多个会话的消息互不影响。

测试中注意：

当前 `tests/test_mvp_flows.py` 里会替换：

```python
main.store = JsonStore(tmp_path / "store.json")
```

你新增测试时也应该让 mock 数据目录使用临时目录，避免污染真实 `app/data/mock_wechat`。如果 `main.mock_wechat` 是全局变量，测试里可以替换：

```python
main.mock_wechat = MockWechatStore(tmp_path / "mock_wechat")
```

## 不要做的事情

下面这些事不要做：

1. 不要把微信接入页重写成新的聊天应用。
2. 不要删除 OpenClaw 真实网关逻辑。
3. 不要把 mock 数据混在前端 `src` 目录。
4. 不要用 localStorage 保存聊天记录。
5. 不要只支持单会话。
6. 不要只支持文本。
7. 不要把图片转 base64 存进 JSON。
8. 不要把文件内容存进 JSON。
9. 不要返回本地磁盘路径给前端。
10. 不要改掉 `content` 字段。
11. 不要让上传文件覆盖已有文件。
12. 不要在非 mock 模式下强制读取 mock 数据。
13. 不要让空消息保存成功。

## 完成标准

完成后必须满足：

1. 设置里有入口进入演示聊天记录编辑器。
2. 编辑器可以新建多个对话。
3. 每个对话都有独立消息文件。
4. 编辑器有两个发送框：客户发送、我的发送。
5. 两个发送框都支持文本、图片、文件。
6. 数据保存到后端 `mock_wechat` 目录。
7. 微信接入页保持原布局。
8. 微信接入页可以切换多个会话。
9. 微信接入页能渲染文本、图片、文件。
10. mock 模式下点击“同步微信桥”能把 JSON 数据同步到页面。
11. 现有案件绑定、一键建案功能不被破坏。
12. 前端 `npm run build` 通过。
13. 后端测试通过或至少新增 mock 测试通过。

## 最终回复要求

完成代码后，最终回复必须包含：

1. 修改了哪些文件。
2. 新增了哪些接口。
3. mock JSON 数据目录在哪里。
4. 如何手工测试。
5. 已运行哪些测试命令。
6. 如果有没完成或没验证的地方，必须明确说明。

