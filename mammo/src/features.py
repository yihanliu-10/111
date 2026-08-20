"""S2:冻结 backbone 倒出特征库(后续 CFM/回流全部挂在这上面)。

用法:
  python -m mammo.src.features --ckpt runs/mock/ckpt.pt --datasets vindr,rsna --mock --out feats/
"""
import argparse
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader

from .datasets import get_dataset
from .model import MammoNet


def dump(ckpt, datasets, mock=False, batch_size=64, out="feats/"):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = MammoNet(pretrained=False).to(device)
    model.load_state_dict(torch.load(ckpt, map_location=device)["model"])
    model.eval()
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    for d in datasets:
        for split in ("train", "val", "test"):
            dl = DataLoader(get_dataset(d, split, mock), batch_size=batch_size)
            fs, ys = [], []
            with torch.no_grad():
                for x, y in dl:
                    fs.append(model.features(x.to(device)).cpu().numpy())
                    ys.append(y.numpy())
            np.savez(out / f"{d}_{split}.npz",
                     feats=np.concatenate(fs), labels=np.concatenate(ys))
            print(f"{d}/{split}: {sum(len(y) for y in ys)} 条特征已存")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--datasets", required=True)
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--out", default="feats/")
    a = ap.parse_args()
    dump(a.ckpt, a.datasets.split(","), mock=a.mock, out=a.out)
