"""S6 审计落盘：每案一个 JSON，含完整辩论记录与校验轨迹。"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

AUDIT_DIR = Path(__file__).resolve().parent.parent / "audit"


def write_audit(record: dict[str, Any]) -> Path:
    AUDIT_DIR.mkdir(exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = AUDIT_DIR / f"{record['case_id']}_{ts}.json"
    path.write_text(
        json.dumps(record, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    return path
