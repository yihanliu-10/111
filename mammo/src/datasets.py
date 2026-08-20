"""数据集注册表:5 个公开集的加载桩 + mock 合成数据。

接真数据时:给 REGISTRY 里对应条目填 root,并实现 _load_index()。
所有数据集统一输出 (image[3,H,W] float, label 0/1)。切分必须按病人级。
"""
import hashlib

import numpy as np
import torch
from torch.utils.data import Dataset

IMG_SIZE = 512  # W1-2 基线用 512;正式实验换 1536


class MockMammo(Dataset):
    """合成数据:每个数据集名对应一种"厂商风格"(gamma/对比度/噪声),
    恶性样本带一个高亮团块。只用于跑通管道。"""

    def __init__(self, name: str, split: str, n: int = 200):
        self.name, self.split, self.n = name, split, n
        seed = int(hashlib.md5(f"{name}-{split}".encode()).hexdigest()[:8], 16)
        self.rng = np.random.RandomState(seed)
        style = int(hashlib.md5(name.encode()).hexdigest()[:8], 16)
        self.gamma = 0.6 + (style % 5) * 0.25          # 厂商 gamma
        self.contrast = 0.7 + ((style // 5) % 4) * 0.2  # 厂商对比度
        self.labels = self.rng.binomial(1, 0.3, size=n)

    def __len__(self):
        return self.n

    def __getitem__(self, i):
        rng = np.random.RandomState(i * 7919 + 13)
        img = rng.rand(IMG_SIZE, IMG_SIZE).astype(np.float32) * 0.3 + 0.2
        if self.labels[i] == 1:  # 恶性:加一个团块
            cx, cy = rng.randint(100, IMG_SIZE - 100, 2)
            y, x = np.ogrid[:IMG_SIZE, :IMG_SIZE]
            img += 0.5 * np.exp(-((x - cx) ** 2 + (y - cy) ** 2) / (2 * 30.0 ** 2))
        img = np.clip(self.contrast * img, 0, 1) ** self.gamma  # 厂商风格
        t = torch.from_numpy(img)[None].repeat(3, 1, 1)
        return t, int(self.labels[i])


class FolderMammo(Dataset):
    """真实数据通用加载器:子类/条目只需给出 index = [(path, label), ...]。"""

    def __init__(self, index, split):
        from torchvision import transforms as T
        self.index, self.split = index, split
        self.tf = T.Compose([
            T.Grayscale(3), T.Resize((IMG_SIZE, IMG_SIZE)), T.ToTensor(),
        ])

    def __len__(self):
        return len(self.index)

    def __getitem__(self, i):
        from PIL import Image
        path, label = self.index[i]
        return self.tf(Image.open(path)), int(label)


def _todo(name):
    def _load_index(root, split):
        raise NotImplementedError(
            f"数据集 {name}:请在 datasets.py 的 REGISTRY 中填 root 并实现 _load_index "
            f"(返回病人级切分后的 [(图路径, 0/1), ...])。")
    return _load_index


# 5 个公开数据集。root 填本地路径;_load_index 按各集的元数据表实现。
REGISTRY = {
    "vindr":    {"root": None, "load": _todo("vindr")},     # PhysioNet VinDr-Mammo
    "rsna":     {"root": None, "load": _todo("rsna")},      # Kaggle RSNA 2023
    "cmmd":     {"root": None, "load": _todo("cmmd")},      # TCIA CMMD
    "inbreast": {"root": None, "load": _todo("inbreast")},  # INbreast
    "cbis":     {"root": None, "load": _todo("cbis")},      # TCIA CBIS-DDSM
}


def get_dataset(name: str, split: str, mock: bool = False) -> Dataset:
    assert name in REGISTRY, f"未知数据集 {name},可选:{list(REGISTRY)}"
    if mock:
        return MockMammo(name, split, n=200 if split == "train" else 80)
    entry = REGISTRY[name]
    return FolderMammo(entry["load"](entry["root"], split), split)
