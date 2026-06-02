# 律智界文件版本控制功能改进实施提示词

你是一个本地代码修改模型。你的任务是改进 `lvzhijie` 项目的“法律文件版本控制”功能。你必须严格按照本文档执行，不要自行发挥，不要改动无关功能。

## 0. 项目基本信息

项目根目录：

```text
C:\Users\35696\Desktop\law-project\lvzhijie
```

后端：

```text
C:\Users\35696\Desktop\law-project\lvzhijie\backend
```

前端：

```text
C:\Users\35696\Desktop\law-project\lvzhijie\frontend
```

技术栈：

- 后端：FastAPI + Pydantic + JSON 文件存储 + python-docx
- 前端：Vue 3 + TypeScript + Vite
- 当前存储文件：`backend/app/data/store.json`
- 当前后端主文件：`backend/app/main.py`
- 当前后端模型文件：`backend/app/models.py`
- 当前 diff 逻辑文件：`backend/app/diffing.py`
- 当前前端文件版本页面：`frontend/src/views/DocumentsView.vue`
- 当前前端 API 封装：`frontend/src/services/api.ts`
- 当前前端类型定义：`frontend/src/types/index.ts`
- 当前前端全局样式：`frontend/src/styles/app.css`

## 1. 总目标

把当前“单文件线性版本历史”升级为“类似 Git 的文件库版本控制”。

必须实现以下功能：

1. 文件库页面可以上传新的文件，上传后自动创建新的文件库。
2. 每个新文件库必须自动创建默认分支 `main`，初始上传文件成为 `main` 分支的第一个版本。
3. 进入一个文件库后，可以从任意已有版本创建新分支。
4. 创建分支时用户可以自定义分支名称。
5. 可以向指定分支上传新版本文件。
6. 版本之间可以任意对比，包括同分支版本对比和跨分支版本对比。
7. 差异显示必须继续使用红色标记删除内容、绿色标记新增内容。
8. Word 导出必须支持导出带红色/绿色差异标记的 Word 文件。
9. 文件库中的分支和版本必须像 VSCode 资源管理器一样提供树状总览。
10. 版本差异区域必须新增“AI 分析”功能：
    - 审查当前两个版本差异中可能存在歧义的地方。
    - 提示两个法律文件版本差异中可能存在的风险。
    - 特别关注“暗改条款表述方式”“弱化责任”“改变期限”“改变管辖/仲裁”“改变付款/违约/解除/保密”等风险。
11. 旧功能不能损坏：
    - `/api/documents`
    - `/api/documents/upload`
    - `/api/documents/{document_id}`
    - `/api/documents/{document_id}/diff`
    - `/api/documents/{document_id}/export.docx`
    - 案件详情页上传文件功能

## 2. 禁止事项

禁止做以下事情：

1. 不要重构整个项目。
2. 不要把 JSON 存储改成数据库。
3. 不要删除现有接口。
4. 不要删除现有字段。
5. 不要删除现有测试。
6. 不要改微信、案件、推理、智能体、OpenClaw 等无关功能。
7. 不要改 `mission-control` 目录。
8. 不要引入大型新前端框架。
9. 不要改变当前路由结构，`/documents` 仍然是文件版本控制页面。
10. 不要依赖真实外部 LLM 才能让测试通过。AI 接口必须有规则降级逻辑。

## 3. 当前已有功能说明

当前已有功能是线性的：

- `LegalDocument` 表示文件。
- `LegalDocumentRevision` 表示版本。
- 每个版本只有 `version_number`，没有分支。
- 上传新文件会创建 `LegalDocument` 和第一个 `LegalDocumentRevision`。
- 上传新版本会给该文件追加一个 revision。
- diff 使用 `backend/app/diffing.py` 的 `build_char_diff()` 和 `build_paragraph_diff()`。
- 风险提示使用 `summarize_legal_risks()` 的关键词规则。
- Word 导出只导出当前最新版本纯文本，不包含红绿 diff。

你要在此基础上扩展，不要推翻重写。

## 4. 后端数据模型改造

修改文件：

```text
backend/app/models.py
```

### 4.1 新增模型 `LegalDocumentBranch`

在 `LegalDocumentRevision` 附近新增：

```python
class LegalDocumentBranch(BaseModel):
    id: str = Field(default_factory=lambda: new_id("branch"))
    document_id: str
    name: str
    head_revision_id: str | None = None
    base_revision_id: str | None = None
    is_default: bool = False
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)
```

字段含义：

- `id`：分支 ID。
- `document_id`：所属文件库 ID。
- `name`：分支名称，例如 `main`、`client-edits`、`lawyer-review`。
- `head_revision_id`：该分支当前最新版本 ID。
- `base_revision_id`：创建该分支时所基于的版本 ID。
- `is_default`：是否默认分支。每个文件库只能有一个默认分支，默认名称必须是 `main`。
- `created_at`：创建时间。
- `updated_at`：更新时间。

### 4.2 扩展 `LegalDocument`

当前模型大致是：

```python
class LegalDocument(BaseModel):
    id: str = Field(default_factory=lambda: new_id("doc"))
    case_id: str | None = None
    title: str
    document_type: Literal["contract", "letter", "pleading", "evidence", "other"] = "other"
    current_revision_id: str | None = None
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)
```

新增字段：

```python
    default_branch_id: str | None = None
```

要求：

- 不能删除 `current_revision_id`，旧代码还会用到。
- `current_revision_id` 应保持等于默认分支 `main` 的 `head_revision_id`。

### 4.3 扩展 `LegalDocumentRevision`

当前模型大致是：

```python
class LegalDocumentRevision(BaseModel):
    id: str = Field(default_factory=lambda: new_id("rev"))
    document_id: str
    version_number: int
    content_text: str
    source_filename: str | None = None
    author_type: Literal["owner", "agent", "import"] = "owner"
    change_summary: str = ""
    created_at: str = Field(default_factory=now_iso)
```

