from __future__ import annotations

from app.models import (
    ActivityEvent,
    Case,
    CaseMemory,
    CaseTask,
    FollowUpQuestion,
    LegalAgent,
    LegalDocument,
    LegalDocumentBranch,
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
    main_branch = LegalDocumentBranch(
        id="branch_demo_main",
        document_id=document.id,
        name="main",
        is_default=True,
    )
    revisions = [
        LegalDocumentRevision(
            id="rev_demo_1",
            document_id=document.id,
            version_number=1,
            content_text="甲方应在验收后7日内支付服务费。违约金按每日万分之三计算。",
            source_filename="contract-v1.txt",
            change_summary="初始版本",
            branch_id=main_branch.id,
            parent_revision_id=None,
            created_from_revision_id=None,
            short_hash="rev_dem",
        ),
        LegalDocumentRevision(
            id="rev_demo_2",
            document_id=document.id,
            version_number=2,
            content_text="甲方应在验收后30日内支付服务费。违约金按每日万分之一计算，累计不超过合同金额10%。",
            source_filename="contract-v2.txt",
            change_summary="付款期限和违约责任调整",
            branch_id=main_branch.id,
            parent_revision_id="rev_demo_1",
            created_from_revision_id="rev_demo_1",
            short_hash="rev_dem",
        ),
    ]
    main_branch.base_revision_id = revisions[0].id
    main_branch.head_revision_id = revisions[-1].id
    document.default_branch_id = main_branch.id
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
    sample_contacts: list[WechatContact] = []
    sample_conversations: list[WechatConversation] = []
    sample_messages: list[WechatMessage] = []
    sample_cases: list[Case] = []
    sample_tasks: list[CaseTask] = []
    sample_memories: list[CaseMemory] = []
    sample_followups: list[FollowUpQuestion] = []
    sample_reply_jobs: list[LegalReplyJob] = []
    sample_events: list[ActivityEvent] = []
    family_consultation_specs = [
        {
            "suffix": "225",
            "surname": "江",
            "remark": "校园防卫刑事咨询",
            "case_type": "criminal",
            "case_title": "江家属校园防卫刑事咨询",
            "summary": "家属咨询未成年人在校园被多人围堵殴打后持小折刀反击，关注能否主张正当防卫及防卫限度。",
            "messages": [
                (
                    "wechat_user",
                    "inbound",
                    "您好，我是江家属。孩子在学校被十几名同学围住殴打，情急下用随身小折刀反击，现在担心会不会按故意伤害处理。",
                ),
                (
                    "openclaw_auto",
                    "outbound",
                    "我先帮您把关键事实梳理清楚。孩子当时是否被迫到现场、对方人数、受伤情况和警方程序到哪一步了？",
                ),
                (
                    "wechat_user",
                    "inbound",
                    "孩子说上午已经被拉扯和踢打，中午又被带到厕所。对方大约十五人，有人勒住脖子把他摔倒，随后多人一起踢打。",
                ),
                (
                    "wechat_user",
                    "inbound",
                    "孩子手里的折刀是同学平时开药瓶用的小工具，不是管制刀具。对方暂时散开后，又有人从背后打他，他才转身反击。",
                ),
                (
                    "owner",
                    "outbound",
                    "先重点保留被围堵、倒地挨打、对方人数、刀具来源、伤情鉴定、老师处理记录和在场同学证言。",
                ),
            ],
            "memories": [
                ("fact", "咨询人称孩子在校园内被多人围堵、摔倒并持续殴打后持小折刀反击。"),
                ("timeline", "上午发生拉扯和踢打，中午被带往厕所后再次遭多人围堵殴打，随后发生持刀反击。"),
                ("evidence", "需收集监控、在场学生证言、伤情鉴定、刀具来源、学校处理记录和报警材料。"),
                ("uncertainty", "需核对孩子是否被迫前往现场、不法侵害是否仍在进行、防卫行为是否明显超过必要限度。"),
            ],
            "tasks": [
                ("整理校园冲突时间线", "案件秘书 Agent", "in_progress"),
                ("分析正当防卫构成与防卫限度", "承办律师 Agent", "todo"),
                ("生成家属追问清单", "风险质控 Agent", "todo"),
            ],
            "followups": [
                "请补充学校监控、老师记录、在场同学证言和伤情鉴定材料是否已经取得。",
                "请按时间顺序说明孩子何时被叫走、何时被围堵、何时倒地以及对方是否仍在继续攻击。",
                "请确认折刀来源、尺寸、平时用途以及孩子携带时的主观想法。",
            ],
            "draft": (
                "江家属您好，现有信息显示，本案重点不是简单看是否使用了工具，而是核对孩子是否处于被迫防卫、"
                "不法侵害是否正在进行，以及反击是否明显超过必要限度。建议先固定监控、证言、伤情鉴定和学校处理记录，"
                "再围绕正当防卫提出系统意见。"
            ),
        },
        {
            "suffix": "269",
            "surname": "刘",
            "remark": "交通事故刑事责任咨询",
            "case_type": "traffic",
            "case_title": "刘家属交通事故刑事责任咨询",
            "summary": "家属咨询交通事故后离开现场被认定全责，但事故原因显示对方超车等行为作用更大，关注是否构成交通肇事罪。",
            "messages": [
                (
                    "wechat_user",
                    "inbound",
                    "我是刘家属。家里人骑无号牌电动三轮和一辆摩托发生剐蹭，对方乘车人后来抢救无效。交警因为他离开现场认定全责，现在被追究交通肇事。",
                ),
                (
                    "wechat_user",
                    "inbound",
                    "对方摩托超车时对面来了卡车，紧急变向才碰到三轮。我们家人确实没证、车辆没登记、没戴头盔，事故后短暂停留又离开。",
                ),
                (
                    "openclaw_auto",
                    "outbound",
                    "需要区分行政事故责任和刑事责任。请补充事故认定书中事故原因分析、责任结论、证人证言和离开现场是否导致损害扩大。",
                ),
                (
                    "wechat_user",
                    "inbound",
                    "认定书原因部分写对方超车、无证、无牌、未戴头盔是主要原因，我们这边是次要原因，但责任结论又写因为离开现场承担全责。",
                ),
                (
                    "owner",
                    "outbound",
                    "这个样例重点在刑法因果关系。请先把事故原因部分、责任认定部分、现场证人材料和救治时间线整理出来。",
                ),
            ],
            "memories": [
                ("fact", "咨询人称事故认定书的原因分析与最终责任结论存在张力，离开现场成为全责认定的重要因素。"),
                ("timeline", "事故发生后当事人短暂停留后离开现场，后续对方乘车人经抢救无效死亡。"),
                ("evidence", "需核对事故认定书、现场目击证言、车辆轨迹、救治记录和离开现场对损害后果的影响。"),
                ("uncertainty", "需判断离开现场行为对事故发生或损害扩大是否具有刑法意义上的原因力。"),
            ],
            "tasks": [
                ("拆分事故原因与责任结论", "案件秘书 Agent", "in_progress"),
                ("分析交通肇事罪刑事责任基础", "承办律师 Agent", "todo"),
                ("核对行政责任与刑事责任差异", "风险质控 Agent", "todo"),
            ],
            "followups": [
                "请提供事故认定书中“事故发生原因”和“责任认定”两个部分的完整内容。",
                "请补充离开现场前后是否有人报警、是否影响救治、是否影响事故原因查明。",
                "请整理对方超车、会车、头盔、证照和车辆登记情况的证据来源。",
            ],
            "draft": (
                "刘家属您好，交通事故认定书是重要证据，但刑事责任还要看事故原因和因果关系。"
                "如果离开现场没有导致事故发生，也没有导致损害扩大，不能当然把行政上的全责结论直接等同为交通肇事罪中的主要责任。"
                "下一步应重点核对事故原因分析、证人证言和救治过程。"
            ),
        },
        {
            "suffix": "272",
            "surname": "艾",
            "remark": "危险驾驶做局咨询",
            "case_type": "criminal",
            "case_title": "艾家属危险驾驶做局咨询",
            "summary": "家属咨询当事人醉酒后在高速驾驶被查，后发现他人通过欺骗、陪酒、安排车辆和报警制造案件，关注被诱导者与组织者责任。",
            "messages": [
                (
                    "wechat_user",
                    "inbound",
                    "我是艾家属。家里人酒后在高速上开车被查，血检超过醉驾标准。后来发现是别人为了换取从宽处理故意做局，让他喝酒再引导上高速并报警。",
                ),
                (
                    "openclaw_auto",
                    "outbound",
                    "先确认醉驾事实、是否被诱导、哪些人安排聚餐和车辆、是否有聊天记录、转账记录或报警时间线。",
                ),
                (
                    "wechat_user",
                    "inbound",
                    "对方有人安排吃饭、陪酒，还说会叫代驾，后来又说换地方玩。家里人本来想住下，对方又说跟车走高速没事。",
                ),
                (
                    "wechat_user",
                    "inbound",
                    "我们想问这种情况下家里人会怎么处理，做局的人是不是也构成危险驾驶共犯。",
                ),
                (
                    "owner",
                    "outbound",
                    "醉驾事实本身仍有刑事风险，但诱导者如果反复欺骗、怂恿并安排路线车辆，可能承担更重的共犯责任。",
                ),
            ],
            "memories": [
                ("fact", "咨询人称当事人醉酒后在高速驾驶被查，存在他人安排聚餐、陪酒、车辆、路线和报警的情况。"),
                ("timeline", "聚餐饮酒后，当事人原有住宿意向，后被引导驾车上高速并在出口被查。"),
                ("evidence", "需收集聊天记录、转账记录、聚餐参与人员陈述、车辆安排记录、报警记录和血检报告。"),
                ("uncertainty", "需判断诱导者是否与醉驾行为存在共同意思联络，以及各人在促成醉驾中的作用大小。"),
            ],
            "tasks": [
                ("整理做局过程和证据链", "案件秘书 Agent", "in_progress"),
                ("分析危险驾驶共犯责任", "承办律师 Agent", "todo"),
                ("评估被诱导者量刑情节", "风险质控 Agent", "todo"),
            ],
            "followups": [
                "请整理聚餐前后的聊天记录，尤其是约饭、陪酒、代驾、换地点和高速路线相关内容。",
                "请补充车辆由谁提供、谁提出上高速、谁报警、报警前后各方是否保持联系。",
                "请确认血检数值、查获地点、是否主动供述被诱导经过以及是否有转账记录。",
            ],
            "draft": (
                "艾家属您好，醉酒驾驶事实需要单独评估，但若他人以获取从宽处理为目的，反复欺骗、怂恿并安排车辆路线促成醉驾，"
                "组织者、诱导者可能按危险驾驶罪共犯评价。建议先固定聊天、转账、报警和车辆安排证据。"
            ),
        },
    ]

    for spec in family_consultation_specs:
        suffix = str(spec["suffix"])
        contact_id = f"contact_family_{suffix}"
        conversation_id = f"conv_family_{suffix}"
        case_id = f"case_family_{suffix}"
        contact_item = WechatContact(
            id=contact_id,
            openclaw_contact_id=f"mock_{contact_id}",
            display_name=f"{spec['surname']}家属",
            remark=str(spec["remark"]),
            last_seen_at=now_iso(),
        )
        conversation_item = WechatConversation(
            id=conversation_id,
            openclaw_conversation_id=f"mock_{conversation_id}",
            contact_id=contact_id,
            case_id=case_id,
            status="open",
            last_message_at=now_iso(),
            unread_count=0,
        )
        case_item = Case(
            id=case_id,
            title=str(spec["case_title"]),
            case_type=spec["case_type"],  # type: ignore[arg-type]
            status="collecting_info",
            summary=str(spec["summary"]),
            wechat_contact_ref=contact_id,
            conversation_ref=conversation_id,
        )
        sample_contacts.append(contact_item)
        sample_conversations.append(conversation_item)
        sample_cases.append(case_item)

        first_user_question = ""
        for index, (sender, direction, content) in enumerate(spec["messages"], start=1):
            status = "synced"
            if sender == "openclaw_auto":
                status = "openclaw_auto_replied"
            elif sender == "owner":
                status = "sent_via_openclaw"
            if direction == "inbound" and not first_user_question:
                first_user_question = str(content)
            sample_messages.append(
                WechatMessage(
                    id=f"msg_family_{suffix}_{index}",
                    conversation_id=conversation_id,
                    sender=sender,  # type: ignore[arg-type]
                    direction=direction,  # type: ignore[arg-type]
                    content=str(content),
                    status=status,  # type: ignore[arg-type]
                    source="mock",
                )
            )

        for index, (kind, content) in enumerate(spec["memories"], start=1):
            sample_memories.append(
                CaseMemory(
                    id=f"memory_family_{suffix}_{index}",
                    case_id=case_id,
                    kind=kind,  # type: ignore[arg-type]
                    content=str(content),
                    source_ref=conversation_id,
                    confirmed=False,
                )
            )

        for index, (title, role, status) in enumerate(spec["tasks"], start=1):
            sample_tasks.append(
                CaseTask(
                    id=f"task_family_{suffix}_{index}",
                    case_id=case_id,
                    title=str(title),
                    assigned_agent_role=str(role),
                    status=status,  # type: ignore[arg-type]
                )
            )

        for index, content in enumerate(spec["followups"], start=1):
            sample_followups.append(
                FollowUpQuestion(
                    id=f"followup_family_{suffix}_{index}",
                    case_id=case_id,
                    content=str(content),
                )
            )

        sample_reply_jobs.append(
            LegalReplyJob(
                id=f"reply_family_{suffix}_1",
                case_id=case_id,
                mode="short_reply",
                title="家属咨询首轮回复",
                case_summary=case_item.summary,
                user_question=first_user_question,
                status="ready_for_review",
                assigned_agent_role="客户服务 Agent",
                draft_text=str(spec["draft"]),
            )
        )
        sample_events.extend(
            [
                ActivityEvent(
                    id=f"event_family_{suffix}_wechat",
                    event_type="wechat.sample.created",
                    title="创建家属咨询样例",
                    description=case_item.title,
                    entity_type="conversation",
                    entity_id=conversation_id,
                ),
                ActivityEvent(
                    id=f"event_family_{suffix}_case",
                    event_type="case.sample.created",
                    title="创建案件样例",
                    description=case_item.title,
                    entity_type="case",
                    entity_id=case_id,
                ),
            ]
        )

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
        "wechat_contacts": [contact.model_dump(), *[item.model_dump() for item in sample_contacts]],
        "wechat_conversations": [conversation.model_dump(), *[item.model_dump() for item in sample_conversations]],
        "wechat_messages": [message.model_dump() for message in messages + sample_messages],
        "cases": [case.model_dump(), *[item.model_dump() for item in sample_cases]],
        "case_tasks": [task.model_dump() for task in tasks + sample_tasks],
        "case_memories": [memory.model_dump() for memory in memories + sample_memories],
        "legal_agents": [agent.model_dump() for agent in agents],
        "legal_documents": [document.model_dump()],
        "legal_document_revisions": [revision.model_dump() for revision in revisions],
        "legal_document_branches": [main_branch.model_dump()],
        "legal_document_diffs": [],
        "legal_document_analyses": [],
        "legal_reasoning_runs": [],
        "follow_up_questions": [question.model_dump() for question in sample_followups],
        "reply_jobs": [job.model_dump() for job in reply_jobs + sample_reply_jobs],
        "activity_events": [event.model_dump() for event in events + sample_events],
    }
