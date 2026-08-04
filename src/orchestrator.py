"""状态机：S1 闸门 → S2 立论 → S3 反驳 → S4 裁决 → S5 校验 → S6 审计。"""

from datetime import datetime, timezone
from typing import Any

from .agents import run_judge, run_opening, run_rebuttal
from .audit import write_audit
from .gate import run_gate
from .policy import Policy
from .schemas import CasePacket, Opening, Rebuttal, Verdict


def _converged(m: Opening, r: Opening) -> bool:
    """立论已收敛：处置一致且档位一致，反驳轮无信息增量，跳过 S3。"""
    return m.proposed_action == r.proposed_action and m.proposed_tier == r.proposed_tier


def _transcript(
    m_open: Opening,
    r_open: Opening,
    m_reb: Rebuttal | None,
    r_reb: Rebuttal | None,
) -> str:
    parts = [
        f"[营销代理·立论] {m_open.model_dump_json()}",
        f"[风控代理·立论] {r_open.model_dump_json()}",
    ]
    if m_reb and r_reb:
        parts += [
            f"[营销代理·反驳] {m_reb.model_dump_json()}",
            f"[风控代理·反驳] {r_reb.model_dump_json()}",
        ]
    else:
        parts.append("[系统] 双方立论已收敛，跳过反驳轮。")
    return "\n".join(parts)


def run_case(packet: CasePacket, policy: Policy, mock: bool) -> dict[str, Any]:
    from .validator import validate_verdict

    log = lambda msg: print(f"  {msg}")
    record: dict[str, Any] = {
        "case_id": packet.case_id,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "mode": "mock" if mock else "live",
        "policy_version": policy.version,
        "case_packet": packet.model_dump(),
    }

    # S1 硬规则闸门
    gate = run_gate(packet, policy)
    record["gate"] = gate.model_dump()
    log(f"S1 闸门：{gate.reason}")
    if gate.decision is not None:
        record["final"] = {
            "decision": gate.decision,
            "tier": gate.tier,
            "decided_by": "gate",
        }
        record["audit_path"] = str(write_audit(record))
        return record

    # S2 独立立论
    m_open = run_opening("marketing", packet, policy, gate.grade, mock)
    r_open = run_opening("risk", packet, policy, gate.grade, mock)
    record["openings"] = {
        "marketing": m_open.model_dump(),
        "risk": r_open.model_dump(),
    }
    log(f"S2 立论：营销 {m_open.proposed_action}/{m_open.proposed_tier}，"
        f"风控 {r_open.proposed_action}/{r_open.proposed_tier}")

    # S3 反驳轮（最多 1 轮，收敛则跳过）
    m_reb = r_reb = None
    if _converged(m_open, r_open):
        log("S3 反驳：立论已收敛，跳过")
        record["rebuttals"] = None
    else:
        m_reb = run_rebuttal("marketing", packet, policy, m_open, r_open, mock)
        r_reb = run_rebuttal("risk", packet, policy, r_open, m_open, mock)
        record["rebuttals"] = {
            "marketing": m_reb.model_dump(),
            "risk": r_reb.model_dump(),
        }
        log(f"S3 反驳：营销 {m_reb.updated_action}/{m_reb.updated_tier}"
            f"（让步={m_reb.concede}），风控 {r_reb.updated_action}/{r_reb.updated_tier}"
            f"（让步={r_reb.concede}）")

    transcript = _transcript(m_open, r_open, m_reb, r_reb)

    # S4 裁决 + S5 确定性校验（违规打回一次，再违规转人工）
    attempts: list[dict[str, Any]] = []
    verdict: Verdict | None = None
    violation_text: str | None = None
    for attempt in (1, 2):
        verdict = run_judge(
            packet, policy, gate.grade, transcript, mock, violation=violation_text
        )
        violations = validate_verdict(verdict, packet, policy)
        attempts.append(
            {"verdict": verdict.model_dump(), "violations": violations}
        )
        if not violations:
            log(f"S4/S5 裁决（第{attempt}次）：{verdict.decision}/{verdict.tier}，校验通过")
            break
        violation_text = "\n".join(f"- {v}" for v in violations)
        log(f"S5 校验（第{attempt}次）未通过：{'；'.join(violations)}")
    record["judge_attempts"] = attempts

    if attempts[-1]["violations"]:
        log("S5 二次违规，转人工")
        record["final"] = {
            "decision": "MANUAL_REVIEW",
            "tier": None,
            "decided_by": "validator_escalation",
            "reason": "裁决两次未通过确定性校验",
        }
    else:
        assert verdict is not None
        record["final"] = {
            "decision": verdict.decision,
            "tier": verdict.tier,
            "decided_by": "judge",
        }

    # S6 审计落盘
    record["audit_path"] = str(write_audit(record))
    return record
