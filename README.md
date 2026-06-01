# 律智界

个人法律智能工作台。当前项目是按 v0.4 需求边界重构的新系统：

- 前端：Vue 3 + Vite + TypeScript，视觉风格参考 `mission-control` 的工作台布局。
- 后端：Python + FastAPI。
- OpenClaw：只作为微信插件运行环境和消息跳板，不承载案件、文件、推理或法律智能体业务。

## 功能边界

OpenClaw 负责：

- 运行微信插件。
- 读取微信聊天记录。
- 执行 OpenClaw 自己的微信自动回复。
- 电脑端发消息时作为跳板转发到微信。

本系统负责：

- 微信聊天记录同步和电脑端展示。
- 电脑端通过 OpenClaw 给手机发消息。
- 案件管理。
- 法律文件仿 Git 版本管理与逐字 diff。
- 法律推理 AOE 图。
- 待追问问题生成。
- 仿律师事务所智能体角色管理。

## 页面

- `/dashboard`：总览。
- `/wechat`：OpenClaw 微信聊天读取与电脑端发送。
- `/cases`：案件列表。
- `/cases/:id`：案件详情、任务、记忆、聊天沉淀。
- `/documents`：法律文件版本与逐字 diff。
- `/reasoning`：案件 AOE 推理图。
- `/agents`：仿律师事务所智能体架构。
- `/openclaw`：本机 OpenClaw 微信桥配置。

## OpenClaw 连接方式

后端的 OpenClaw Adapter 默认使用 mission-control 兼容的 Gateway WebSocket RPC：

```text
sessions.list
chat.history
chat.send
```

如果你的 OpenClaw 微信插件暴露的是专用方法名，可以在 `/openclaw` 页面修改：

- `List Method`
- `History Method`
- `Send Method`
- `Session Filter`

同步逻辑会将 OpenClaw session 映射为本系统的微信会话，将 history 消息映射为本系统聊天记录。电脑端发送消息时，会使用配置的 `Send Method` 通过 OpenClaw 转发。

如果 Gateway 需要设备配对，保持 `Control UI bypass` 关闭。首次连接可能需要在 OpenClaw 侧批准设备。若你的 Gateway 明确开启了控制台免配对，再打开 `Control UI bypass`。

## 后端启动

```powershell
cd C:\Users\35696\Desktop\law-project\lvzhijie\backend
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## 前端启动

```powershell
cd C:\Users\35696\Desktop\law-project\lvzhijie\frontend
npm install
npm run dev
```

打开：

```text
http://127.0.0.1:5173
```

## 验证

```powershell
cd C:\Users\35696\Desktop\law-project\lvzhijie\backend
uv run --extra dev python -c "from fastapi.testclient import TestClient; from app.main import app; c=TestClient(app); print(c.get('/api/health').json())"

cd C:\Users\35696\Desktop\law-project\lvzhijie\frontend
npm run build
```