新增字段：

```python
    branch_id: str | None = None
    parent_revision_id: str | None = None
    created_from_revision_id: str | None = None
    short_hash: str | None = None
```

字段含义：

- `branch_id`：版本所属分支。
- `parent_revision_id`：当前版本的父版本。上传新版本时，父版本应为该分支上传前的 HEAD。
- `created_from_revision_id`：如果这是某个分支创建后的第一个提交，可以记录从哪个版本派生；一般等于 `parent_revision_id`。
- `short_hash`：模拟 Git commit hash，使用 revision ID 的后 7 位或根据内容生成短 hash。推荐简单实现：创建 revision 后设置为 `revision.id.replace("rev_", "")[:7]`。

注意：

- 保留 `version_number`，用于兼容旧列表显示。
- 新功能的版本关系以 `branch_id` 和 `parent_revision_id` 为准。

### 4.4 新增模型 `LegalDocumentTreeNode`

新增用于 API 返回树状总览：

```python
class LegalDocumentTreeNode(BaseModel):
    revision: LegalDocumentRevision
    children: list["LegalDocumentTreeNode"] = Field(default_factory=list)
```

如果 Pydantic 前向引用有问题，可以不使用这个模型，直接返回普通 `dict`。

### 4.5 新增模型 `LegalDocumentAnalysis`

新增 AI 分析结果模型：

```python
class LegalDocumentAnalysis(BaseModel):
    id: str = Field(default_factory=lambda: new_id("analysis"))
    document_id: str
    base_revision_id: str
    target_revision_id: str
    source: Literal["llm", "rule_fallback"] = "rule_fallback"
    risk_level: Literal["low", "medium", "high"] = "medium"
    ambiguities: list[str] = Field(default_factory=list)
    stealth_changes: list[str] = Field(default_factory=list)
    risk_points: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    manual_review_checklist: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=now_iso)
```

字段含义：

- `source`：`llm` 表示成功调用大模型；`rule_fallback` 表示没有 key 或调用失败后使用规则兜底。
- `risk_level`：整体风险等级。
- `ambiguities`：可能存在歧义的文本变化。
- `stealth_changes`：疑似暗改或弱化条款的变化。
- `risk_points`：法律风险点。
- `suggestions`：修改建议。
- `manual_review_checklist`：人工复核清单。

### 4.6 新增请求模型

新增：

```python
class BranchCreateRequest(BaseModel):
    name: str
    base_revision_id: str


class BranchRevisionCreateRequest(BaseModel):
    content_text: str
    source_filename: str | None = None
    author_type: LegalDocumentRevision.model_fields["author_type"].annotation = "owner"
    change_summary: str = ""
```

## 5. JSON 存储结构

修改文件：

```text
backend/app/seed.py
backend/app/store.py
```

### 5.1 seed 数据必须包含新表

在 `build_seed_data()` 返回值中增加：

```python
"legal_document_branches": [main_branch.model_dump()],
"legal_document_analyses": [],
```

对于 demo 文档：

- 创建一个 `main_branch`。
- `main_branch.document_id = document.id`
- `main_branch.name = "main"`
- `main_branch.is_default = True`
- `main_branch.base_revision_id = revisions[0].id`
- `main_branch.head_revision_id = revisions[-1].id`
- `document.default_branch_id = main_branch.id`
- `document.current_revision_id = revisions[-1].id`
- 每个 demo revision 的 `branch_id = main_branch.id`
- 第一个 demo revision 的 `parent_revision_id = None`
- 第二个 demo revision 的 `parent_revision_id = 第一个 revision.id`

### 5.2 JsonStore.normalize 必须兼容旧 store.json

修改：

```text
backend/app/store.py
```

在 `normalize()` 中确保：

1. 如果缺少 `legal_document_branches`，创建空列表。
2. 如果缺少 `legal_document_analyses`，创建空列表。
3. 对每个 `legal_documents` 中的文档：
   - 如果没有 `default_branch_id`，自动创建 `main` 分支。
   - 查找该文档所有 `legal_document_revisions`。
   - 按 `version_number` 排序。
   - 给没有 `branch_id` 的 revision 设置为该 `main` 分支 ID。
   - 给没有 `parent_revision_id` 的 revision 设置父版本：
     - 第一个版本为 `None`
     - 后续版本为前一个版本 ID
   - 给没有 `short_hash` 的 revision 设置短 hash。
   - 设置 `main.head_revision_id` 为最后一个 revision ID。
   - 设置 `document.current_revision_id` 为最后一个 revision ID。
   - 设置 `document.default_branch_id` 为 main 分支 ID。

注意：

- 不要重复创建多个 `main` 分支。
- 如果已有分支，不要覆盖。
- normalize 完成后如果有修改，调用 `self.save()`。

## 6. 后端工具函数

修改文件：

```text
backend/app/main.py
```

### 6.1 import 新模型

从 `app.models` 导入：

```python
LegalDocumentBranch
LegalDocumentAnalysis
BranchCreateRequest
BranchRevisionCreateRequest
```

### 6.2 创建默认分支函数

新增函数：

```python
def create_default_branch_for_document(document: LegalDocument, first_revision: LegalDocumentRevision) -> LegalDocumentBranch:
    branch = LegalDocumentBranch(
        document_id=document.id,
        name="main",
        head_revision_id=first_revision.id,
        base_revision_id=first_revision.id,
        is_default=True,
    )
    first_revision.branch_id = branch.id
    first_revision.parent_revision_id = None
    first_revision.created_from_revision_id = None
    first_revision.short_hash = make_revision_short_hash(first_revision)
    document.default_branch_id = branch.id
    document.current_revision_id = first_revision.id
    store.add("legal_document_branches", branch)
    return branch
```

### 6.3 短 hash 函数

新增：

```python
def make_revision_short_hash(revision: LegalDocumentRevision) -> str:
    return revision.id.replace("rev_", "")[:7]
```

