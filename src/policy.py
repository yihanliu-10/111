"""当期政策：档位、等级边界、风险偏好、闸门参数。政策变了只改这里。"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class Policy:
    version: str
    # 额度档位（元）
    tiers: dict[str, int]
    # 风险等级上界（含）：p_risk 落在哪个区间即为哪个等级，按顺序取第一个满足的
    grade_bounds: tuple[tuple[str, float], ...]
    # 各等级可批的最高档位；None 表示该等级不可自动批准
    grade_tier_cap: dict[str, Optional[str]]
    # 硬拒绝线：p_risk >= 此值直接 AUTO_REJECT，任何角色不得越线批准
    hard_reject_risk: float
    # 快速通过：p_risk <= max_risk 且 p_want >= min_want
    auto_approve_max_risk: float
    auto_approve_min_want: float
    # 风险偏好描述（进入 prompt）
    risk_appetite: str = ""

    def grade_of(self, p_risk: float) -> str:
        for grade, upper in self.grade_bounds:
            if p_risk < upper:
                return grade
        return self.grade_bounds[-1][0]

    def tier_rank(self, tier: str) -> int:
        return list(self.tiers).index(tier)


CURRENT_POLICY = Policy(
    version="2026Q3-v1",
    tiers={"T1": 10_000, "T2": 30_000, "T3": 50_000},
    grade_bounds=(("A", 0.05), ("B", 0.10), ("C", 0.20), ("D", 1.01)),
    grade_tier_cap={"A": "T3", "B": "T2", "C": "T1", "D": None},
    hard_reject_risk=0.25,
    auto_approve_max_risk=0.05,
    auto_approve_min_want=0.60,
    risk_appetite="稳健：优先控制不良率；灰区案件宁可降档批准，不可越级授信。",
)


def policy_digest(p: Policy) -> str:
    """政策的可读摘要，进入各角色 prompt。"""
    tiers = "、".join(f"{k}={v:,}元" for k, v in p.tiers.items())
    grades = "；".join(
        f"{g}级: p_risk<{u}" for g, u in p.grade_bounds[:-1]
    ) + f"；{p.grade_bounds[-1][0]}级: 其余"
    caps = "；".join(
        f"{g}级最高可批{c or '不可批（转人工或拒绝）'}" for g, c in p.grade_tier_cap.items()
    )
    return (
        f"政策版本 {p.version}\n"
        f"额度档位：{tiers}\n"
        f"风险等级：{grades}\n"
        f"等级档位上限：{caps}\n"
        f"硬拒绝线：p_risk >= {p.hard_reject_risk} 一律拒绝，不得例外\n"
        f"风险偏好：{p.risk_appetite}"
    )
