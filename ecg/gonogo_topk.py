"""预实验 1c:量出"聪明选择"的天花板(上 RL 之前的必做题)。

三个选择器同预算对比(均按记录级判定,max 聚合,90% 特异度工作点):
  uniform  均匀采 K 窗(下界,已知会塌)
  topk     粗筛 top-K:RR 特征分类器全扫打分,取最可疑 K 窗(级联基线,RL 的对手)
  oracle   神谕:用真实标注优先挑含 AF 的窗(完美选择器的上界)

用法:先跑 embed_ltaf.py,然后  py gonogo_topk.py
"""
import pathlib

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

rng = np.random.RandomState(0)
z = np.load(pathlib.Path(__file__).parent / "ltaf_windows.npz", allow_pickle=True)
feats, af_frac, rec_id = z["feats"], z["af_frac"], z["rec_id"]
if len(feats) == 0:
    raise SystemExit("特征缓存为空——先修 config.py 并重跑 embed_ltaf.py。")

recs = np.unique(rec_id)
burden = np.array([af_frac[rec_id == r].mean() for r in recs])
rec_label = (burden > 0.01).astype(int)
strata = np.where(burden < 0.01, "无AF",
         np.where(burden < 0.20, "稀疏", np.where(burden < 0.80, "中等", "持续")))

perm = rng.permutation(len(recs))
tr_recs = set(recs[perm[: int(0.6 * len(recs))]])
te_recs = set(recs[perm[int(0.6 * len(recs)):]])
tr = np.isin(rec_id, list(tr_recs))

clf = LogisticRegression(max_iter=1000, class_weight="balanced")
mu, sd = feats[tr].mean(0), feats[tr].std(0) + 1e-8
clf.fit((feats[tr] - mu) / sd, (af_frac[tr] > 0.5).astype(int))
prob = clf.predict_proba((feats - mu) / sd)[:, 1]

def score(r, k, mode):
    p = prob[rec_id == r]
    hit = af_frac[rec_id == r] > 0.5
    n = len(p)
    if k is None or k >= n:
        idx = np.arange(n)
    elif mode == "uniform":
        return np.mean([p[rng.choice(n, k, replace=False)].max() for _ in range(20)])
    elif mode == "topk":
        idx = np.argsort(p)[-k:]           # 粗筛分数最高的 K 窗
    elif mode == "oracle":
        af_idx = np.where(hit)[0]
        rest = np.where(~hit)[0]
        idx = np.concatenate([af_idx[:k], rest[: max(0, k - len(af_idx))]])
    return p[idx].max()

te = [r for r in recs if r in te_recs]
i_of = {r: list(recs).index(r) for r in te}
te_y = np.array([rec_label[i_of[r]] for r in te])
te_s = np.array([strata[i_of[r]] for r in te])

print(f"测试集 {len(te)} 记录(阳性 {te_y.sum()},阴性 {(te_y == 0).sum()} ← 阴性极少,数字看趋势)")
print(f"{'K':>5} {'选择器':>8} | {'总AUC':>6} | {'稀疏档敏感度':>10} | {'持续档敏感度':>10}")
for k in [2, 5, 10, 20]:
    for mode in ["uniform", "topk", "oracle"]:
        s = np.array([score(r, k, mode) for r in te])
        auc = roc_auc_score(te_y, s) if len(set(te_y)) > 1 else float("nan")
        thr = np.percentile(s[te_y == 0], 90) if (te_y == 0).any() else 0.5
        sens = lambda m: (s[m & (te_y == 1)] > thr).mean() if (m & (te_y == 1)).any() else float("nan")
        print(f"{k:>5} {mode:>8} | {auc:6.3f} | {sens(te_s == '稀疏'):10.3f} | {sens(te_s == '持续'):10.3f}")
    print()
