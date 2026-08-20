"""预实验 2a:LTAF 10 秒窗 + 多事件标签缓存(v2)。

相对 v1 的三个改动:窗 60s→10s;标签从"AF 占比"改为逐事件"窗内含该节律即 True";
额外记录每窗所属小时(小时 = 后续判定单元)。

用法:py embed_ltaf_v2.py  → 生成 ltaf_windows_v2.npz(几分钟)
"""
import pathlib

import numpy as np
import wfdb

from config import LTAF_DIR as DATA

OUT = pathlib.Path(__file__).parent / "ltaf_windows_v2.npz"
WIN = 10  # 秒
EVENTS = ["(AFIB", "(SBR", "(SVTA", "(VT"]  # 稀疏度光谱:52% / 2.8% / 0.17% / 0.02%
BEAT_SYMS = set("NLRBAaJSVrFejnE/fQ?")

def rhythm_intervals(ann, sig_len):
    """[(start, end, label), ...] 由节律标记展开。"""
    out, cur, last = [], None, 0
    for samp, note in zip(ann.sample, ann.aux_note):
        if note and note.startswith("("):
            if cur is not None:
                out.append((last, samp, cur))
            cur, last = note.strip("\x00"), samp
    if cur is not None:
        out.append((last, sig_len, cur))
    return out

def window_features(rr):
    if len(rr) < 3:
        return None
    d = np.diff(rr)
    return np.array([
        len(rr), rr.mean(), rr.std(), rr.std() / (rr.mean() + 1e-8),
        np.sqrt((d ** 2).mean()), (np.abs(d) > 0.05).mean(),
        np.median(np.abs(rr - np.median(rr))),
    ])

feats, ev_labels, rec_ids, hour_ids = [], [], [], []
records = sorted(p.stem for p in DATA.glob("*.hea"))
if not records:
    raise SystemExit(f"在 {DATA} 没找到 .hea——检查 config.py。")

for ri, rec in enumerate(records):
    try:
        ann = wfdb.rdann(str(DATA / rec), "atr")
        header = wfdb.rdheader(str(DATA / rec))
    except Exception as e:
        print(f"{rec}: 读取失败 {e}")
        continue
    fs, sig_len = header.fs, header.sig_len
    ivals = rhythm_intervals(ann, sig_len)
    beats = ann.sample[np.isin(ann.symbol, list(BEAT_SYMS))]
    wlen, hlen = int(WIN * fs), int(3600 * fs)
    n_win = sig_len // wlen
    # 每窗每事件:窗与该事件任一区间有重叠即 True
    starts = np.arange(n_win) * wlen
    lab = np.zeros((n_win, len(EVENTS)), dtype=bool)
    for s, e, name in ivals:
        if name in EVENTS:
            j = EVENTS.index(name)
            w0, w1 = max(0, s // wlen), min(n_win, e // wlen + 1)
            lab[w0:w1, j] = True
    for w in range(n_win):
        lo = starts[w]
        b = beats[(beats >= lo) & (beats < lo + wlen)]
        f = window_features(np.diff(b) / fs)
        if f is None:
            continue
        feats.append(f)
        ev_labels.append(lab[w])
        rec_ids.append(ri)
        hour_ids.append(int(lo // hlen))
    print(f"{rec}: {n_win} 窗")

np.savez(OUT,
         feats=np.array(feats, dtype=np.float32),
         events=np.array(ev_labels, dtype=bool),
         event_names=np.array(EVENTS),
         rec_id=np.array(rec_ids, dtype=np.int32),
         hour_id=np.array(hour_ids, dtype=np.int32),
         records=np.array(records))
print(f"\n共 {len(feats)} 窗,已存 {OUT}")
