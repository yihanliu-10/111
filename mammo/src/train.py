"""合并若干源数据集训练判别基线(v15 的 S1)。

用法:
  python -m mammo.src.train --datasets vindr,rsna,cmmd --mock --epochs 2 --out runs/mock
"""
import argparse
import json
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import ConcatDataset, DataLoader

from .datasets import get_dataset
from .metrics import auc, sens_at_spec
from .model import MammoNet


def evaluate(model, loader, device):
    model.eval()
    ys, ps = [], []
    with torch.no_grad():
        for x, y in loader:
            p = torch.sigmoid(model(x.to(device))).cpu().numpy()
            ps.append(p), ys.append(y.numpy())
    y, p = np.concatenate(ys), np.concatenate(ps)
    return {"auc": auc(y, p), "sens@90spec": sens_at_spec(y, p, 0.9)}


def train(datasets, mock=False, epochs=10, batch_size=32, lr=3e-4,
          out="runs/baseline", device=None):
    device = device or ("cuda" if torch.cuda.is_available() else "cpu")
    out = Path(out); out.mkdir(parents=True, exist_ok=True)

    train_ds = ConcatDataset([get_dataset(d, "train", mock) for d in datasets])
    val_loaders = {d: DataLoader(get_dataset(d, "val", mock), batch_size=batch_size)
                   for d in datasets}
    # 类别不平衡:按训练集阳性率加权
    labels = np.array([train_ds[i][1] for i in range(len(train_ds))])
    pos_weight = torch.tensor([(labels == 0).sum() / max((labels == 1).sum(), 1)],
                              dtype=torch.float32, device=device)

    model = MammoNet(pretrained=not mock).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=lr)
    crit = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
    loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True,
                        num_workers=2, drop_last=True)

    for ep in range(epochs):
        model.train()
        for x, y in loader:
            opt.zero_grad()
            loss = crit(model(x.to(device)), y.float().to(device))
            loss.backward(); opt.step()
        ivals = {d: evaluate(model, dl, device) for d, dl in val_loaders.items()}
        print(f"[ep {ep+1}/{epochs}] " +
              " ".join(f"{d}:auc={v['auc']:.3f}" for d, v in ivals.items()))

    torch.save({"model": model.state_dict(), "datasets": datasets}, out / "ckpt.pt")
    (out / "val_metrics.json").write_text(json.dumps(ivals, indent=2))
    return model, ivals


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--datasets", required=True, help="逗号分隔,如 vindr,rsna,cmmd")
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--epochs", type=int, default=10)
    ap.add_argument("--batch-size", type=int, default=32)
    ap.add_argument("--out", default="runs/baseline")
    a = ap.parse_args()
    train(a.datasets.split(","), mock=a.mock, epochs=a.epochs,
          batch_size=a.batch_size, out=a.out)
