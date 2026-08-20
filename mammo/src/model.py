"""backbone + 判别头。backbone 之后所有阶段(特征库、CFM)都挂在 features 上。"""
import torch
import torch.nn as nn
from torchvision import models


class MammoNet(nn.Module):
    def __init__(self, pretrained: bool = True):
        super().__init__()
        weights = models.EfficientNet_B2_Weights.DEFAULT if pretrained else None
        m = models.efficientnet_b2(weights=weights)
        self.backbone = nn.Sequential(m.features, m.avgpool, nn.Flatten())
        self.feat_dim = m.classifier[1].in_features  # 1408
        self.head = nn.Linear(self.feat_dim, 1)

    def features(self, x: torch.Tensor) -> torch.Tensor:
        return self.backbone(x)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.head(self.features(x)).squeeze(-1)  # logit