如果 revision 已有 `short_hash`，不要覆盖。

### 6.4 查找文档分支

新增：

```python
def document_branches(document_id: str) -> list[LegalDocumentBranch]:
    return sorted(
        store.filter("legal_document_branches", LegalDocumentBranch, document_id=document_id),
        key=lambda item: (not item.is_default, item.name.lower(), item.created_at),
    )
```

### 6.5 查找分支

新增：

```python
def get_document_branch(document_id: str, branch_id: str) -> LegalDocumentBranch:
    branch = store.get("legal_document_branches", branch_id, LegalDocumentBranch)
    if not branch or branch.document_id != document_id:
        raise HTTPException(status_code=404, detail="Branch not found")
    return branch
```

### 6.6 创建 revision 的统一函数

新增：

```python
def create_revision_on_branch(
    *,
    document: LegalDocument,
    branch: LegalDocumentBranch,
    content_text: str,
    source_filename: str | None,
    author_type: str,
    change_summary: str,
) -> LegalDocumentRevision:
    revisions = store.filter("legal_document_revisions", LegalDocumentRevision, document_id=document.id)
    parent_id = branch.head_revision_id
    revision = LegalDocumentRevision(
        document_id=document.id,
        version_number=len(revisions) + 1,
        content_text=content_text,
        source_filename=source_filename,
        author_type=author_type,
        change_summary=change_summary,
        branch_id=branch.id,
        parent_revision_id=parent_id,
        created_from_revision_id=parent_id,
    )
    revision.short_hash = make_revision_short_hash(revision)
    branch.head_revision_id = revision.id
    branch.updated_at = now_iso()
    document.updated_at = now_iso()
    if branch.is_default:
        document.current_revision_id = revision.id
    store.add("legal_document_revisions", revision)
    store.update("legal_document_branches", branch)
    store.update("legal_documents", document)
    return revision
```

注意：

- 这个函数用于“手动新增版本”和“上传新版本”。
- 不要让同一个 revision 同时属于多个分支。

### 6.7 删除文件时级联删除新表

修改现有 `delete_document_rows(document_id)`：

必须删除：

```python
store.remove_where("legal_document_revisions", lambda row: row.get("document_id") == document_id)
store.remove_where("legal_document_diffs", lambda row: row.get("document_id") == document_id)
store.remove_where("legal_document_branches", lambda row: row.get("document_id") == document_id)
store.remove_where("legal_document_analyses", lambda row: row.get("document_id") == document_id)
store.delete("legal_documents", document_id)
```

## 7. 后端接口设计

所有接口都在：

```text
backend/app/main.py
```

### 7.1 保留 `GET /api/documents`

现有接口保留。

返回 `list[LegalDocument]`。

### 7.2 保留并增强 `POST /api/documents`

现有 JSON 创建文档接口保留。

处理逻辑改为：

1. 创建 `LegalDocument`。
2. 创建第一个 `LegalDocumentRevision`。
3. 调用 `create_default_branch_for_document(document, revision)`。
4. 保存 document、revision、branch。

注意：

- 原接口仍返回 `LegalDocument`。
- 不要改变请求体。

### 7.3 保留并增强 `POST /api/documents/upload`

请求：

`multipart/form-data`

字段：

- `file`: 文件，必填，支持 `.txt`、`.md`、`.docx`
- `title`: 可选
- `case_id`: 可选
- `document_type`: 可选，默认 `other`
- `change_summary`: 可选，默认 `Initial upload`

处理逻辑：

1. 读取文件文本。
2. 创建 `LegalDocument`。
3. 创建第一个 `LegalDocumentRevision`。
4. 创建默认分支 `main`。
5. 保存所有数据。
6. 返回 `LegalDocument`。

### 7.4 修改 `GET /api/documents/{document_id}`

当前返回：

```json
{
  "document": {},
  "revisions": []
}
```

必须增强为：

```json
{
  "document": {},
  "branches": [],
  "revisions": []
}
```

兼容要求：

- 前端旧代码使用 `detail.revisions`，必须继续存在。
- `branches` 新增即可。

排序：

- `branches`：默认分支优先，然后按名称。
- `revisions`：按 `version_number` 升序。

### 7.5 新增 `GET /api/documents/{document_id}/tree`

用途：返回 VSCode 风格树状总览所需数据。

返回示例：

```json
{
  "document": {
    "id": "doc_xxx",
    "title": "合同"
  },
  "branches": [
    {
      "id": "branch_xxx",
      "document_id": "doc_xxx",
      "name": "main",
      "head_revision_id": "rev_2",
      "base_revision_id": "rev_1",
      "is_default": true,
      "created_at": "...",
      "updated_at": "...",
      "revisions": [
        {
          "id": "rev_1",
          "label": "v1 abc1234 初始版本",
          "version_number": 1,
          "short_hash": "abc1234",
          "parent_revision_id": null,
          "change_summary": "初始版本",
          "source_filename": "contract-v1.docx",
          "created_at": "..."
        },
        {
          "id": "rev_2",
          "label": "v2 def4567 上传新版本",
          "version_number": 2,
          "short_hash": "def4567",
          "parent_revision_id": "rev_1",
          "change_summary": "上传新版本",
          "source_filename": "contract-v2.docx",
          "created_at": "..."
        }
      ]
    }
  ]
}
```

实现规则：

- 每个 branch 下只返回属于该 branch 的 revisions。
- branch 内 revisions 按 `version_number` 升序。
- `label` 在后端生成，格式必须是：

```text
v{version_number} {short_hash} {change_summary}
```

- 如果 `change_summary` 为空，使用 `"无版本说明"`。

### 7.6 新增 `POST /api/documents/{document_id}/branches`

用途：从某个版本创建分支。

请求 JSON：

```json
{
  "name": "client-edits",
  "base_revision_id": "rev_xxx"
}
```

