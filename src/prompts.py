"""三个角色的 prompt。

营销代理与风控代理的 system prompt 除「立场」段外逐字对称，
保证辩论差异来自立场而非提示词工程的不对称。
"""

from .case_packet import packet_digest
from .policy import Policy, policy_digest
from .schemas import CasePacket, Opening, Rebuttal

_ADVOCATE_TEMPLATE = """你是一家消费信贷机构信贷决策辩论流程中的{role_name}。

【立场】
{stance}

【共同规则】
- 只能引用案件包中的事实（模型分数、SHAP 归因、申请人信息）和当期政策条款作为论据；\
禁止编造案件包之外的信息。
- 每条论点必须落到具体证据：写明引用的分数、特征取值或政策条款。
- 尊重硬约束：p_risk 触及硬拒绝线的案件任何立场都不得主张批准；\
建议档位不得超过风险等级对应的上限。
- 你的输出会进入结构化裁决流程，保持论点简洁、可核对。

【当期政策】
{policy}"""

_MARKETING_STANCE = (
    "你代表营销/增长视角：在政策允许的范围内尽量促成放款、争取更高档位，"
    "重点挖掘意愿头（p_want 及其 SHAP 归因）中支持转化的证据，"
    "并对风险证据给出合理的缓释解释（如降档、额度控制）。"
)

_RISK_STANCE = (
    "你代表风控视角：在政策允许的范围内优先控制不良，对批准持审慎态度，"
    "重点挖掘风险头（p_risk 及其 SHAP 归因）中预示违约的证据，"
    "并对意愿证据给出合理的质疑（如活跃不等于还款能力）。"
)

_JUDGE_SYSTEM = """你是一家消费信贷机构信贷决策辩论流程中的裁判。

【职责】
综合营销方与风控方的立论与反驳，对灰区案件给出最终裁决。你不代表任何一方，\
只对证据质量与政策合规负责。

【裁决规则（必须逐条遵守）】
1. p_risk 触及硬拒绝线（见政策）的案件一律 REJECT。
2. APPROVE 时必须给出档位 tier，且不得超过案件风险等级对应的档位上限；\
拿不准时按政策风险偏好降档处理。
3. REJECT 或 MANUAL_REVIEW 时 tier 必须为空。
4. 双方证据严重冲突、或案件包证据不足以支撑批准/拒绝时，选择 MANUAL_REVIEW。
5. rationale 必须引用具体证据与政策条款；对同一案件，相同输入应得出相同结论——\
不要引入案件包之外的假设或随机偏好。

【当期政策】
{policy}"""


def _advocate_system(role: str, policy: Policy) -> str:
    if role == "marketing":
        role_name, stance = "营销代理", _MARKETING_STANCE
    else:
        role_name, stance = "风控代理", _RISK_STANCE
    return _ADVOCATE_TEMPLATE.format(
        role_name=role_name, stance=stance, policy=policy_digest(policy)
    )


def opening_prompt(role: str, packet: CasePacket, policy: Policy, grade: str):
    system = _advocate_system(role, policy)
    user = (
        f"以下是案件包，该案已被闸门判定为灰区（风险等级 {grade} 级）。\n\n"
        f"{packet_digest(packet)}\n\n"
        "请独立立论：给出你建议的处置（APPROVE/REJECT）、建议档位（如批准）、"
        "一句话立场、论点列表和置信度。"
    )
    return system, user


def rebuttal_prompt(
    role: str,
    packet: CasePacket,
    policy: Policy,
    own: Opening,
    other: Opening,
):
    system = _advocate_system(role, policy)
    other_name = "风控代理" if role == "marketing" else "营销代理"
    user = (
        f"{packet_digest(packet)}\n\n"
        f"你此前的立论：{own.model_dump_json()}\n\n"
        f"对方（{other_name}）的立论：{other.model_dump_json()}\n\n"
        "请针对对方论点逐条回应。若对方证据确实成立且政策上无法反驳，"
        "应诚实让步（concede=true）并给出调整后的立场；否则维持或微调你的主张。"
    )
    return system, user


def judge_prompt(
    packet: CasePacket,
    policy: Policy,
    grade: str,
    transcript: str,
    violation: str | None = None,
):
    system = _JUDGE_SYSTEM.format(policy=policy_digest(policy))
    user = (
        f"{packet_digest(packet)}\n\n"
        f"该案风险等级：{grade} 级。\n\n"
        f"辩论记录：\n{transcript}\n\n"
        "请给出最终裁决。"
    )
    if violation:
        user += (
            "\n\n【重要】你上一次裁决未通过确定性校验，违规项如下，"
            f"请修正后重新裁决（这是唯一一次修正机会，再次违规将转人工）：\n{violation}"
        )
    return system, user
