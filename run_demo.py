#!/usr/bin/env python3
"""多智能体信贷决策 demo 入口。

用法：
    python run_demo.py --mock                       # 全部案件走确定性 mock，零 token
    python run_demo.py --case C003_灰区_高意愿高风险  # 单案真实调用（需 API 凭证）
    python run_demo.py --mock --case C004_灰区_低意愿低风险
"""

import argparse
import sys

from src.case_packet import load_cases
from src.orchestrator import run_case
from src.policy import CURRENT_POLICY


def main() -> int:
    parser = argparse.ArgumentParser(description="多智能体信贷决策 demo")
    parser.add_argument(
        "--mock", action="store_true",
        help="确定性 mock，不调用 LLM（验证状态机/校验/审计）",
    )
    parser.add_argument(
        "--case", default=None,
        help="只跑指定 case_id（见 data/mock_cases.json）",
    )
    args = parser.parse_args()

    packets = load_cases(CURRENT_POLICY)
    if args.case:
        packets = [p for p in packets if p.case_id == args.case]
        if not packets:
            all_ids = [p.case_id for p in load_cases(CURRENT_POLICY)]
            print(f"未找到案件 {args.case}，可选：{all_ids}")
            return 1

    if not args.mock and len(packets) > 1:
        print("提示：真实调用建议先用 --case 单案跑（灰区案件每案约 5 次 LLM 调用）。\n")

    results = []
    for packet in packets:
        print(f"\n=== {packet.case_id} ===")
        record = run_case(packet, CURRENT_POLICY, mock=args.mock)
        final = record["final"]
        print(f"  最终：{final['decision']}"
              + (f" / {final['tier']}" if final.get("tier") else "")
              + f"（{final['decided_by']}）")
        print(f"  审计：{record['audit_path']}")
        results.append((packet.case_id, final))

    print("\n=== 汇总 ===")
    for case_id, final in results:
        tier = f" {final['tier']}" if final.get("tier") else ""
        print(f"  {case_id}: {final['decision']}{tier}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