校验：

1. 文档必须存在，否则 404。
2. `name` 去掉首尾空格后不能为空，否则 422。
3. `name` 只能包含：
   - 中文
   - 英文字母
   - 数字
   - 下划线 `_`
   - 中划线 `-`
   - 斜杠 `/`
4. 同一文档下分支名不能重复，否则 409。
5. `base_revision_id` 必须属于该 document，否则 404。

处理：

1. 创建 `LegalDocumentBranch`。
2. `head_revision_id = base_revision_id`
3. `base_revision_id = base_revision_id`
4. `is_default = False`
5. 保存。
6. 记录 activity。
7. 返回 branch。

注意：

- 创建分支时不要复制 revision。
- 分支刚创建时，HEAD 指向已有 base revision。
- 之后向该分支上传新版本，新 revision 的 `parent_revision_id` 才是 base revision。

### 7.7 保留 `POST /api/documents/{document_id}/revisions`

兼容旧接口。

处理规则：

- 如果没有传 branch，就默认提交到默认分支 `main`。
- 使用 `create_revision_on_branch()`。
- 返回 revision。

### 7.8 保留 `POST /api/documents/{document_id}/revisions/upload`

兼容旧接口。

处理规则：

- 默认上传到默认分支 `main`。
- 使用 `create_revision_on_branch()`。
- 返回 revision。

### 7.9 新增 `POST /api/documents/{document_id}/branches/{branch_id}/revisions`

用途：向指定分支手动提交文本版本。

请求 JSON：

```json
{
  "content_text": "新版本文本",
  "source_filename": null,
  "author_type": "owner",
  "change_summary": "客户修改付款期限"
}
```

处理：

1. 校验文档存在。
2. 校验分支属于该文档。
3. `content_text` 不能为空，否则 422。
4. 调用 `create_revision_on_branch()`。
5. 返回 revision。

### 7.10 新增 `POST /api/documents/{document_id}/branches/{branch_id}/revisions/upload`

用途：向指定分支上传文件版本。

请求 `multipart/form-data`：

- `file`：必填
- `change_summary`：可选，默认 `"Uploaded revision"`

处理：

1. 校验文档存在。
2. 校验分支属于该文档。
3. 读取文件文本。
4. 文本为空则 422。
5. 调用 `create_revision_on_branch()`，`author_type="import"`。
6. 返回 revision。

### 7.11 修改 `DELETE /api/documents/{document_id}/revisions/{revision_id}`

当前删除 revision 会重新编号。新逻辑必须谨慎。

为了避免破坏分支树，建议实现规则：

1. 如果 revision 被任何分支的 `head_revision_id` 引用，则不允许删除，返回 409，提示 `"Cannot delete branch head revision"`。
2. 如果 revision 被任何其他 revision 的 `parent_revision_id` 引用，则不允许删除，返回 409，提示 `"Cannot delete revision with children"`。
3. 只有叶子 revision 才能删除。
4. 删除后删除相关 diff 和 analysis。
5. 不要重新写乱父子关系。
6. 可以保留旧的 `version_number` 不连续，不强制重新编号。

如果你为了兼容现有测试必须重新编号，只能在不影响父子关系时重新编号。

### 7.12 保留并增强 `GET /api/documents/{document_id}/diff`

请求 query：

- `base_revision_id`
- `target_revision_id`

处理：

1. 文档必须存在。
2. 两个 revision 必须存在并且都属于该文档。
3. 如果没有传参数，默认比较默认分支的倒数第二个版本和 HEAD。
4. 可以跨分支比较，只要两个 revision 属于同一 document。
5. 继续返回 `LegalDocumentDiff`。

### 7.13 新增 `GET /api/documents/{document_id}/diff/export.docx`

用途：导出带红绿标记的差异 Word。

请求 query：

- `base_revision_id`：必填
- `target_revision_id`：必填

响应：

```text
Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document
Content-Disposition: attachment; filename="legal-document-diff-{document_id}.docx"
```

Word 内容要求：

1. 标题：`{document.title} - 版本差异`
2. 第一段：显示基准版本和目标版本：
   - `基准版本：v{base.version_number} {base.short_hash} {base.change_summary}`
   - `目标版本：v{target.version_number} {target.short_hash} {target.change_summary}`
3. “逐字差异”章节：
   - equal：普通黑色文字。
   - insert：文字底色绿色。
   - delete：文字底色红色 + 删除线。
4. “段落变化”章节：
   - 新增段落：绿色底色。
   - 删除段落：红色底色 + 删除线。
   - 替换段落：先写“原文：”红色删除线，再写“改为：”绿色。
5. “风险提示”章节：
   - 写入 `diff.risk_summary`。

实现可以使用 `python-docx`：

```python
run.font.color.rgb = RGBColor(22, 101, 52)  # green
run.font.color.rgb = RGBColor(153, 27, 27)  # red
run.font.strike = True
```

需要导入：

```python
from docx.shared import RGBColor
```

### 7.14 新增 `POST /api/documents/{document_id}/diff/analyze`

用途：AI 分析两个版本的法律风险。

请求 JSON：

```json
{
  "base_revision_id": "rev_xxx",
  "target_revision_id": "rev_yyy"
}
```

如果不想新增请求模型，也可以用 Query 参数，但前端必须按你的实现调用。建议用 JSON body。

响应：`LegalDocumentAnalysis`

处理步骤：

1. 校验文档存在。
2. 校验两个 revision 存在且属于该文档。
3. 如果之前已经分析过同一组 `document_id + base_revision_id + target_revision_id`，直接返回最新一条缓存结果。
4. 生成 diff，拿到 `segments`、`paragraph_changes`、`risk_summary`。
5. 调用大模型。
6. 如果没有 API key 或调用失败，返回规则兜底结果，`source="rule_fallback"`。
7. 保存到 `legal_document_analyses`。
8. 返回分析结果。

