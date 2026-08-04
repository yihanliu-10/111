"""案件包 / 辩论输出 / 裁决的 Pydantic 模型。

Opening / Rebuttal / Verdict 三个模型同时作为 LLM 结构化输出 schema
（经 client.messages.parse 的 output_format 传给 API），因此字段保持扁平、
不用递归结构，Optional 字段显式给默认值。
"""

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

Role = Literal["marketing", "risk"]
Action = Literal["APPROVE", "REJECT"]
Decision = Literal["APPROVE", "REJECT", "MANUAL_REVIEW"]
Tier = Literal["T1", "T2", "T3"]


# ---------- 案件包（输入侧，非 LLM 输出） ----------

class Scores(BaseModel):
    p_want: float = Field(description="双头模型意愿头输出，0-1")
    p_risk: float = Field(description="双头模型风险头输出，0-1，越大越差")


class ShapItem(BaseModel):
    head: Literal["want", "risk"]
    feature: str
    value: Any
    contribution: float = Field(description="SHAP 贡献值，正向推高该头得分")


class CasePacket(BaseModel):
    case_id: str
    applicant: dict[str, Any]
    scores: Scores
    shap_top: list[ShapItem]
    policy_version: str


# ---------- 辩论输出（LLM 结构化输出 schema） ----------

class Opening(BaseModel):
    """S2 独立立论。"""

    proposed_action: Action
    proposed_tier: Optional[Tier] = Field(
        default=None, description="仅 APPROVE 时给出建议档位"
    )
    stance_summary: str = Field(description="一句话立场")
    arguments: list[str] = Field(
        description="论点列表，每条必须引用案件包中的具体证据（分数/SHAP/政策条款）"
    )
    confidence: float = Field(description="对自身立场的置信度 0-1")


class Rebuttal(BaseModel):
    """S3 反驳轮。"""

    concede: bool = Field(description="是否被对方说服而调整立场")
    counterpoints: list[str] = Field(description="针对对方论点的逐条回应")
    updated_action: Action
    updated_tier: Optional[Tier] = Field(default=None)
    confidence: float


class Verdict(BaseModel):
    """S4 裁判裁决。"""

    decision: Decision
    tier: Optional[Tier] = Field(
        default=None, description="仅 APPROVE 时给出，须符合政策档位与等级上限"
    )
    rationale: str = Field(description="裁决理由，须落到具体证据与政策条款")
    key_factors: list[str] = Field(description="决定性因素")
    accepted_from_marketing: list[str] = Field(description="采纳的营销方论点")
    accepted_from_risk: list[str] = Field(description="采纳的风控方论点")


# ---------- 过程记录（审计用） ----------

class GateResult(BaseModel):
    decision: Optional[Literal["AUTO_APPROVE", "AUTO_REJECT"]] = None
    tier: Optional[Tier] = None
    grade: str
    reason: str
