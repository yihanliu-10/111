"""S1 硬规则闸门：纯代码，零 LLM 成本。

优先级：硬拒绝线 > 快速通过 > 灰区（进入辩论）。
"""

from .policy import Policy
from .schemas import CasePacket, GateResult


def run_gate(packet: CasePacket, policy: Policy) -> GateResult:
    p_want, p_risk = packet.scores.p_want, packet.scores.p_risk
    grade = policy.grade_of(p_risk)

    if p_risk >= policy.hard_reject_risk:
        return GateResult(
            decision="AUTO_REJECT",
            grade=grade,
            reason=f"p_risk={p_risk:.3f} 触及硬拒绝线 {policy.hard_reject_risk}",
        )

    if (
        p_risk <= policy.auto_approve_max_risk
        and p_want >= policy.auto_approve_min_want
    ):
        tier = policy.grade_tier_cap[grade]
        return GateResult(
            decision="AUTO_APPROVE",
            tier=tier,
            grade=grade,
            reason=(
                f"p_risk={p_risk:.3f}<= {policy.auto_approve_max_risk} 且 "
                f"p_want={p_want:.3f}>= {policy.auto_approve_min_want}，"
                f"按 {grade} 级上限批 {tier}"
            ),
        )

    return GateResult(
        decision=None,
        grade=grade,
        reason=f"灰区案件（{grade} 级，p_want={p_want:.3f}），进入辩论流程",
    )
