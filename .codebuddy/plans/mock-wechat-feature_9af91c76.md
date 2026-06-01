---
name: mock-wechat-feature
overview: 实现本地 Mock 微信聊天记录功能：后端新增 MockWechatStore 读写 mock JSON 数据，修改已有接口支持 mock 模式，新增设置页专用 API；前端增强消息渲染支持图片/文件，新建 MockWechatView 编辑器页面，添加路由和入口。
todos:
  - id: backend-models
    content: 修改 models.py，添加 WechatAttachment 模型，扩展 WechatMessage 的 type 和 attachments 字段，添加 MockConversation 请求模型
    status: completed
  - id: mock-store
    content: 新建 mock_wechat_store.py，实现 MockWechatStore 类（会话/消息 CRUD、文件上传、同步到 JsonStore）
    status: completed
    dependencies:
      - backend-models
  - id: backend-api
    content: 修改 main.py：挂载静态资源、实例化 MockWechatStore、修改已有微信接口支持 mock 模式、新增 /api/mock-wechat/ CRUD 接口、修改 openclaw sync 接口
    status: completed
    dependencies:
      - mock-store
  - id: frontend-types-api
    content: 修改 types/index.ts 添加 WechatAttachment 类型，修改 services/api.ts 添加 mock 相关 API 函数
    status: completed
  - id: enhance-wechat-view
    content: 修改 WechatView.vue 增强消息渲染（支持图片/文件附件），更新搜索逻辑包含附件名，添加 app.css 附件样式
    status: completed
    dependencies:
      - frontend-types-api
  - id: mock-editor-page
    content: 新建 MockWechatView.vue 设置页编辑器（会话列表、新建对话、双发送框、消息预览），添加路由到 main.ts，在 OpenClawView.vue 添加入口
    status: completed
    dependencies:
      - frontend-types-api
  - id: backend-tests
    content: 新建 tests/test_mock_wechat.py，测试 mock 模式下会话创建、消息添加、文件上传、同步到微信接口等功能
    status: completed
    dependencies:
      - backend-api
  - id: verify
    content: 运行后端测试和前端构建验证，确保所有功能正常且现有功能不被破坏
    status: completed
    dependencies:
      - enhance-wechat-view
      - mock-editor-page
      - backend-tests
---

## 产品概述

在现有法律工作台项目中实现本地 Mock 微信聊天记录功能，用于本地演示和测试，不连接真实微信。

## 核心功能

- 后端模型兼容：为 WechatMessage 添加 type 和 attachments 字段，新增 WechatAttachment 模型
- Mock 数据存储：新建 mock_wechat_store.py，管理 conversations.json、messages/*.json 和 assets/ 目录
- 后端接口改造：当 transport_mode 为 "mock" 时，已有微信接口从 mock 目录读取数据；新增 /api/mock-wechat/ CRUD 接口用于设置页编辑
- 静态资源挂载：挂载 /mock-wechat-assets 提供上传文件的 HTTP 访问
- 前端类型和 API 扩展：添加 WechatAttachment 类型，新增 mock 相关 API 函数
- 增强消息渲染：WechatView.vue 支持文本、图片、文件附件渲染，搜索支持附件名
- 设置页编辑器：新建 MockWechatView.vue，支持新建对话、双发送框（客户/我方）添加消息和附件上传，在 OpenClawView.vue 添加入口
- 兼容现有功能：案件绑定、一键建案、推理逻辑不被破坏

## 技术栈

- **后端**: FastAPI + Pydantic (已选定，无需更换)
- **前端**: Vue 3 + TypeScript + Vite (已选定，无需更换)
- **数据存储**: 本地 JSON 文件 (提示词要求不引入数据库)
- **静态文件**: FastAPI StaticFiles 中间件

## 实现方案

### 架构设计

复用现有架构，新增 MockWechatStore 作为独立数据层。当 `transport_mode == "mock"` 时，已有微信接口先同步 mock 数据到 JsonStore 再返回，保持与现有案件绑定、推理等功能的兼容性。

```
请求 → main.py 路由
  ├─ transport_mode == "mock" → MockWechatStore 读取 → 同步到 JsonStore → 返回
  └─ transport_mode == "gateway_rpc" → 原 OpenClaw 逻辑（不改动）
```

### 数据流

1. Mock 模式下，mock_wechat/ 目录是源数据，store.json 是镜像
2. 每次读取前调用 sync_to_json_store() 同步，确保案件绑定等依赖 store.json 的功能正常
3. 前端调用原有 /api/wechat/* 接口，无需感知数据来源
4. 设置页通过 /api/mock-wechat/* 接口编辑 mock 数据

### 关键技术决策

1. MockWechatStore 独立于 JsonStore，职责清晰，便于测试时替换目录
2. 附件文件名加 UUID 前缀防覆盖，URL 使用 /mock-wechat-assets/ 前缀返回 HTTP 路径
3. WechatMessage 的 type 和 attachments 字段设默认值，兼容旧数据
4. conftest.py 中增加 mock_wechat fixture 替换，避免污染真实数据目录

### 性能与可靠性

- JSON 文件读写开销小，演示场景无性能瓶颈
- 文件上传使用 UploadFile 流式读取，内存可控
- 文件名安全处理防止路径穿越攻击