使用的环境变量：

```text
LVZHIJIE_LLM_API_KEY
OPENAI_API_KEY
LVZHIJIE_LLM_BASE_URL
OPENAI_BASE_URL
LVZHIJIE_LLM_MODEL
OPENAI_MODEL
```

优先级：

```python
api_key = os.getenv("LVZHIJIE_LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
base_url = (os.getenv("LVZHIJIE_LLM_BASE_URL") or os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
model = os.getenv("LVZHIJIE_LLM_MODEL") or os.getenv("OPENAI_MODEL") or "gpt-4o-mini"
```

请求大模型接口：

```text
POST {base_url}/chat/completions
```

请求体：

```json
{
  "model": "...",
  "messages": [
    {
      "role": "system",
      "content": "你是资深中国律师，专门审查合同版本差异、暗改风险和歧义条款。只能输出 JSON。"
    },
    {
      "role": "user",
      "content": "..."
    }
  ],
  "temperature": 0.2
}
```

Prompt 内容必须包含：

```text
请分析两个法律文件版本之间的差异。
只能输出 JSON 对象，不要输出 Markdown。
JSON 字段必须包含：
- risk_level: low / medium / high
- ambiguities: 字符串数组，列出可能存在歧义的变化
- stealth_changes: 字符串数组，列出疑似暗改、弱化责任、扩大免责、改变期限、改变争议解决方式的变化
- risk_points: 字符串数组，列出法律风险点
- suggestions: 字符串数组，列出修改或谈判建议
- manual_review_checklist: 字符串数组，列出人工必须复核的问题

文件标题：
{document.title}

基准版本：
v{base.version_number} {base.change_summary}

目标版本：
v{target.version_number} {target.change_summary}

段落变化：
{paragraph_changes_text}

逐字变化摘要：
{changed_text}
```

兜底逻辑：

如果没有 key 或失败，返回：

```python
LegalDocumentAnalysis(
    document_id=document.id,
    base_revision_id=base.id,
    target_revision_id=target.id,
    source="rule_fallback",
    risk_level="medium",
    ambiguities=["发现文本变化，请人工核对是否影响权利义务、履行期限或争议解决。"],
    stealth_changes=[],
    risk_points=diff.risk_summary,
    suggestions=["建议逐条核对红色删除和绿色新增内容，确认是否改变双方实质权利义务。"],
    manual_review_checklist=[
        "核对付款金额、付款期限和付款条件是否变化。",
        "核对违约责任、赔偿上限和免责条款是否变化。",
        "核对解除条件、通知期限和争议解决条款是否变化。",
    ],
)
```

## 8. diffing.py 改造

修改文件：

```text
backend/app/diffing.py
```

现有函数保留：

- `build_char_diff`
- `build_paragraph_diff`
- `summarize_legal_risks`

可以新增：

```python
def build_changed_text_for_analysis(base: str, target: str, limit: int = 6000) -> str:
    ...
```

要求：

- 只提取变化附近上下文。
- 不要把超长全文直接发给大模型。
- 输出最多 `limit` 字符。

可以增强 `LEGAL_RISK_KEYWORDS`，加入：

```python
"期限": "期限条款发生变化，需要核对是否改变履行、通知、解除或追责节点。",
"通知": "通知方式或通知期限发生变化，可能影响送达和违约起算。",
"赔偿": "赔偿条款发生变化，需要关注赔偿范围、上限和证明责任。",
"免责": "免责或限责条款发生变化，可能削弱追责空间。",
"知识产权": "知识产权归属或授权范围发生变化，需要核对权利转让和使用限制。",
"个人信息": "个人信息或隐私条款发生变化，需要关注合规义务和授权范围。",
```

## 9. 前端类型定义

修改文件：

```text
frontend/src/types/index.ts
```

新增类型：

```ts
export type LegalDocumentBranch = {
  id: string;
  document_id: string;
  name: string;
  head_revision_id?: string | null;
  base_revision_id?: string | null;
  is_default: boolean;
  created_at: string;
  updated_at: string;
};
```

扩展 `LegalDocument`：

```ts
default_branch_id?: string | null;
```

扩展 `LegalDocumentRevision`：

```ts
branch_id?: string | null;
parent_revision_id?: string | null;
created_from_revision_id?: string | null;
short_hash?: string | null;
```

新增：

```ts
export type LegalDocumentTreeRevision = {
  id: string;
  label: string;
  version_number: number;
  short_hash?: string | null;
  parent_revision_id?: string | null;
  change_summary: string;
  source_filename?: string | null;
  created_at: string;
};

export type LegalDocumentTreeBranch = LegalDocumentBranch & {
  revisions: LegalDocumentTreeRevision[];
};

export type LegalDocumentTree = {
  document: LegalDocument;
  branches: LegalDocumentTreeBranch[];
};

export type LegalDocumentAnalysis = {
  id: string;
  document_id: string;
  base_revision_id: string;
  target_revision_id: string;
  source: "llm" | "rule_fallback";
  risk_level: "low" | "medium" | "high";
  ambiguities: string[];
  stealth_changes: string[];
  risk_points: string[];
  suggestions: string[];
  manual_review_checklist: string[];
  created_at: string;
};
```

扩展 `LegalDocumentDiff` 不强制新增字段。

## 10. 前端 API 封装

修改文件：

```text
frontend/src/services/api.ts
```

新增 import 类型：

```ts
LegalDocumentBranch,
LegalDocumentTree,
LegalDocumentAnalysis,
```

修改 `documentDetail` 返回类型：

```ts
documentDetail: (documentId: string) =>
  request<{ document: LegalDocument; branches: LegalDocumentBranch[]; revisions: LegalDocumentRevision[] }>(
    `/api/documents/${documentId}`,
  ),
```

新增：

