from __future__ import annotations

from difflib import SequenceMatcher

from app.models import DiffSegment, ParagraphChange


LEGAL_RISK_KEYWORDS = {
    "付款": "付款安排发生变化，需要核对金额、期限和付款条件。",
    "金额": "金额条款发生变化，可能影响主给付义务或违约责任。",
    "违约": "违约责任条款发生变化，需要评估责任范围和赔偿上限。",
    "解除": "解除条件发生变化，可能影响合同退出路径。",
    "管辖": "管辖条款发生变化，可能影响争议解决成本和地点。",
    "仲裁": "争议解决方式发生变化，需要确认是否排除法院管辖。",
    "保密": "保密义务发生变化，需要核对义务主体、期限和例外。",
    "责任": "责任承担条款发生变化，需要关注免责和限责内容。",
    "期限": "期限条款发生变化，需要核对是否改变履行、通知、解除或追责节点。",
    "通知": "通知方式或通知期限发生变化，可能影响送达和违约起算。",
    "赔偿": "赔偿条款发生变化，需要关注赔偿范围、上限和证明责任。",
    "免责": "免责或限责条款发生变化，可能削弱追责空间。",
    "知识产权": "知识产权归属或授权范围发生变化，需要核对权利转让和使用限制。",
    "个人信息": "个人信息或隐私条款发生变化，需要关注合规义务和授权范围。",
}


def build_char_diff(base: str, target: str) -> list[DiffSegment]:
    matcher = SequenceMatcher(a=base, b=target)
    segments: list[DiffSegment] = []
    for op, i1, i2, j1, j2 in matcher.get_opcodes():
        if op == "equal":
            segments.append(DiffSegment(op="equal", text=base[i1:i2]))
        elif op == "delete":
            segments.append(DiffSegment(op="delete", text=base[i1:i2]))
        elif op == "insert":
            segments.append(DiffSegment(op="insert", text=target[j1:j2]))
        elif op == "replace":
            if base[i1:i2]:
                segments.append(DiffSegment(op="delete", text=base[i1:i2]))
            if target[j1:j2]:
                segments.append(DiffSegment(op="insert", text=target[j1:j2]))
    return _merge_adjacent(segments)


def build_paragraph_diff(base: str, target: str) -> list[ParagraphChange]:
    base_parts = [part.strip() for part in base.splitlines() if part.strip()]
    target_parts = [part.strip() for part in target.splitlines() if part.strip()]
    matcher = SequenceMatcher(a=base_parts, b=target_parts)
    changes: list[ParagraphChange] = []
    for op, i1, i2, j1, j2 in matcher.get_opcodes():
        if op == "equal":
            for left, right in zip(base_parts[i1:i2], target_parts[j1:j2], strict=False):
                changes.append(ParagraphChange(op="equal", base=left, target=right))
        elif op == "delete":
            for left in base_parts[i1:i2]:
                changes.append(ParagraphChange(op="delete", base=left))
        elif op == "insert":
            for right in target_parts[j1:j2]:
                changes.append(ParagraphChange(op="insert", target=right))
        elif op == "replace":
            changes.append(
                ParagraphChange(
                    op="replace",
                    base="\n".join(base_parts[i1:i2]),
                    target="\n".join(target_parts[j1:j2]),
                )
            )
    return changes


def summarize_legal_risks(base: str, target: str) -> list[str]:
    matcher = SequenceMatcher(a=base, b=target)
    changed_text = "\n".join(
        f"{base[max(0, i1 - 12): min(len(base), i2 + 12)]}\n"
        f"{target[max(0, j1 - 12): min(len(target), j2 + 12)]}"
        for op, i1, i2, j1, j2 in matcher.get_opcodes()
        if op != "equal"
    )
    risks = [
        message
        for keyword, message in LEGAL_RISK_KEYWORDS.items()
        if keyword in changed_text
    ]
    if "30日" in changed_text or "7日" in changed_text:
        risks.append("履行期限发生变化，需要核对是否影响催告、违约起算和付款安排。")
    if "不超过" in changed_text or "上限" in changed_text:
        risks.append("责任上限发生变化，需要确认是否削弱赔偿或追责空间。")
    if not risks:
        risks.append("发现文本变化，请人工核对是否影响权利义务、履行期限或争议解决。")
    return list(dict.fromkeys(risks))[:6]


def build_changed_text_for_analysis(base: str, target: str, limit: int = 6000) -> str:
    matcher = SequenceMatcher(a=base, b=target)
    parts: list[str] = []
    for op, i1, i2, j1, j2 in matcher.get_opcodes():
        if op == "equal":
            continue
        ctx_start = max(0, i1 - 40)
        ctx_end = min(len(base), i2 + 40)
        ctx_start_t = max(0, j1 - 40)
        ctx_end_t = min(len(target), j2 + 40)
        part = f"[删除] {base[ctx_start:ctx_end]}\n[新增] {target[ctx_start_t:ctx_end_t]}"
        parts.append(part)
        if sum(len(p) for p in parts) >= limit:
            break
    result = "\n---\n".join(parts)
    return result[:limit]


def _merge_adjacent(segments: list[DiffSegment]) -> list[DiffSegment]:
    merged: list[DiffSegment] = []
    for segment in segments:
        if not segment.text:
            continue
        if merged and merged[-1].op == segment.op:
            merged[-1].text += segment.text
        else:
            merged.append(segment)
    return merged
