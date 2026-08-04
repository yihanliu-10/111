"""Agent 调用入口，含 mock 路径。

mock 路径完全确定性，不发起任何网络调用，用于验证状态机 / 校验 / 审计。
mock 裁判首次刻意越档（若存在更高档位），以演练 S5 打回-修正闭环。
"""

from .llm import call_structured
from .policy import Policy
from .prompts import judge_prompt, opening_prompt, rebuttal_prompt
from .schemas import CasePacket, Opening, Rebuttal, Verdict

# ---------- 真实调用 ----------


def run_opening(
    role: str, packet: CasePacket, policy: Policy, grade: str, mock: bool
) -> Opening:
    if mock:
        return _mock_opening(role, packet, policy, grade)
    system, user = opening_prompt(role, packet, policy, grade)
    return call_structured(system, user, Opening)


def run_rebuttal(
    role: str,
    packet: CasePacket,
    policy: Policy,
    own: Opening,
    other: Opening,
    mock: bool,
) -> Rebuttal:
    if mock:
        return _mock_rebuttal(role, packet, policy, own, other)
    system, user = rebuttal_prompt(role, packet, policy, own, other)
    return call_structured(system, user, Rebuttal)


def run_judge(
    packet: CasePacket,
    policy: Policy,
    grade: str,
    transcript: str,
    mock: bool,
    violation: str | None = None,
) -> Verdict:
    if mock:
        return _mock_verdict(packet, policy, grade, violation)
    system, user = judge_prompt(packet, policy, grade, transcript, violation)
    return call_structured(system, user, Verdict)


# ---------- mock 路径（确定性） ----------


def _cap_tier(policy: Policy, grade: str) -> str | None:
    return policy.grade_tier_cap[grade]


def _shap_lines(packet: CasePacket, head: str) -> list[str]:
    return [
        f"{s.feature}={s.value}（SHAP {s.contribution:+.3f}）"
        for s in packet.shap_top
        if s.head == head
    ]


def _mock_opening(role, packet, policy, grade) -> Opening:
    cap = _cap_tier(policy, grade) or "T1"
    if role == "marketing":
        return Opening(
            proposed_action="APPROVE",
            proposed_tier=cap,
            stance_summary=f"意愿充足，建议按 {grade} 级上限批 {cap}",
            arguments=[f"意愿证据：{x}" for x in _shap_lines(packet, "want")]
            + [f"p_want={packet.scores.p_want:.3f} 高于灰区均值，转化概率大"],
            confidence=0.7,
        )
    # 风控：风险偏高则拒绝，否则同意按上限批（与营销收敛）
    if packet.scores.p_risk >= 0.10:
        return Opening(
            proposed_action="REJECT",
            proposed_tier=None,
            stance_summary=f"{grade} 级风险偏高，建议拒绝",
            arguments=[f"风险证据：{x}" for x in _shap_lines(packet, "risk")]
            + [f"p_risk={packet.scores.p_risk:.3f} 接近硬拒绝线，政策偏好稳健"],
            confidence=0.65,
        )
    return Opening(
        proposed_action="APPROVE",
        proposed_tier=cap,
        stance_summary=f"风险可控，可按 {grade} 级上限批 {cap}",
        arguments=[f"风险证据：{x}" for x in _shap_lines(packet, "risk")]
        + [f"p_risk={packet.scores.p_risk:.3f} 距硬拒绝线尚远"],
        confidence=0.7,
    )


def _mock_rebuttal(role, packet, policy, own, other) -> Rebuttal:
    cap = _cap_tier(policy, "C") or "T1"
    if role == "risk" and packet.scores.p_want >= 0.70:
        # 高意愿灰区：风控有条件让步，同意最低档试探性授信
        return Rebuttal(
            concede=True,
            counterpoints=[
                f"营销方 p_want={packet.scores.p_want:.3f} 的意愿证据成立",
                "但风险证据未被推翻，只接受最低档位授信以控制敞口",
            ],
            updated_action="APPROVE",
            updated_tier=cap,
            confidence=0.6,
        )
    return Rebuttal(
        concede=False,
        counterpoints=[f"对方论点『{other.stance_summary}』未改变本方证据权重"],
        updated_action=own.proposed_action,
        updated_tier=own.proposed_tier,
        confidence=own.confidence,
    )


def _mock_verdict(packet, policy, grade, violation) -> Verdict:
    cap = _cap_tier(policy, grade)
    if cap is None:
        return Verdict(
            decision="REJECT",
            tier=None,
            rationale=f"{grade} 级不可自动批准，且风险证据占优",
            key_factors=[f"p_risk={packet.scores.p_risk:.3f}", f"风险等级 {grade}"],
            accepted_from_marketing=[],
            accepted_from_risk=["风险头 SHAP 证据"],
        )
    tiers = list(policy.tiers)
    if violation is None and policy.tier_rank(cap) + 1 < len(tiers):
        # 首次刻意越档一级，触发 S5 打回，演练修正闭环
        over = tiers[policy.tier_rank(cap) + 1]
        return Verdict(
            decision="APPROVE",
            tier=over,
            rationale=f"意愿证据充分，批 {over}（mock：演示越档被校验打回）",
            key_factors=[f"p_want={packet.scores.p_want:.3f}"],
            accepted_from_marketing=["意愿头 SHAP 证据"],
            accepted_from_risk=[],
        )
    return Verdict(
        decision="APPROVE",
        tier=cap,
        rationale=(
            f"意愿证据充分且风险未触硬线，按 {grade} 级上限批 {cap}；"
            "采纳风控方降档控敞口意见"
        ),
        key_factors=[
            f"p_want={packet.scores.p_want:.3f}",
            f"p_risk={packet.scores.p_risk:.3f}",
            f"等级上限 {cap}",
        ],
        accepted_from_marketing=["意愿头 SHAP 证据"],
        accepted_from_risk=["降档控制敞口"],
    )