```ts
documentTree: (documentId: string) =>
  request<LegalDocumentTree>(`/api/documents/${documentId}/tree`),

createDocumentBranch: (documentId: string, payload: { name: string; base_revision_id: string }) =>
  request<LegalDocumentBranch>(`/api/documents/${documentId}/branches`, {
    method: "POST",
    body: JSON.stringify(payload),
  }),

createBranchRevision: (
  documentId: string,
  branchId: string,
  payload: { content_text: string; change_summary?: string; source_filename?: string | null },
) =>
  request<LegalDocumentRevision>(`/api/documents/${documentId}/branches/${branchId}/revisions`, {
    method: "POST",
    body: JSON.stringify(payload),
  }),

uploadBranchRevision: (documentId: string, branchId: string, form: FormData) =>
  request<LegalDocumentRevision>(`/api/documents/${documentId}/branches/${branchId}/revisions/upload`, {
    method: "POST",
    body: form,
  }),

analyzeDocumentDiff: (
  documentId: string,
  payload: { base_revision_id: string; target_revision_id: string },
) =>
  request<LegalDocumentAnalysis>(`/api/documents/${documentId}/diff/analyze`, {
    method: "POST",
    body: JSON.stringify(payload),
  }),

documentDiffExportUrl: (documentId: string, baseRevisionId: string, targetRevisionId: string) => {
  const params = new URLSearchParams({
    base_revision_id: baseRevisionId,
    target_revision_id: targetRevisionId,
  });
  return `${API_BASE}/api/documents/${documentId}/diff/export.docx?${params.toString()}`;
},
```

保留旧：

```ts
documentExportUrl
documentDiff
uploadRevision
createRevision
```

旧接口给案件详情页使用，不要删除。

## 11. 前端界面改造

主要修改：

```text
frontend/src/views/DocumentsView.vue
frontend/src/styles/app.css
```

可以选择拆组件，但为了减少风险，推荐先只改 `DocumentsView.vue` 和 `app.css`。

### 11.1 页面整体布局

`DocumentsView.vue` 页面布局改为三栏：

1. 左栏：文件库列表 + 上传新文件库。
2. 中栏：当前文件库的分支树状总览 + 创建分支。
3. 右栏：上传版本 + 版本对比 + diff + AI 分析 + Word 导出。

推荐模板结构：

```vue
<template>
  <PageHeader title="法律文件" description="文件库、分支、版本对比和法律风险分析。">
    <button class="button primary" @click="createSample">新建双版本示例</button>
  </PageHeader>

  <section class="page-content">
    <div class="document-workbench">
      <section class="panel document-sidebar">...</section>
      <section class="panel document-tree-panel">...</section>
      <section class="panel document-diff-panel">...</section>
    </div>
  </section>
</template>
```

### 11.2 左栏：文件库列表和上传

左栏必须包含：

- 标题：`文件库`
- 文件标题输入框
- 文件类型 select
- 文件上传 input
- 按钮：`上传为新文件库`
- 文件库列表

上传逻辑：

- 使用现有 `api.uploadDocument(form)`。
- 上传成功后：
  - 清空上传文件和标题。
  - 重新加载 documents。
  - 自动选中新文件。
  - 自动加载 tree。

文件库列表每项显示：

- 文件标题
- 文件类型
- 当前版本数量
- 删除按钮

点击文件库后调用：

```ts
await select(document.id)
```

### 11.3 中栏：VSCode 风格分支树

中栏必须包含：

- 标题：`分支总览`
- 创建分支表单
- 分支树

创建分支表单字段：

- 分支名 input，placeholder：`新分支名称，例如 lawyer-review`
- 基于版本 select
- 按钮：`创建分支`

创建分支逻辑：

```ts
async function createBranch() {
  if (!selectedId.value || !newBranchName.value.trim() || !branchBaseRevisionId.value) return;
  await api.createDocumentBranch(selectedId.value, {
    name: newBranchName.value.trim(),
    base_revision_id: branchBaseRevisionId.value,
  });
  newBranchName.value = "";
  await select(selectedId.value);
}
```

树状显示规则：

- 每个分支是一组。
- 分支头部显示：
  - 分支图标或字符：`⌁` 或使用 lucide 图标 `GitBranch`
  - 分支名
  - 如果 `is_default`，显示 `默认`
  - 如果 `head_revision_id`，显示 `HEAD`
- 分支下方显示 revisions。
- 每个 revision 显示：
  - `v{version_number}`
  - `short_hash`
  - `change_summary`
  - `source_filename`
  - 创建时间

点击 revision 的行为：

- 如果还没有选择 base revision，则设置为 base。
- 如果已选择 base 但没有 target，则设置为 target。
- 如果 base 和 target 都已有，则点击后设置 target 为点击的 revision。
- 点击后调用 `reloadDiff()`。

为了避免用户困惑，每个 revision 旁边提供两个小按钮：

- `设为基准`
- `设为目标`

不要只依赖点击整行。

### 11.4 右栏：向指定分支上传新版本

右栏上半部分必须包含：

- 标题：`提交新版本`
- 目标分支 select
- 文本 textarea
- 文件上传 input
- 版本说明 input
- 按钮：`提交文本版本`
- 按钮：`上传文件版本`

目标分支：

- 默认选择 `main`。
- 如果当前选中分支，默认选择当前选中分支。

提交文本版本：

```ts
async function createTextRevision() {
  if (!selectedId.value || !selectedBranchId.value || !revisionText.value.trim()) return;
  await api.createBranchRevision(selectedId.value, selectedBranchId.value, {
    content_text: revisionText.value.trim(),
    change_summary: revisionSummary.value.trim() || "手动粘贴新版本",
  });
  revisionText.value = "";
  revisionSummary.value = "";
  await select(selectedId.value);
}
```

上传文件版本：

