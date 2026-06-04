from __future__ import annotations

from typing import Any

from app.models import (
    ActivityEvent,
    Case,
    CaseMemory,
    CaseTask,
    CaseTaskComment,
    FollowUpQuestion,
    LegalDocumentAnalysis,
    LegalDocumentDiff,
    LegalAgent,
    LegalDocument,
    LegalDocumentBranch,
    LegalDocumentRevision,
    LegalReplyJob,
    LegalResearchResult,
    LegalResearchRun,
    LegalReasoningRun,
    OpenClawConnection,
    ReasoningEdge,
    ReasoningNode,
    WechatContact,
    WechatConversation,
    WechatMessage,
    now_iso,
)
from app.diffing import build_char_diff, build_paragraph_diff, summarize_legal_risks


def demo_time(hour: int, minute: int) -> str:
    return f"2026-06-03T{hour:02d}:{minute:02d}:00+08:00"


def family_enrichment(suffix: str) -> dict[str, Any]:
    data: dict[str, dict[str, Any]] = {
        "225": {
            "similar_query": "校园多人围堵殴打 小折刀反击 正当防卫 防卫限度",
            "law_query": "正当防卫 不法侵害正在进行 防卫限度 未成年人校园冲突",
            "keywords": ["正当防卫", "多人围堵", "防卫限度", "校园冲突"],
            "document_title": "江家属正当防卫阶段性法律意见",
            "document_revisions": [
                (
                    "initial-facts.txt",
                    "初始事实整理",
                    "一、事实整理\n家属反映，未成年人在校园被多人围堵、摔倒并持续殴打后，使用随身小折刀反击。\n\n二、初步判断\n现阶段只能判断存在正当防卫审查空间，尚需核对监控、证言、伤情鉴定和刀具来源。\n\n三、待补材料\n请补充学校监控、报警材料、老师处理记录和在场学生证言。",
                ),
                (
                    "defense-analysis-v2.txt",
                    "补充防卫构成要件",
                    "一、事实整理\n家属反映，未成年人上午已被拉扯踢打，中午又被带至厕所附近，被约十五人围堵、摔倒并持续殴打后，使用随身小折刀反击。\n\n二、法律分析\n本案应围绕不法侵害是否正在进行、孩子是否被迫防卫、反击是否明显超过必要限度展开。多人围堵、倒地后继续踢打、背后再次攻击，是支持防卫紧迫性的关键事实。\n\n三、证据清单\n优先固定监控、伤情照片和鉴定、同学证言、老师处理记录、报警回执、刀具来源和尺寸说明。",
                ),
                (
                    "defense-opinion-review.txt",
                    "主任律师复核版",
                    "一、阶段性结论\n现有陈述显示，本案具备正当防卫重点审查价值，不宜仅因使用小折刀即径行评价为普通故意伤害。核心应审查不法侵害是否持续、反击是否针对正在发生的危险、是否明显超过必要限度。\n\n二、论证重点\n1. 对方人数明显占优，且存在勒颈、摔倒、多人踢打等持续侵害情节。\n2. 孩子并非主动挑衅后扩大冲突，而是在被围堵、受控场景下反击。\n3. 小折刀来源、尺寸、用途和使用次数仍需证据固定，避免被误解为预谋携带凶器。\n\n三、办理建议\n立即调取校内监控，申请伤情鉴定，固定在场学生证言和学校处置记录。对外表述应保留“阶段性判断”边界，待警方材料和鉴定结论补齐后再形成正式辩护意见。",
                ),
            ],
            "similar_results": [
                {
                    "title": "多人围殴中被围堵者反击行为的防卫性质审查",
                    "reference": "演示类案-刑-防卫-001",
                    "court_or_authority": "演示案例库",
                    "key_points": [
                        "判断防卫性质时，应结合人数对比、被控制程度、侵害是否持续等事实综合评价。",
                        "不能仅因防卫工具造成伤害后果，就否定不法侵害正在进行。",
                    ],
                },
                {
                    "title": "校园冲突中未成年人被持续殴打后的反击限度评估",
                    "reference": "演示类案-刑-防卫-002",
                    "court_or_authority": "演示案例库",
                    "key_points": [
                        "未成年人判断能力、现场紧迫性和脱离可能性，是评价反击必要性的重要背景。",
                        "学校监控、老师处置记录和同学证言通常决定事实复原质量。",
                    ],
                },
            ],
            "law_results": [
                {
                    "title": "中华人民共和国刑法第二十条",
                    "reference": "正当防卫条款",
                    "court_or_authority": "全国人民代表大会",
                    "key_points": [
                        "为了使国家、公共利益、本人或者他人的人身、财产和其他权利免受正在进行的不法侵害，可以实施防卫。",
                        "防卫明显超过必要限度造成重大损害的，应负刑事责任但依法减轻或者免除处罚。",
                    ],
                },
                {
                    "title": "关于依法适用正当防卫制度的指导意见",
                    "reference": "正当防卫司法政策",
                    "court_or_authority": "最高人民法院、最高人民检察院、公安部",
                    "key_points": [
                        "防卫认定应立足防卫人所处情境，防止事后以冷静旁观标准苛求防卫人。",
                        "对多人围殴、持续侵害等场景，应重点审查防卫紧迫性和必要性。",
                    ],
                },
            ],
            "risk_level": "medium",
        },
        "269": {
            "similar_query": "交通事故 离开现场 行政全责 刑事主要责任 因果关系",
            "law_query": "交通肇事罪 主要责任 逃逸 因果关系 事故认定书",
            "keywords": ["交通肇事罪", "事故认定书", "主要责任", "因果关系"],
            "document_title": "刘家属交通肇事刑事责任分析",
            "document_revisions": [
                (
                    "traffic-facts.txt",
                    "初始事故事实整理",
                    "一、事实整理\n家属反映，电动三轮与摩托车发生剐蹭后，对方乘车人经抢救无效死亡。当事人存在无证、无牌、未戴头盔和离开现场情节。\n\n二、初步判断\n需要区分行政责任结论与刑事主要责任，不宜直接以全责认定替代刑法因果关系分析。",
                ),
                (
                    "traffic-causation-v2.txt",
                    "补充因果关系分析",
                    "一、事实整理\n事故原因部分显示，对方摩托车超车、对面来车后紧急变向，与三轮车发生剐蹭；认定书又因当事人离开现场作出全责结论。\n\n二、法律分析\n交通肇事罪审查重点是事故发生原因、损害结果和行为人责任程度。若离开现场未导致事故发生，也未导致损害扩大，行政上的全责结论不能当然等同刑事主要责任。\n\n三、待补材料\n需核对事故认定书全文、现场图、证人证言、救治时间线、报警记录和离开现场对调查及救治的影响。",
                ),
                (
                    "traffic-defense-review.txt",
                    "抗辩要点复核版",
                    "一、阶段性结论\n本案抗辩重点在于拆分“事故发生原因”和“事后离开现场”两个层次。若原因分析已确认对方超车、会车风险和紧急变向是主要成因，则需论证全责结论是否仅服务于行政事故处理，不能机械推定刑事主要责任。\n\n二、论证重点\n1. 对方超车与对面来车形成危险源，是事故发生的直接背景。\n2. 当事人离开现场虽有程序和行政风险，但需证明其导致救治延误、损害扩大或事故原因无法查明，才可能增强刑法原因力。\n3. 事故认定书内部若存在原因部分与责任结论张力，应申请复核或在刑事程序中充分质证。\n\n三、办理建议\n调取现场证人材料、救护记录、报警时间线和事故复核材料，准备书面意见说明行政责任与刑事责任的评价差异。",
                ),
            ],
            "similar_results": [
                {
                    "title": "事故认定全责与交通肇事罪主要责任的区分",
                    "reference": "演示类案-交-刑责-001",
                    "court_or_authority": "演示案例库",
                    "key_points": [
                        "刑事责任评价应围绕事故原因力和损害结果，不宜机械照搬行政责任结论。",
                        "认定书原因分析与责任结论不一致时，应结合现场证据重新审查主要责任基础。",
                    ],
                },
                {
                    "title": "离开现场行为对交通事故死亡结果的因果力审查",
                    "reference": "演示类案-交-刑责-002",
                    "court_or_authority": "演示案例库",
                    "key_points": [
                        "离开现场是否构成加重评价，取决于是否影响救治、损害扩大或事故原因查明。",
                        "事后逃离与事故发生原因应分层论证。",
                    ],
                },
            ],
            "law_results": [
                {
                    "title": "中华人民共和国刑法第一百三十三条",
                    "reference": "交通肇事罪条款",
                    "court_or_authority": "全国人民代表大会",
                    "key_points": [
                        "违反交通运输管理法规，因而发生重大事故并造成严重后果的，依法追究刑事责任。",
                        "审查重点包括行为违法性、事故结果、责任程度和因果关系。",
                    ],
                },
                {
                    "title": "关于审理交通肇事刑事案件具体应用法律若干问题的解释",
                    "reference": "交通肇事司法解释",
                    "court_or_authority": "最高人民法院",
                    "key_points": [
                        "是否承担主要责任或全部责任，是交通肇事罪入罪判断的重要条件。",
                        "责任判断需结合事故发生原因和证据材料，而非只看单一标签。",
                    ],
                },
            ],
            "risk_level": "high",
        },
        "272": {
            "similar_query": "危险驾驶 醉驾 做局 怂恿 安排车辆 报警 共犯责任",
            "law_query": "危险驾驶罪 醉酒驾驶 共犯 怂恿 诱导 量刑情节",
            "keywords": ["危险驾驶罪", "醉酒驾驶", "共犯", "诱导做局"],
            "document_title": "艾家属危险驾驶共犯责任分析",
            "document_revisions": [
                (
                    "dangerous-driving-facts.txt",
                    "初始醉驾事实整理",
                    "一、事实整理\n家属反映，当事人酒后在高速驾驶被查，血检超过醉驾标准，同时存在他人安排聚餐、陪酒、车辆路线和报警的情况。\n\n二、初步判断\n醉驾事实本身仍有刑事风险，但诱导者是否构成危险驾驶共犯需要单独分析。",
                ),
                (
                    "dangerous-driving-v2.txt",
                    "补充做局链条分析",
                    "一、事实整理\n对方人员安排吃饭和陪酒，承诺叫代驾，后又引导换地点、跟车上高速，并在关键时间报警。\n\n二、法律分析\n危险驾驶罪共犯审查，应看诱导者是否具有促成醉驾的共同意思联络，以及是否实施陪酒、欺骗、安排车辆路线、报警等促成行为。被诱导者仍需面对醉驾事实，但可将被设计、诱导、主动供述等作为责任和量刑评价情节。\n\n三、待补材料\n需固定聊天记录、转账记录、聚餐参与人员陈述、车辆安排记录、报警记录、血检报告和查获地点。",
                ),
                (
                    "dangerous-driving-review.txt",
                    "共犯与量刑复核版",
                    "一、阶段性结论\n本案应区分两条线：当事人醉驾行为的基本刑事风险，以及组织做局人员可能承担的共犯或更重责任。现有陈述显示，若他人以换取从宽处理为目的，连续实施陪酒、欺骗、安排车辆路线并报警，具备共犯审查价值。\n\n二、论证重点\n1. 诱导者是否提前预设目的，并持续推动当事人饮酒后驾驶。\n2. “会叫代驾”“换地方玩”“跟车走高速没事”等话术是否削弱当事人风险判断。\n3. 报警时间、车辆安排和上高速路线能否证明诱导者对醉驾发生具有支配或重要促进作用。\n\n三、办理建议\n先固定电子证据和报警时间线，再准备同步反映做局人员责任的书面材料。对被诱导者部分，应如实说明醉驾事实并重点提出诱导、坦白、配合调查等量刑情节。",
                ),
            ],
            "similar_results": [
                {
                    "title": "危险驾驶案件中组织陪酒并安排车辆路线的共犯责任",
                    "reference": "演示类案-危驾-共犯-001",
                    "court_or_authority": "演示案例库",
                    "key_points": [
                        "对促成醉驾具有明确目的并实施安排、怂恿、报警等行为的人员，可被纳入共犯责任审查。",
                        "组织者的目的、分工、过程控制和报警节点，是判断责任大小的核心事实。",
                    ],
                },
                {
                    "title": "被诱导醉驾人员责任与量刑情节审查",
                    "reference": "演示类案-危驾-量刑-002",
                    "court_or_authority": "演示案例库",
                    "key_points": [
                        "被诱导不当然排除危险驾驶罪风险，但可影响责任评价和量刑建议。",
                        "聊天记录、代驾承诺、路线安排和查获地点能够帮助证明诱导链条。",
                    ],
                },
            ],
            "law_results": [
                {
                    "title": "中华人民共和国刑法第一百三十三条之一",
                    "reference": "危险驾驶罪条款",
                    "court_or_authority": "全国人民代表大会",
                    "key_points": [
                        "在道路上醉酒驾驶机动车，构成危险驾驶罪的基本评价对象。",
                        "高速路段、血检数值、是否造成现实危险和配合调查情况影响处理尺度。",
                    ],
                },
                {
                    "title": "关于办理醉酒危险驾驶刑事案件的意见",
                    "reference": "醉酒危险驾驶办理意见",
                    "court_or_authority": "最高人民法院、最高人民检察院、公安部、司法部",
                    "key_points": [
                        "办理醉酒危险驾驶案件应坚持宽严相济，综合评价行为危险性和从宽从重情节。",
                        "他人组织、指使、强令、怂恿醉酒驾驶的，应关注其在案件形成中的作用。",
                    ],
                },
            ],
            "risk_level": "medium",
        },
    }
    return data[suffix]


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
    sample_task_comments: list[CaseTaskComment] = []
    sample_memories: list[CaseMemory] = []
    sample_followups: list[FollowUpQuestion] = []
    sample_reply_jobs: list[LegalReplyJob] = []
    sample_events: list[ActivityEvent] = []
    sample_documents: list[LegalDocument] = []
    sample_revisions: list[LegalDocumentRevision] = []
    sample_branches: list[LegalDocumentBranch] = []
    sample_diffs: list[LegalDocumentDiff] = []
    sample_analyses: list[LegalDocumentAnalysis] = []
    sample_research_runs: list[LegalResearchRun] = []
    sample_research_results: list[LegalResearchResult] = []
    sample_reasoning_runs: list[LegalReasoningRun] = []
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
                (
                    "wechat_user",
                    "inbound",
                    "学校说监控要等派出所调取，我们手上有孩子脖子和胳膊的伤照，也有两个同学愿意作证。",
                ),
                (
                    "owner",
                    "outbound",
                    "可以。录屏样例里我会把监控、伤照、同学证言和学校记录列成证据清单，再生成正当防卫追问。",
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
                (
                    "wechat_user",
                    "inbound",
                    "现在有事故认定书照片、现场图和救护车到场时间。家属担心认定全责后就没法再解释了。",
                ),
                (
                    "owner",
                    "outbound",
                    "仍然可以解释。我们会把行政全责、事故原因力和刑事主要责任分开分析，并准备补充追问。",
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
                (
                    "wechat_user",
                    "inbound",
                    "我们有饭局前后的聊天记录，对方提过代驾，也有人说已经报警等着查他。",
                ),
                (
                    "owner",
                    "outbound",
                    "这些记录很关键。演示里会把做局链条、共犯责任和被诱导者量刑情节分成三个推理节点。",
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
            last_seen_at=demo_time(9, int(suffix) % 50),
        )
        conversation_item = WechatConversation(
            id=conversation_id,
            openclaw_conversation_id=f"mock_{conversation_id}",
            contact_id=contact_id,
            case_id=case_id,
            status="open",
            last_message_at=demo_time(10, int(suffix) % 50),
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
            created_at=demo_time(9, int(suffix) % 50),
            updated_at=demo_time(11, int(suffix) % 50),
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
                    created_at=demo_time(9, (int(suffix) + index) % 55),
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
                    created_at=demo_time(10, (int(suffix) + index) % 55),
                )
            )

        for index, (title, role, status) in enumerate(spec["tasks"], start=1):
            task_type = "general"
            priority = "medium"
            description = "演示样例预置任务。"
            result_summary = ""
            if index == 1:
                task_type = "general"
                priority = "high"
                description = "整理客户聊天、时间线、证据缺口和已确认事实。"
                result_summary = "已从聊天记录沉淀核心事实和证据缺口，等待补充材料。"
            elif index == 2:
                task_type = "reasoning"
                priority = "high"
                description = "基于案件记忆、聊天和检索结果形成 AOE 推理图。"
                result_summary = "已生成阶段性推理 run，建议主任律师复核争议焦点和追问边界。"
                status = "waiting_owner_review"
            elif index == 3:
                task_type = "client_reply"
                description = "将推理缺口转化为可发送给家属的追问。"
                result_summary = "已生成可发送追问，发送前请核对措辞和材料清单。"
                status = "done"
            sample_tasks.append(
                CaseTask(
                    id=f"task_family_{suffix}_{index}",
                    case_id=case_id,
                    title=str(title),
                    assigned_agent_role=str(role),
                    status=status,  # type: ignore[arg-type]
                    task_type=task_type,  # type: ignore[arg-type]
                    priority=priority,  # type: ignore[arg-type]
                    description=description,
                    result_summary=result_summary,
                    created_at=demo_time(10, (int(suffix) + index + 4) % 55),
                    updated_at=demo_time(11, (int(suffix) + index + 4) % 55),
                )
            )
            if result_summary:
                sample_task_comments.append(
                    CaseTaskComment(
                        id=f"comment_family_{suffix}_{index}",
                        case_id=case_id,
                        task_id=f"task_family_{suffix}_{index}",
                        message=result_summary,
                        author_type="agent",
                        author_label=str(role),
                        created_at=demo_time(11, (int(suffix) + index + 6) % 55),
                    )
                )

        for index, content in enumerate(spec["followups"], start=1):
            sample_followups.append(
                FollowUpQuestion(
                    id=f"followup_family_{suffix}_{index}",
                    case_id=case_id,
                    reasoning_run_id=f"reason_family_{suffix}_1",
                    content=str(content),
                    status="draft",
                    created_at=demo_time(11, (int(suffix) + index + 12) % 55),
                    updated_at=demo_time(11, (int(suffix) + index + 12) % 55),
                )
            )

        enrichment = family_enrichment(suffix)
        doc_id = f"doc_family_{suffix}_opinion"
        main_branch_id = f"branch_family_{suffix}_main"
        review_branch_id = f"branch_family_{suffix}_review"
        revision_ids = [f"rev_family_{suffix}_{index}" for index in range(1, 4)]
        document_item = LegalDocument(
            id=doc_id,
            case_id=case_id,
            title=str(enrichment["document_title"]),
            document_type="pleading",
            current_revision_id=revision_ids[-1],
            default_branch_id=main_branch_id,
            created_at=demo_time(10, (int(suffix) + 15) % 55),
            updated_at=demo_time(11, (int(suffix) + 15) % 55),
        )
        main_branch = LegalDocumentBranch(
            id=main_branch_id,
            document_id=doc_id,
            name="main",
            head_revision_id=revision_ids[1],
            base_revision_id=revision_ids[0],
            is_default=True,
            created_at=demo_time(10, (int(suffix) + 16) % 55),
            updated_at=demo_time(11, (int(suffix) + 16) % 55),
        )
        review_branch = LegalDocumentBranch(
            id=review_branch_id,
            document_id=doc_id,
            name="lawyer-review",
            head_revision_id=revision_ids[2],
            base_revision_id=revision_ids[1],
            is_default=False,
            created_at=demo_time(10, (int(suffix) + 17) % 55),
            updated_at=demo_time(11, (int(suffix) + 17) % 55),
        )
        sample_documents.append(document_item)
        sample_branches.extend([main_branch, review_branch])
        revision_texts: list[str] = []
        for index, (filename, change_summary, content_text) in enumerate(
            enrichment["document_revisions"],  # type: ignore[arg-type]
            start=1,
        ):
            revision_texts.append(str(content_text))
            sample_revisions.append(
                LegalDocumentRevision(
                    id=revision_ids[index - 1],
                    document_id=doc_id,
                    version_number=index,
                    content_text=str(content_text),
                    source_filename=str(filename),
                    author_type="agent" if index > 1 else "import",
                    change_summary=str(change_summary),
                    branch_id=review_branch_id if index == 3 else main_branch_id,
                    parent_revision_id=None if index == 1 else revision_ids[index - 2],
                    created_from_revision_id=None if index == 1 else revision_ids[index - 2],
                    short_hash=f"fam{suffix}{index}",
                    created_at=demo_time(10, (int(suffix) + 18 + index) % 55),
                )
            )

        diff_id = f"diff_family_{suffix}_review"
        risk_summary = summarize_legal_risks(revision_texts[1], revision_texts[2])
        sample_diffs.append(
            LegalDocumentDiff(
                id=diff_id,
                document_id=doc_id,
                base_revision_id=revision_ids[1],
                target_revision_id=revision_ids[2],
                segments=build_char_diff(revision_texts[1], revision_texts[2]),
                paragraph_changes=build_paragraph_diff(revision_texts[1], revision_texts[2]),
                risk_summary=risk_summary,
                created_at=demo_time(11, (int(suffix) + 22) % 55),
            )
        )
        analysis_id = f"analysis_family_{suffix}_review"
        sample_analyses.append(
            LegalDocumentAnalysis(
                id=analysis_id,
                document_id=doc_id,
                base_revision_id=revision_ids[1],
                target_revision_id=revision_ids[2],
                source="rule_fallback",
                risk_level=str(enrichment["risk_level"]),  # type: ignore[arg-type]
                ambiguities=["阶段性意见中仍有事实来源待核对，正式对外前需标明证据依据。"],
                stealth_changes=["主任律师复核版增加了对外表述边界和证据优先级，需确认客户是否接受。"],
                risk_points=risk_summary,
                suggestions=[
                    "录屏时可选择 v2 与 lawyer-review/v3 查看差异。",
                    "正式发送前由承办律师核对事实来源、证据编号和法律依据。",
                ],
                manual_review_checklist=[
                    "核对聊天记录与案件记忆是否能支持阶段性结论。",
                    "核对法规/类案检索结果是否需要替换为真实检索结论。",
                    "核对追问问题是否适合直接发送给家属。",
                ],
                created_at=demo_time(11, (int(suffix) + 23) % 55),
            )
        )

        similar_task_id = f"task_family_{suffix}_similar"
        regulation_task_id = f"task_family_{suffix}_regulation"
        review_task_id = f"task_family_{suffix}_doc_review"
        similar_run_id = f"research_family_{suffix}_similar"
        regulation_run_id = f"research_family_{suffix}_regulation"
        sample_tasks.extend(
            [
                CaseTask(
                    id=similar_task_id,
                    case_id=case_id,
                    title="检索可类比裁判规则",
                    description=str(enrichment["similar_query"]),
                    task_type="similar_case_search",
                    status="done",
                    priority="medium",
                    assigned_agent_role="法律检索 Agent",
                    metadata={
                        "query": enrichment["similar_query"],
                        "keywords": enrichment["keywords"],
                        "run_id": similar_run_id,
                        "demo_seed": True,
                    },
                    result_summary="演示检索已完成：命中 2 条类案规则，已写回案件。",
                    created_at=demo_time(10, (int(suffix) + 24) % 55),
                    updated_at=demo_time(11, (int(suffix) + 24) % 55),
                ),
                CaseTask(
                    id=regulation_task_id,
                    case_id=case_id,
                    title="检索法规与司法政策",
                    description=str(enrichment["law_query"]),
                    task_type="regulation_search",
                    status="done",
                    priority="medium",
                    assigned_agent_role="法律检索 Agent",
                    metadata={
                        "query": enrichment["law_query"],
                        "keywords": enrichment["keywords"],
                        "run_id": regulation_run_id,
                        "demo_seed": True,
                    },
                    result_summary="演示检索已完成：命中 2 条法规/司法政策，已写回案件。",
                    created_at=demo_time(10, (int(suffix) + 25) % 55),
                    updated_at=demo_time(11, (int(suffix) + 25) % 55),
                ),
                CaseTask(
                    id=review_task_id,
                    case_id=case_id,
                    title="审查阶段性意见 v2 与复核版差异",
                    description="比对案件意见 v2 与主任律师复核版，标记新增论证、证据缺口和对外表述边界。",
                    task_type="document_review",
                    status="waiting_owner_review",
                    priority="high",
                    assigned_agent_role="合同审查律师 Agent",
                    document_id=doc_id,
                    base_revision_id=revision_ids[1],
                    target_revision_id=revision_ids[2],
                    metadata={"diff_id": diff_id, "analysis_id": analysis_id, "demo_seed": True},
                    result_summary=f"已生成文档差异和风险分析，风险等级：{enrichment['risk_level']}。",
                    created_at=demo_time(10, (int(suffix) + 26) % 55),
                    updated_at=demo_time(11, (int(suffix) + 26) % 55),
                ),
            ]
        )
        for task_id, message, label in [
            (similar_task_id, "类案检索完成，结果已挂载到任务卡片和检索页。", "法律检索 Agent"),
            (regulation_task_id, "法规检索完成，结果已挂载到任务卡片和检索页。", "法律检索 Agent"),
            (review_task_id, "文档审查完成，等待主任律师确认是否采用复核版。", "合同审查律师 Agent"),
        ]:
            sample_task_comments.append(
                CaseTaskComment(
                    id=f"comment_{task_id}",
                    case_id=case_id,
                    task_id=task_id,
                    message=message,
                    author_type="agent",
                    author_label=label,
                    created_at=demo_time(11, (int(suffix) + 27) % 55),
                )
            )

        sample_research_runs.extend(
            [
                LegalResearchRun(
                    id=similar_run_id,
                    case_id=case_id,
                    task_id=similar_task_id,
                    search_type="similar_case",
                    query=str(enrichment["similar_query"]),
                    keywords=list(enrichment["keywords"]),
                    status="completed",
                    summary="演示类案检索完成，已筛出可用于录屏展示的裁判规则。",
                    result_count=2,
                    created_at=demo_time(10, (int(suffix) + 28) % 55),
                    completed_at=demo_time(10, (int(suffix) + 29) % 55),
                ),
                LegalResearchRun(
                    id=regulation_run_id,
                    case_id=case_id,
                    task_id=regulation_task_id,
                    search_type="regulation",
                    query=str(enrichment["law_query"]),
                    keywords=list(enrichment["keywords"]),
                    status="completed",
                    summary="演示法规检索完成，已筛出可用于录屏展示的法律依据。",
                    result_count=2,
                    created_at=demo_time(10, (int(suffix) + 30) % 55),
                    completed_at=demo_time(10, (int(suffix) + 31) % 55),
                ),
            ]
        )
        for index, result in enumerate(enrichment["similar_results"], start=1):
            sample_research_results.append(
                LegalResearchResult(
                    id=f"result_family_{suffix}_similar_{index}",
                    run_id=similar_run_id,
                    case_id=case_id,
                    task_id=similar_task_id,
                    result_type="similar_case",
                    external_id=f"demo_family_{suffix}_case_{index}",
                    title=str(result["title"]),
                    source="演示类案库",
                    reference=str(result["reference"]),
                    court_or_authority=str(result["court_or_authority"]),
                    relevance_score=0.91 - index * 0.04,
                    key_points=[str(item) for item in result["key_points"]],
                    metadata={"demo_seed": True, "query": enrichment["similar_query"]},
                    verified=False,
                    created_at=demo_time(10, (int(suffix) + 32 + index) % 55),
                )
            )
        for index, result in enumerate(enrichment["law_results"], start=1):
            sample_research_results.append(
                LegalResearchResult(
                    id=f"result_family_{suffix}_law_{index}",
                    run_id=regulation_run_id,
                    case_id=case_id,
                    task_id=regulation_task_id,
                    result_type="regulation",
                    external_id=f"demo_family_{suffix}_law_{index}",
                    title=str(result["title"]),
                    source="演示法规库",
                    reference=str(result["reference"]),
                    court_or_authority=str(result["court_or_authority"]),
                    relevance_score=0.93 - index * 0.04,
                    key_points=[str(item) for item in result["key_points"]],
                    metadata={"demo_seed": True, "query": enrichment["law_query"]},
                    verified=True,
                    created_at=demo_time(10, (int(suffix) + 36 + index) % 55),
                )
            )
        nodes = [
            ReasoningNode(
                id=f"node_family_{suffix}_fact",
                node_type="Fact",
                label="核心事实",
                content=str(spec["memories"][0][1]),
                confidence=0.82,
                source_refs=[f"memory_family_{suffix}_1"],
            ),
            ReasoningNode(
                id=f"node_family_{suffix}_timeline",
                node_type="Timeline",
                label="时间线",
                content=str(spec["memories"][1][1]),
                confidence=0.78,
                source_refs=[f"memory_family_{suffix}_2"],
            ),
            ReasoningNode(
                id=f"node_family_{suffix}_evidence",
                node_type="Evidence",
                label="证据清单",
                content=str(spec["memories"][2][1]),
                confidence=0.74,
                source_refs=[f"memory_family_{suffix}_3", doc_id],
            ),
            ReasoningNode(
                id=f"node_family_{suffix}_issue",
                node_type="Issue",
                label="争议焦点",
                content=str(enrichment["similar_query"]),
                confidence=0.76,
                source_refs=[similar_run_id],
            ),
            ReasoningNode(
                id=f"node_family_{suffix}_rule",
                node_type="Rule",
                label="法规与规则",
                content="；".join(result.title for result in sample_research_results if result.case_id == case_id and result.result_type == "regulation")[:260],
                confidence=0.79,
                source_refs=[regulation_run_id],
            ),
            ReasoningNode(
                id=f"node_family_{suffix}_analysis",
                node_type="Analysis",
                label="阶段分析",
                content=str(revision_texts[2]).split("二、论证重点")[0].strip(),
                confidence=0.72,
                source_refs=[doc_id, diff_id],
            ),
            ReasoningNode(
                id=f"node_family_{suffix}_conclusion",
                node_type="Conclusion",
                label="阶段结论",
                content="可以用于录屏展示的阶段性判断已生成，但正式对外前仍需补齐证据并人工复核。",
                confidence=0.68,
                source_refs=[analysis_id],
            ),
            ReasoningNode(
                id=f"node_family_{suffix}_uncertainty",
                node_type="Uncertainty",
                label="待补强点",
                content=str(spec["memories"][3][1]),
                confidence=0.88,
                source_refs=[f"memory_family_{suffix}_4"],
            ),
            ReasoningNode(
                id=f"node_family_{suffix}_question",
                node_type="Question",
                label="可发送追问",
                content="；".join(str(item) for item in spec["followups"]),
                confidence=0.9,
                source_refs=[f"followup_family_{suffix}_1", f"followup_family_{suffix}_2"],
            ),
        ]
        sample_reasoning_runs.append(
            LegalReasoningRun(
                id=f"reason_family_{suffix}_1",
                case_id=case_id,
                status="needs_evidence",
                input_summary=case_item.summary,
                nodes=nodes,
                edges=[
                    ReasoningEdge(id=f"edge_family_{suffix}_fact_issue", source=nodes[0].id, target=nodes[3].id, relation_type="supports"),
                    ReasoningEdge(id=f"edge_family_{suffix}_timeline_issue", source=nodes[1].id, target=nodes[3].id, relation_type="supports"),
                    ReasoningEdge(id=f"edge_family_{suffix}_evidence_analysis", source=nodes[2].id, target=nodes[5].id, relation_type="supports"),
                    ReasoningEdge(id=f"edge_family_{suffix}_issue_rule", source=nodes[3].id, target=nodes[4].id, relation_type="requires"),
                    ReasoningEdge(id=f"edge_family_{suffix}_rule_analysis", source=nodes[4].id, target=nodes[5].id, relation_type="supports"),
                    ReasoningEdge(id=f"edge_family_{suffix}_analysis_conclusion", source=nodes[5].id, target=nodes[6].id, relation_type="leads_to"),
                    ReasoningEdge(id=f"edge_family_{suffix}_analysis_uncertainty", source=nodes[5].id, target=nodes[7].id, relation_type="uncertain_about"),
                    ReasoningEdge(id=f"edge_family_{suffix}_uncertainty_question", source=nodes[7].id, target=nodes[8].id, relation_type="asks"),
                ],
                follow_up_questions=[str(item) for item in spec["followups"]],
                blocked_reason=str(spec["memories"][3][1]),
                review_focus=["事实来源", "证据缺口", "法规适用", "对外表述边界"],
                output_summary=f"已预置 {len(nodes)} 个推理节点、8 条关系和 {len(spec['followups'])} 个可发送追问。",
                created_at=demo_time(11, (int(suffix) + 40) % 55),
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
                created_at=demo_time(11, (int(suffix) + 41) % 55),
                updated_at=demo_time(11, (int(suffix) + 41) % 55),
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
        "openclaw_connection": OpenClawConnection(transport_mode="mock").model_dump(),
        "wechat_contacts": [contact.model_dump(), *[item.model_dump() for item in sample_contacts]],
        "wechat_conversations": [conversation.model_dump(), *[item.model_dump() for item in sample_conversations]],
        "wechat_messages": [message.model_dump() for message in messages + sample_messages],
        "cases": [case.model_dump(), *[item.model_dump() for item in sample_cases]],
        "case_tasks": [task.model_dump() for task in tasks + sample_tasks],
        "case_task_comments": [comment.model_dump() for comment in sample_task_comments],
        "case_memories": [memory.model_dump() for memory in memories + sample_memories],
        "legal_agents": [agent.model_dump() for agent in agents],
        "legal_documents": [document.model_dump(), *[item.model_dump() for item in sample_documents]],
        "legal_document_revisions": [revision.model_dump() for revision in revisions + sample_revisions],
        "legal_document_branches": [main_branch.model_dump(), *[item.model_dump() for item in sample_branches]],
        "legal_document_diffs": [item.model_dump() for item in sample_diffs],
        "legal_document_analyses": [item.model_dump() for item in sample_analyses],
        "legal_research_runs": [item.model_dump() for item in sample_research_runs],
        "legal_research_results": [item.model_dump() for item in sample_research_results],
        "legal_reasoning_runs": [item.model_dump() for item in sample_reasoning_runs],
        "follow_up_questions": [question.model_dump() for question in sample_followups],
        "reply_jobs": [job.model_dump() for job in reply_jobs + sample_reply_jobs],
        "activity_events": [event.model_dump() for event in events + sample_events],
    }
