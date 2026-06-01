from __future__ import annotations

from app.models import (
    ActivityEvent,
    Case,
    CaseMemory,
    CaseTask,
    LegalAgent,
    LegalDocument,
    LegalDocumentRevision,
    LegalReplyJob,
    OpenClawConnection,
    WechatContact,
    WechatConversation,
    WechatMessage,
    now_iso,
)


def build_seed_data() -> dict[str, object]:
    contact = WechatContact(
        id="contact_demo",
        openclaw_contact_id="wx_demo_client",
        display_name="张先生",
        remark="劳动争议咨询",
        last_seen_at=now_iso(),
    )
    conversation = WechatConversation(
        id="conv_demo",
        openclaw_conversation_id="oc_wx_conv_demo",
        contact_id=contact.id,
        case_id="case_demo",
        status="open",
        last_message_at=now_iso(),
        unread_count=1,
    )
    messages = [
        WechatMessage(
            id="msg_demo_1",
            conversation_id=conversation.id,
            sender="wechat_user",
            direction="inbound",
            content="公司拖欠我两个月工资，还说让我自己离职，我该怎么办？",
        ),
        WechatMessage(
            id="msg_demo_2",
            conversation_id=conversation.id,
            sender="openclaw_auto",
            direction="outbound",
            content="我先帮您梳理信息。请问您入职时间、劳动合同是否签订、工资发放记录是否还在？",
            status="openclaw_auto_replied",
        ),
    ]
    case = Case(
        id="case_demo",
        title="张先生劳动争议咨询",
        case_type="labor",
        status="collecting_info",
        summary="用户反映公司拖欠工资并要求其主动离职，需要确认劳动合同、工资流水和解除事实。",
        wechat_contact_ref=contact.id,
        conversation_ref=conversation.id,
    )
    tasks = [
        CaseTask(
            id="task_demo_1",
            case_id=case.id,
            title="整理劳动关系基础事实",
            assigned_agent_role="案件秘书 Agent",
            status="in_progress",
        ),
        CaseTask(
            id="task_demo_2",
            case_id=case.id,
            title="生成第一轮追问问题",
            assigned_agent_role="风险质控 Agent",
            status="todo",
        ),
    ]
    memories = [
        CaseMemory(
            id="memory_demo_1",
            case_id=case.id,
            kind="fact",
            content="用户称公司拖欠两个月工资。",
            source_ref="msg_demo_1",
            confirmed=False,
        ),
        CaseMemory(
            id="memory_demo_2",
            case_id=case.id,
            kind="uncertainty",
            content="尚不清楚劳动合同签订情况、入职时间、工资标准和离职沟通证据。",
            source_ref="msg_demo_1",
            confirmed=False,
        ),
    ]
    document = LegalDocument(
        id="doc_demo",
        case_id=case.id,
        title="服务合同示例",
        document_type="contract",
        current_revision_id="rev_demo_2",
    )
    revisions = [
        LegalDocumentRevision(
            id="rev_demo_1",
            document_id=document.id,
            version_number=1,
            content_text="甲方应在验收后7日内支付服务费。违约金按每日万分之三计算。",
            source_filename="contract-v1.txt",
            change_summary="初始版本",
        ),
        LegalDocumentRevision(
            id="rev_demo_2",
            document_id=document.id,
            version_number=2,
            content_text="甲方应在验收后30日内支付服务费。违约金按每日万分之一计算，累计不超过合同金额10%。",
            source_filename="contract-v2.txt",
            change_summary="付款期限和违约责任调整",
        ),
    ]
    agents = [
        LegalAgent(
            role="dispatch_agent",
            title="调度智能体",
            description="负责统一接收案件信号、判断业务类型并分派给专业智能体组。",
            responsibilities=["识别业务入口", "选择处理链路", "跟踪任务状态"],
            group="dispatcher",
        ),
        LegalAgent(
            role="core_business_agent",
            title="核心业务 Agent",
            description="负责法律专业判断、部门分流、推理和文书交付。",
            responsibilities=["分流法律部门", "组织深度推理", "沉淀交付成果"],
            group="orchestration",
            reports_to="dispatch_agent",
        ),
        LegalAgent(
            role="client_service_agent",
            title="客户服务 Agent",
            description="负责法律咨询、接案报价、投诉处理和客户沟通节奏。",
            responsibilities=["法律咨询", "接案报价", "投诉处理"],
            group="orchestration",
            reports_to="dispatch_agent",
        ),
        LegalAgent(
            role="compliance_review_agent",
            title="合规审查 Agent",
            description="负责收案审批、利益冲突审查、风险评估和人工复核点。",
            responsibilities=["收案审批", "利益冲突审查", "风险评估"],
            group="orchestration",
            reports_to="dispatch_agent",
        ),
        LegalAgent(
            role="archive_management_agent",
            title="档案管理 Agent",
            description="负责案卷归档、档案查询、证据目录和过程记录。",
            responsibilities=["案卷归档", "档案查询"],
            group="orchestration",
            reports_to="dispatch_agent",
        ),
        LegalAgent(
            role="managing_lawyer",
            title="主任律师 Agent",
            description="负责案件总控、任务分配和结论把关。",
            responsibilities=["判断案件类型", "拆解办案任务", "标记必须人工复核的结论"],
            group="core_business",
            reports_to="core_business_agent",
        ),
        LegalAgent(
            role="reception_lawyer",
            title="客户接待 Agent",
            description="负责整理微信咨询和生成温和追问建议。",
            responsibilities=["读取微信聊天", "识别咨询主题", "整理初步案情"],
            group="client_service",
            reports_to="client_service_agent",
        ),
        LegalAgent(
            role="case_secretary",
            title="案件秘书 Agent",
            description="负责事实、时间线、证据和材料清单。",
            responsibilities=["抽取事实", "维护时间线", "标记证据缺口"],
            group="archive_management",
            reports_to="archive_management_agent",
        ),
        LegalAgent(
            role="handling_lawyer",
            title="承办律师 Agent",
            description="负责法律关系、争议焦点和要件分析。",
            responsibilities=["识别法律关系", "匹配事实与要件", "生成分析摘要"],
            group="core_business",
            reports_to="core_business_agent",
        ),
        LegalAgent(
            role="contract_reviewer",
            title="合同审查律师 Agent",
            description="负责合同版本差异和法律风险提示。",
            responsibilities=["分析逐字差异", "标记关键条款变化", "输出风险摘要"],
            group="compliance_review",
            reports_to="compliance_review_agent",
        ),
        LegalAgent(
            role="litigation_strategist",
            title="诉讼策略律师 Agent",
            description="负责诉讼路径、举证责任、风险和成本评估。",
            responsibilities=["评估诉讼/仲裁路径", "拆解举证责任", "提示程序风险"],
            group="core_business",
            reports_to="core_business_agent",
        ),
        LegalAgent(
            role="legal_researcher",
            title="法律检索 Agent",
            description="负责生成法条、案例和裁判规则检索方向。",
            responsibilities=["生成检索关键词", "整理法条方向", "标记待核验案例"],
            group="core_business",
            reports_to="core_business_agent",
        ),
        LegalAgent(
            role="quality_control",
            title="风险质控 Agent",
            description="负责检查过度推断、不确定点和追问问题。",
            responsibilities=["检查来源", "总结不确定点", "生成追问"],
            group="compliance_review",
            reports_to="compliance_review_agent",
        ),
        LegalAgent(
            role="drafting_lawyer",
            title="文书起草 Agent",
            description="负责起草微信回复、法律意见摘要和文书草稿。",
            responsibilities=["起草答复", "整理意见摘要", "生成文书草稿"],
            group="core_business",
            reports_to="core_business_agent",
        ),
    ]
    reply_jobs = [
        LegalReplyJob(
            id="reply_demo_1",
            case_id=case.id,
            mode="short_reply",
            title="首轮咨询短回复",
            case_summary=case.summary,
            user_question=messages[0].content,
            status="ready_for_review",
            assigned_agent_role="客户服务 Agent",
            draft_text=(
                "张先生您好，您描述的拖欠工资和要求主动离职都需要保留证据。"
                "建议先整理劳动合同、工资流水、考勤记录和离职沟通记录，"
                "我们再判断是否适合走劳动监察或劳动仲裁路径。"
            ),
        ),
        LegalReplyJob(
            id="reply_demo_2",
            case_id=case.id,
            mode="long_reply",
            title="劳动争议长回复任务",
            case_summary=case.summary,
            user_question=messages[0].content,
            status="queued",
            assigned_agent_role="文书起草 Agent",
        ),
    ]
    events = [
        ActivityEvent(
            event_type="wechat.synced",
            title="同步 OpenClaw 微信消息",
            description="已同步张先生的咨询会话。",
            entity_type="conversation",
            entity_id=conversation.id,
        ),
        ActivityEvent(
            event_type="case.created",
            title="创建案件",
            description="从微信会话创建劳动争议咨询案件。",
            entity_type="case",
            entity_id=case.id,
        ),
    ]
    return {
        "openclaw_connection": OpenClawConnection().model_dump(),
        "wechat_contacts": [contact.model_dump()],
        "wechat_conversations": [conversation.model_dump()],
        "wechat_messages": [message.model_dump() for message in messages],
        "cases": [case.model_dump()],
        "case_tasks": [task.model_dump() for task in tasks],
        "case_memories": [memory.model_dump() for memory in memories],
        "legal_agents": [agent.model_dump() for agent in agents],
        "legal_documents": [document.model_dump()],
        "legal_document_revisions": [revision.model_dump() for revision in revisions],
        "legal_document_diffs": [],
        "legal_reasoning_runs": [],
        "follow_up_questions": [],
        "reply_jobs": [job.model_dump() for job in reply_jobs],
        "activity_events": [event.model_dump() for event in events],
    }