```ts
async function uploadRevision() {
  if (!selectedId.value || !selectedBranchId.value || !revisionFile.value) return;
  const form = new FormData();
  form.append("file", revisionFile.value);
  form.append("change_summary", revisionSummary.value.trim() || "上传新版本");
  await api.uploadBranchRevision(selectedId.value, selectedBranchId.value, form);
  revisionFile.value = null;
  revisionSummary.value = "";
  await select(selectedId.value);
}
```

### 11.5 右栏：版本对比

必须包含：

- 基准版本 select
- 目标版本 select
- 按钮：`刷新对比`
- 按钮：`导出差异 Word`
- 按钮：`AI 分析`

导出差异 Word：

```vue
<a
  class="button"
  :href="api.documentDiffExportUrl(selectedId, baseRevisionId, targetRevisionId)"
  :class="{ disabled: !canCompare }"
>
  导出差异 Word
</a>
```

如果项目没有 `.disabled` 样式，可以按钮 disabled 时隐藏链接或使用 button 点击 `window.location.href = url`。

`canCompare`：

```ts
const canCompare = computed(() => Boolean(selectedId.value && baseRevisionId.value && targetRevisionId.value && baseRevisionId.value !== targetRevisionId.value));
```

`reloadDiff()`：

```ts
async function reloadDiff() {
  analysis.value = null;
  if (!canCompare.value) {
    diff.value = null;
    return;
  }
  diff.value = await api.documentDiff(selectedId.value, baseRevisionId.value, targetRevisionId.value);
}
```

### 11.6 diff 显示

继续使用现有逻辑：

```vue
<span
  v-for="(segment, index) in diff.segments"
  :key="index"
  :class="segment.op === 'insert' ? 'diff-insert' : segment.op === 'delete' ? 'diff-delete' : ''"
>{{ segment.text }}</span>
```

段落变化：

- insert 使用绿色 Badge。
- delete 使用红色 Badge。
- replace 使用 amber Badge。
- equal 可以不展示，或者展示为灰色。

建议过滤掉 equal：

```vue
<div v-for="change in changedParagraphs" ...>
```

```ts
const changedParagraphs = computed(() =>
  diff.value ? diff.value.paragraph_changes.filter((item) => item.op !== "equal") : [],
);
```

### 11.7 AI 分析面板

按钮：

```vue
<button class="button primary" :disabled="!canCompare || analyzing" @click="analyzeDiff">
  {{ analyzing ? "分析中" : "AI 分析" }}
</button>
```

逻辑：

```ts
async function analyzeDiff() {
  if (!canCompare.value) return;
  analyzing.value = true;
  try {
    analysis.value = await api.analyzeDocumentDiff(selectedId.value, {
      base_revision_id: baseRevisionId.value,
      target_revision_id: targetRevisionId.value,
    });
  } finally {
    analyzing.value = false;
  }
}
```

展示内容：

- 风险等级：低/中/高
- 分析来源：大模型 / 规则兜底
- 可能歧义
- 疑似暗改
- 风险点
- 建议
- 人工复核清单

示例模板：

```vue
<section v-if="analysis" class="plain-section">
  <div class="detail-header">
    <h3 class="panel-title">AI 分析</h3>
    <Badge :tone="analysis.risk_level === 'high' ? 'red' : analysis.risk_level === 'medium' ? 'amber' : 'green'">
      {{ riskLevelLabel(analysis.risk_level) }}
    </Badge>
  </div>
  <p class="muted small">来源：{{ analysis.source === "llm" ? "大模型" : "规则兜底" }}</p>
  <h4 class="section-label">可能歧义</h4>
  <ul><li v-for="item in analysis.ambiguities" :key="item">{{ item }}</li></ul>
  <h4 class="section-label">疑似暗改</h4>
  <ul><li v-for="item in analysis.stealth_changes" :key="item">{{ item }}</li></ul>
  <h4 class="section-label">风险点</h4>
  <ul><li v-for="item in analysis.risk_points" :key="item">{{ item }}</li></ul>
  <h4 class="section-label">建议</h4>
  <ul><li v-for="item in analysis.suggestions" :key="item">{{ item }}</li></ul>
  <h4 class="section-label">人工复核清单</h4>
  <ul><li v-for="item in analysis.manual_review_checklist" :key="item">{{ item }}</li></ul>
</section>
```

## 12. 前端样式

修改文件：

```text
frontend/src/styles/app.css
```

新增样式：

```css
.document-workbench {
  display: grid;
  grid-template-columns: minmax(220px, 0.9fr) minmax(260px, 1fr) minmax(420px, 1.6fr);
  gap: 14px;
  align-items: start;
}

.document-sidebar,
.document-tree-panel,
.document-diff-panel {
  min-width: 0;
}

.branch-tree {
  display: grid;
  gap: 10px;
}

.branch-group {
  border: 1px solid var(--border);
  border-radius: 6px;
  background: #ffffff;
  overflow: hidden;
}

.branch-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 8px 10px;
  background: #f8fafc;
  border-bottom: 1px solid var(--border);
}

.branch-name {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  font-weight: 700;
}

.revision-tree-list {
  display: grid;
  gap: 0;
}

.revision-tree-item {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto;
  gap: 6px;
  align-items: center;
  padding: 7px 10px 7px 22px;
  border-bottom: 1px solid var(--border);
  background: #fff;
}

.revision-tree-item:last-child {
  border-bottom: 0;
}

.revision-tree-item.active-base {
  background: #eff6ff;
}

.revision-tree-item.active-target {
  background: #f0fdf4;
}

.revision-main {
  min-width: 0;
}

.revision-title {
  display: flex;
  gap: 6px;
  align-items: center;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.hash {
  font-family: "Cascadia Code", Consolas, monospace;
  color: var(--muted);
  font-size: 11px;
}

.section-label {
  margin: 10px 0 6px;
  font-size: 13px;
}

@media (max-width: 1100px) {
  .document-workbench {
    grid-template-columns: 1fr;
  }
}
```

保留现有 `.diff-insert` 和 `.diff-delete`。

