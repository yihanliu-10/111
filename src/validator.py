"""S5 确定性校验：档位 / 等级边界 / 硬线双保险。

裁判是 LLM，闸门是代码；这里用纯代码把政策硬约束再兜一遍底。
返回违规项列表，空列表即通过。
"""

from .policy import Policy
from .schemas import CasePacket, Verdict


def validate_verdict(
    verdict: Verdict, packet: CasePacket, policy: Policy
) -> list[str]:
    violations: list[str] = []
    p_risk = packet.scores.p_risk
    grade = policy.grade_of(p_risk)

    if verdict.decision == "APPROVE":
        if p_risk >= policy.hard_reject_risk:
            violations.append(
                f"硬线违规：p_risk={p_risk:.3f} >= 硬拒绝线 {policy.hard_reject_risk}，不得批准"
            )
        if verdict.tier is None:
            violations.append("档位缺失：APPROVE 必须给出 tier")
        elif verdict.tier not in policy.tiers:
            violations.append(f"档位非法：{verdict.tier} 不在政策档位 {list(policy.tiers)} 中")
        else:
            cap = policy.grade_tier_cap[grade]
            if cap is None:
                violations.append(f"等级违规：{grade} 级不可自动批准")
            elif policy.tier_rank(verdict.tier) > policy.tier_rank(cap):
                violations.append(
                    f"越档违规：{grade} 级上限为 {cap}，裁决给出 {verdict.tier}"
                )
    else:
        if verdict.tier is not None:
            violations.append(
                f"字段冲突：{verdict.decision} 时 tier 必须为空，实际为 {verdict.tier}"
            )

    return violations
