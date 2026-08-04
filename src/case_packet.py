"""案件包组装。

demo 阶段从 data/mock_cases.json 读取手工案件；接真模型时，把 load_cases
的数据源换成 LightGBM 双头预测 + SHAP 归因即可，下游不感知。
"""

import json
from pathlib import Path

from .policy import Policy
from .schemas import CasePacket, Scores, ShapItem

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "mock_cases.json"


def load_cases(policy: Policy, path: Path = DATA_PATH) -> list[CasePacket]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    packets = []
    for item in raw:
        packets.append(
            CasePacket(
                case_id=item["case_id"],
                applicant=item["applicant"],
                scores=Scores(**item["scores"]),
                shap_top=[ShapItem(**s) for s in item["shap_top"]],
                policy_version=policy.version,
            )
        )
    return packets


def packet_digest(packet: CasePacket) -> str:
    """案件包的可读摘要，进入各角色 prompt。"""
    lines = [
        f"案件号：{packet.case_id}",
        f"申请人信息：{json.dumps(packet.applicant, ensure_ascii=False)}",
        f"模型分数：p_want(意愿)={packet.scores.p_want:.3f}，p_risk(风险)={packet.scores.p_risk:.3f}",
        "SHAP 头部归因（正贡献推高该头得分）：",
    ]
    for s in packet.shap_top:
        head = "意愿头" if s.head == "want" else "风险头"
        lines.append(f"  - [{head}] {s.feature}={s.value}，贡献 {s.contribution:+.3f}")
    return "\n".join(lines)
