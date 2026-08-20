"""评测指标:AUC、sensitivity@specificity、ECE。"""
import numpy as np
from sklearn.metrics import roc_auc_score, roc_curve


def auc(y, p):
    return float(roc_auc_score(y, p))


def sens_at_spec(y, p, spec: float = 0.9):
    """固定特异度下的敏感度(筛查工作点)。"""
    fpr, tpr, _ = roc_curve(y, p)
    ok = fpr <= (1 - spec)
    return float(tpr[ok].max()) if ok.any() else 0.0


def ece(y, p, n_bins: int = 10):
    """期望校准误差(概率输入)。"""
    y, p = np.asarray(y, float), np.asarray(p, float)
    bins = np.linspace(0, 1, n_bins + 1)
    e, total = 0.0, len(y)
    for lo, hi in zip(bins[:-1], bins[1:]):
        m = (p >= lo) & (p < hi) if hi < 1 else (p >= lo) & (p <= 1)
        if m.sum():
            e += m.sum() / total * abs(y[m].mean() - p[m].mean())
    return float(e)
