"""预实验 1b(go/no-go):均匀采 K 窗 vs 全量,按 AF 负荷分层。

问题:记录级 AF 检测,均匀抽 K 个窗够不够?
- 稀疏档在小 K 下塌、大 K 才恢复 → "去哪看"有信息量,选段策略立项;
- 小 K 即追平全量 → 均匀采样够用,方法故事需重想。

用法:先跑 embed_ltaf.py,然后  py gonogo_uniform.py
"""
import pathlib

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

rng = np.random.RandomState(0)
z = np.load(pathlib.Path(__file__).parent / "ltaf_windows.npz", allow_pickle=True)
feats, af_frac, rec_id = z["feats"], z["af_frac"], z["rec_id"]

# 记录级标签与分层(负荷 = AF 窗占比)
recs = np.unique(rec_id)
burden = np.array([af_frac[rec_id == r].mean() for r in recs])
rec_label = (burden > 0.01).astype(int)          # 记录含 ≥1% AF 即阳性
strata = np.where(burden < 0.01, "无AF",
         np.where(burden < 0.20, "稀疏", np.where(burden < 0.80, "中等", "持续")))
print("分层:", {s: int((strata == s).sum()) for s in np.unique(strata)})

# 病人级切分(LTAF 一记录一病人):60/40
perm = rng.permutation(len(recs))
tr_recs, te_recs = set(recs[perm[: int(0.6 * len(recs))]]), set(recs[perm[int(0.6 * len(recs)):]])
tr = np.isin(rec_id, list(tr_recs))

# 窗级分类器(窗标签 = 窗内 AF 占比>0.5;仅训练集用窗标签)
clf = LogisticRegression(max_iter=1000, class_weight="balanced")
mu, sd = feats[tr].mean(0), feats[tr].std(0) + 1e-8
clf.fit((feats[tr] - mu) / sd, (af_frac[tr] > 0.5).astype(int))
prob = clf.predict_proba((feats - mu) / sd)[:, 1]

def record_score(r, k, n_rep=20):
    """均匀抽 k 窗(k=None 为全量),记录分 = 窗概率 max,重复取均值。"""
    p = prob[rec_id == r]
    if k is None or k >= len(p):
        return p.max()
    return np.mean([p[rng.choice(len(p), k, replace=False)].max() for _ in range(n_rep)])

te = [r for r in recs if r in te_recs]
te_y = np.array([rec_label[list(recs).index(r)] for r in te])
te_s = np.array([strata[list(recs).index(r)] for r in te])

print(f"\n测试集 {len(te)} 记录(阳性 {te_y.sum()})")
print(f"{'K':>6} | {'总AUC':>6} | {'稀疏档敏感度':>10} | {'持续档敏感度':>10} | {'覆盖率(稀疏)':>10}")
for k in [1, 2, 5, 10, 20, 50, 100, None]:
    s = np.array([record_score(r, k) for r in te])
    auc = roc_auc_score(te_y, s) if len(set(te_y)) > 1 else float("nan")
    thr = np.percentile(s[te_y == 0], 90) if (te_y == 0).any() else 0.5  # 90% 特异度工作点
    sens = lambda m: (s[m & (te_y == 1)] > thr).mean() if (m & (te_y == 1)).any() else float("nan")
    # 覆盖率:抽 K 窗至少命中一个 AF 窗的经验概率(稀疏档)
    cov = []
    for r in te:
        if strata[list(recs).index(r)] != "稀疏":
            continue
        hit = af_frac[rec_id == r] > 0.5
        if k is None or k >= len(hit):
            cov.append(float(hit.any()))
        else:
            cov.append(np.mean([hit[rng.choice(len(hit), k, replace=False)].any()
                                for _ in range(20)]))
    kk = "全量" if k is None else k
    print(f"{kk:>6} | {auc:6.3f} | {sens(te_s == '稀疏'):10.3f} | "
          f"{sens(te_s == '持续'):10.3f} | {np.mean(cov) if cov else float('nan'):10.3f}")
