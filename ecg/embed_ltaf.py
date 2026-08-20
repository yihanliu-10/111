"""预实验 1a:LTAF 切窗 + RR 特征缓存。

每条记录切 WIN 秒不重叠窗;RR 间期直接取 .atr 的逐搏标注位置(免 QRS 检测);
每窗输出 RR 统计特征 + AF 占比(af_frac,仅用于评测/分层,不进特征)。

用法:改 DATA 后  py embed_ltaf.py   → 生成 ltaf_windows.npz
"""
import pathlib

import numpy as np
import wfdb

from config import LTAF_DIR as DATA
OUT = pathlib.Path(__file__).parent / "ltaf_windows.npz"
WIN = 60  # 窗长(秒)

AF_LABELS = ("(AFIB", "(AFL")
BEAT_SYMS = set("NLRBAaJSVrFejnE/fQ?")  # wfdb 心搏类标注符号

def rhythm_mask(ann, sig_len):
    """逐样本 AF 掩码(由节律区间展开)。"""
    mask = np.zeros(sig_len, dtype=bool)
    cur, last = None, 0
    for samp, note in zip(ann.sample, ann.aux_note):
        if note and note.startswith("("):
            if cur in AF_LABELS:
                mask[last:samp] = True
            cur, last = note.strip("\x00"), samp
    if cur in AF_LABELS:
        mask[last:] = True
    return mask

def window_features(rr):
    """一个窗内的 RR 间期(秒)→ 特征向量;不足 3 个心搏返回 None。"""
    if len(rr) < 3:
        return None
    d = np.diff(rr)
    return np.array([
        len(rr),                        # 心搏数
        rr.mean(), rr.std(),
        rr.std() / (rr.mean() + 1e-8),  # CV
        np.sqrt((d ** 2).mean()),       # RMSSD
        (np.abs(d) > 0.05).mean(),      # pNN50 类比(ΔRR>50ms 占比)
        np.median(np.abs(rr - np.median(rr))),  # MAD
    ])

feats, af_fracs, rec_ids, win_ids = [], [], [], []
records = sorted(p.stem for p in DATA.glob("*.hea"))
if not records:
    raise SystemExit(f"在 {DATA} 没找到任何 .hea 文件——去 ecg/config.py 把 LTAF_DIR "
                     f"改成 stats_ltaf.py 能跑通的那个路径(注意别多/少一层目录)。")
for ri, rec in enumerate(records):
    try:
        ann = wfdb.rdann(str(DATA / rec), "atr")
        header = wfdb.rdheader(str(DATA / rec))
    except Exception as e:
        print(f"{rec}: 读取失败 {e}")
        continue
    fs, sig_len = header.fs, header.sig_len
    mask = rhythm_mask(ann, sig_len)
    beats = ann.sample[np.isin(ann.symbol, list(BEAT_SYMS))]
    wlen = int(WIN * fs)
    n_win = sig_len // wlen
    for w in range(n_win):
        lo, hi = w * wlen, (w + 1) * wlen
        b = beats[(beats >= lo) & (beats < hi)]
        f = window_features(np.diff(b) / fs)
        if f is None:
            continue
        feats.append(f)
        af_fracs.append(mask[lo:hi].mean())
        rec_ids.append(ri)
        win_ids.append(w)
    print(f"{rec}: {n_win} 窗")

np.savez(OUT,
         feats=np.array(feats, dtype=np.float32),
         af_frac=np.array(af_fracs, dtype=np.float32),
         rec_id=np.array(rec_ids, dtype=np.int32),
         win_id=np.array(win_ids, dtype=np.int32),
         records=np.array(records))
print(f"\n共 {len(feats)} 窗,已存 {OUT}")
