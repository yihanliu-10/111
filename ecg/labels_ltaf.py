"""预实验 0b:LTAF 里到底有哪些标签?

统计:①所有节律标签(aux_note 以"("开头)的出现次数 / 总时长 / 时长占比 / 涉及病人数;
     ②所有心搏符号计数。用于决定任务是二分类 AF 还是多类稀疏事件。

用法:py labels_ltaf.py
"""
import collections

import wfdb

from config import LTAF_DIR as DATA

rhythm_dur = collections.Counter()    # 标签 -> 总样本数(时长)
rhythm_cnt = collections.Counter()    # 标签 -> 区间次数
rhythm_pat = collections.defaultdict(set)  # 标签 -> 病人集合
beat_cnt = collections.Counter()      # 心搏符号 -> 次数
total_samples = 0

records = sorted(p.stem for p in DATA.glob("*.hea"))
if not records:
    raise SystemExit(f"在 {DATA} 没找到 .hea——检查 config.py。")

for rec in records:
    try:
        ann = wfdb.rdann(str(DATA / rec), "atr")
        header = wfdb.rdheader(str(DATA / rec))
    except Exception as e:
        print(f"{rec}: 读取失败 {e}")
        continue
    fs, sig_len = header.fs, header.sig_len
    total_samples += sig_len
    beat_cnt.update(ann.symbol)
    cur, last = None, 0
    for samp, note in zip(ann.sample, ann.aux_note):
        if note and note.startswith("("):
            if cur is not None:
                rhythm_dur[cur] += samp - last
            cur = note.strip("\x00")
            rhythm_cnt[cur] += 1
            rhythm_pat[cur].add(rec)
            last = samp
    if cur is not None:
        rhythm_dur[cur] += sig_len - last

fs = 128  # LTAF 采样率(打印占比用总样本数,fs 仅换算小时)
print(f"\n== 节律标签(共 {len(records)} 记录,总时长 {total_samples/fs/3600:.0f} 小时)==")
print(f"{'标签':>8} | {'区间数':>7} | {'总时长(小时)':>10} | {'时长占比':>8} | {'病人数':>5}")
for lab, dur in rhythm_dur.most_common():
    print(f"{lab:>8} | {rhythm_cnt[lab]:>7} | {dur/fs/3600:>10.1f} | "
          f"{100*dur/total_samples:>7.2f}% | {len(rhythm_pat[lab]):>5}")

print("\n== 心搏符号 ==")
for sym, c in beat_cnt.most_common():
    print(f"{sym!r:>6}: {c}")
