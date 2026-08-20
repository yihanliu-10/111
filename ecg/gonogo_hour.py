"""预实验 2b:小时级多事件 go/no-go(v2:鲁棒聚合,uniform vs oracle)。

判定单元 = (记录, 小时),标签 = 该小时内含目标事件。
聚合 = 被选窗概率的 top-3 均值(替代脆弱的 max)。
每个事件 × 预算 K 输出:uniform 与 oracle 的 AUC / sens@90%spec / 阳性覆盖率。

用法:先跑 embed_ltaf_v2.py,然后  py gonogo_hour.py
"""
import pathlib

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

rng = np.random.RandomState(0)
z = np.load(pathlib.Path(__file__).parent / "ltaf_windows_v2.npz", allow_pickle=True)
feats, events, rec_id, hour_id = z["feats"], z["events"], z["rec_id"], z["hour_id"]
names = list(z["event_names"])
if len(feats) == 0:
    raise SystemExit("缓存为空——先跑 embed_ltaf_v2.py。")

# 单元索引:每个 (rec, hour) 的窗下标
unit_key = rec_id.astype(np.int64) * 100000 + hour_id
units, unit_inv = np.unique(unit_key, return_inverse=True)
unit_rec = (units // 100000).astype(int)
unit_windows = [np.where(unit_inv == u)[0] for u in range(len(units))]

# 病人级切分
recs = np.unique(rec_id)
perm = rng.permutation(len(recs))
tr_recs = set(recs[perm[: int(0.6 * len(recs))]])
u_train = np.isin(unit_rec, list(tr_recs))

def agg(p):  # 鲁棒聚合:top-3 均值
    return np.sort(p)[-3:].mean() if len(p) >= 3 else p.mean()

for j, name in enumerate(names):
    y_win = events[:, j]
    u_label = np.array([y_win[w].any() for w in unit_windows])
    n_pos_tr = int(u_label[u_train].sum())
    te_mask = ~u_train
    n_pos_te, n_neg_te = int(u_label[te_mask].sum()), int((~u_label[te_mask]).sum())
    print(f"\n===== {name}  训练阳性小时 {n_pos_tr} | 测试 阳性 {n_pos_te} / 阴性 {n_neg_te} =====")
    if n_pos_tr < 20 or n_pos_te < 10:
        print("阳性太少,跳过")
        continue

    w_tr = np.isin(rec_id, list(tr_recs))
    clf = LogisticRegression(max_iter=1000, class_weight="balanced")
    mu, sd = feats[w_tr].mean(0), feats[w_tr].std(0) + 1e-8
    clf.fit((feats[w_tr] - mu) / sd, y_win[w_tr])
    prob = clf.predict_proba((feats - mu) / sd)[:, 1]

    te_units = np.where(te_mask)[0]
    te_y = u_label[te_units]

    print(f"{'K':>5} {'选择器':>8} | {'AUC':>6} | {'sens@90%spec':>12} | {'阳性覆盖率':>8}")
    for k in [3, 10, 36, 120, None]:
        for mode in ["uniform", "oracle"]:
            scores, covers = [], []
            for u in te_units:
                w = unit_windows[u]
                p, hit = prob[w], y_win[w]
                n = len(w)
                if k is None or k >= n:
                    idx = np.arange(n)
                elif mode == "uniform":
                    idx = rng.choice(n, k, replace=False)
                else:  # oracle:优先取含事件的窗,不足随机补
                    pos = np.where(hit)[0]
                    neg = np.where(~hit)[0]
                    take = min(k, len(pos))
                    idx = np.concatenate([pos[:take],
                                          rng.choice(neg, k - take, replace=False)])
                scores.append(agg(p[idx]))
                if u_label[u]:
                    covers.append(float(hit[idx].any()))
            s = np.array(scores)
            auc = roc_auc_score(te_y, s)
            thr = np.percentile(s[~te_y], 90)
            sens = (s[te_y] > thr).mean()
            kk = "全量" if k is None else k
            print(f"{kk:>5} {mode:>8} | {auc:6.3f} | {sens:12.3f} | "
                  f"{np.mean(covers):8.3f}")
        print()
