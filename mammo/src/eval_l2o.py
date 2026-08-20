"""Leave-2-out 掉点表(W1-2 的 go/no-go 实验)。

对 5 个数据集的每个 C(5,2)=10 组合:留 2 个当 OOD,其余 3 个合并训练;
报告 ID(留内验证集平均)与两个 OOD 测试集的 AUC / sens@90spec,输出 markdown 表。

用法:
  python -m mammo.src.eval_l2o --datasets vindr,rsna,cmmd,inbreast,cbis --mock --epochs 2 --out results/
"""
import argparse
from itertools import combinations
from pathlib import Path

import numpy as np
from torch.utils.data import DataLoader

from .datasets import get_dataset
from .train import evaluate, train


def main(datasets, mock=False, epochs=10, batch_size=32, out="results/"):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    rows = []
    for ood in combinations(datasets, 2):
        src = [d for d in datasets if d not in ood]
        tag = "+".join(src)
        print(f"\n=== 源:{tag}  OOD:{ood} ===")
        model, ivals = train(src, mock=mock, epochs=epochs, batch_size=batch_size,
                             out=out / f"run_{tag}")
        id_auc = float(np.mean([v["auc"] for v in ivals.values()]))
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
        for d in ood:
            dl = DataLoader(get_dataset(d, "test", mock), batch_size=batch_size)
            m = evaluate(model, dl, device)
            rows.append({"source": tag, "ood": d, "id_auc": id_auc,
                         "ood_auc": m["auc"], "drop": id_auc - m["auc"],
                         "ood_sens@90spec": m["sens@90spec"]})
            print(f"  OOD {d}: auc={m['auc']:.3f} (drop {id_auc - m['auc']:+.3f})")

    lines = ["| 源组合 | OOD 集 | ID AUC | OOD AUC | 掉点 | OOD sens@90spec |",
             "|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['source']} | {r['ood']} | {r['id_auc']:.3f} | "
                     f"{r['ood_auc']:.3f} | {r['drop']:+.3f} | {r['ood_sens@90spec']:.3f} |")
    mean_drop = float(np.mean([r["drop"] for r in rows]))
    lines.append(f"\n平均掉点:**{mean_drop:+.3f}**。"
                 f"Go/No-Go:<0.03 换方向;≥0.05 方法空间充足。")
    (Path(out) / "drop_table.md").write_text("\n".join(lines))
    print(f"\n掉点表已写入 {out}/drop_table.md(平均掉点 {mean_drop:+.3f})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--datasets", required=True)
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--epochs", type=int, default=10)
    ap.add_argument("--batch-size", type=int, default=32)
    ap.add_argument("--out", default="results/")
    a = ap.parse_args()
    main(a.datasets.split(","), mock=a.mock, epochs=a.epochs,
         batch_size=a.batch_size, out=a.out)