## 13. 案件详情页兼容

文件：

```text
frontend/src/views/CaseDetailView.vue
```

当前案件详情页只上传文件和导出 Word。可以不大改。

但如果 `documentDetail` 类型改变导致 TypeScript 报错，按新返回类型修复。

案件详情页的上传逻辑继续调用：

```ts
api.uploadDocument(form)
```

不要在案件详情页强制加入分支树，避免页面过复杂。

## 14. 后端测试

修改或新增测试：

```text
backend/tests/test_mvp_flows.py
```

必须新增以下测试。

### 14.1 上传文件自动创建 main 分支

流程：

1. POST `/api/documents/upload`
2. GET `/api/documents/{id}`
3. 断言：
   - `branches` 存在。
   - 有一个 `name == "main"` 的分支。
   - `is_default == True`
   - 初始 revision 的 `branch_id` 等于 main branch id。

### 14.2 创建分支

流程：

1. 创建文档。
2. 获取第一个 revision id。
3. POST `/api/documents/{id}/branches`，name=`client-edits`。
4. 断言：
   - 返回 200。
   - 分支名正确。
   - `head_revision_id == base_revision_id`。

### 14.3 向分支上传新版本

流程：

1. 创建文档。
2. 创建分支。
3. POST `/api/documents/{id}/branches/{branch_id}/revisions/upload`
4. 断言：
   - revision.branch_id == branch_id
   - revision.parent_revision_id == 创建分支时的 base_revision_id
   - GET tree 时该分支下有该 revision。

### 14.4 跨分支 diff

流程：

1. main 有 v1。
2. 创建分支 branchA from v1。
3. branchA 上传 v2。
4. main 上传 v3。
5. GET `/api/documents/{id}/diff?base_revision_id={branchA_v2}&target_revision_id={main_v3}`
6. 断言 200，segments 不为空。

### 14.5 导出差异 Word

流程：

1. 创建两个版本。
2. GET `/api/documents/{id}/diff/export.docx?base_revision_id=...&target_revision_id=...`
3. 断言：
   - status 200
   - content-type 是 docx
   - 内容以 `PK` 开头

不需要在测试中解析 Word 样式。

### 14.6 AI 分析无 key 兜底

流程：

1. monkeypatch 删除 `LVZHIJIE_LLM_API_KEY` 和 `OPENAI_API_KEY`。
2. 创建两个版本。
3. POST `/api/documents/{id}/diff/analyze`
4. 断言：
   - status 200
   - `source == "rule_fallback"`
   - `risk_points` 不为空
   - `manual_review_checklist` 不为空

### 14.7 删除文件级联删除 branches 和 analyses

流程：

1. 创建文档。
2. 创建分支。
3. 创建 analysis。
4. DELETE `/api/documents/{id}`
5. 断言文档不存在。
6. 如果可以直接访问 store，断言没有该 document_id 的 branches 和 analyses。

## 15. 前端验证

必须运行：

```powershell
cd C:\Users\35696\Desktop\law-project\lvzhijie\frontend
npm run build
```

如果 TypeScript 报错，必须修复。

## 16. 后端验证

必须运行：

```powershell
cd C:\Users\35696\Desktop\law-project\lvzhijie\backend
uv run --extra dev pytest
```

如果测试失败，必须修复。

## 17. 手动验收步骤

启动后端：

```powershell
cd C:\Users\35696\Desktop\law-project\lvzhijie\backend
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

启动前端：

```powershell
cd C:\Users\35696\Desktop\law-project\lvzhijie\frontend
npm run dev
```

打开：

```text
http://127.0.0.1:5173/documents
```

验收流程：

1. 上传一个 `.txt` 或 `.docx` 文件。
2. 确认左侧出现一个新文件库。
3. 点击该文件库。
4. 中间树状总览必须出现 `main` 分支。
5. `main` 分支下必须有初始版本。
6. 从初始版本创建分支，分支名填写 `lawyer-review`。
7. 确认树中出现 `lawyer-review` 分支。
8. 选择 `lawyer-review` 分支，上传一个新版本。
9. 选择 `main` 的初始版本为基准，选择 `lawyer-review` 的新版本为目标。
10. 确认右侧出现红绿差异。
11. 点击“AI 分析”。
12. 没有 API key 时也必须出现规则兜底分析。
13. 点击“导出差异 Word”。
14. 下载的 Word 必须能打开，并且包含红色删除、绿色新增。

## 18. 完成标准

全部满足以下条件才算完成：

1. 旧接口仍能正常使用。
2. 上传新文件会自动创建文件库和 `main` 分支。
3. 可以从任意版本创建自定义名称分支。
4. 可以向指定分支上传新版本。
5. 分支和版本在前端以树状结构展示。
6. 任意两个版本可以对比。
7. 前端 diff 红绿标记正常。
8. 差异 Word 导出包含红绿标记。
9. AI 分析按钮可用。
10. 没有 LLM key 时 AI 分析有兜底输出。
11. 后端 `pytest` 通过。
12. 前端 `npm run build` 通过。

## 19. 最重要的实现提醒

1. 不要把“分支”做成单纯前端假数据，必须存入 `legal_document_branches`。
2. 不要用 `version_number` 表示分支关系，分支关系必须使用 `branch_id` 和 `parent_revision_id`。
3. 创建分支时不要复制版本，分支 HEAD 指向已有 base revision。
4. 向分支上传新版本时才创建新 revision。
5. 默认分支永远叫 `main`。
6. `document.current_revision_id` 永远指向默认分支 `main` 的 HEAD，保持旧功能兼容。
7. Word 普通导出 `/export.docx` 保留为导出当前默认分支 HEAD 版本。
8. Word 差异导出必须使用新接口 `/diff/export.docx`。
9. AI 分析不要阻塞 diff 功能，失败必须兜底。
10. 修改时先做后端模型和接口，再做前端，否则前端类型容易混乱。

