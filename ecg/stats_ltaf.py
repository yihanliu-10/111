"""LTAF 预实验 0:每个病人的 AF 负荷统计——回答"事件稀不稀疏"。

用法:改 DATA 为本机 ltafdb 路径,然后  py stats_ltaf.py
输出:每条记录的时长与 AF 占比 + 四档分布统计(判断选段策略有无价值)。
"""
import pathlib

import wfdb

DATA = pathlib.Path("C:/Users/li.ruili/ltafdb")  # ← 改成你的实际路径

AF_LABELS = ("(AFIB", "(AFL")

rows = []
for hea in sorted(DATA.glob("*.hea")):
    rec = hea.stem
    try:
        ann = wfdb.rdann(str(DATA / rec), "atr")
        header = wfdb.rdheader(str(DATA / rec))
    except Exception as e:  # 个别记录损坏时跳过
        print(f"{rec}: 读取失败 {e}")
        continue
    fs, total = header.fs, header.sig_len
    # 节律区间:aux_note 里 "(XXX" 表示新节律开始,持续到下一个节律标记
    af_samples, cur, last = 0, None, 0
    for samp, note in zip(ann.sample, ann.aux_note):
        if note and note.startswith("("):
            if cur in AF_LABELS:
                af_samples += samp - last
            cur, last = note.strip("\x00"), samp
    if cur in AF_LABELS:
        af_samples += total - last
    hours = total / fs / 3600
    af_pct = 100 * af_samples / total
    rows.append((rec, hours, af_pct))
    print(f"{rec}: {hours:.1f} 小时, AF 占比 {af_pct:5.1f}%")

rows.sort(key=lambda r: r[2])
n = len(rows)
print(f"\n== 共 {n} 条记录 ==")
for lo, hi, tag in [(0, 1, "≈无 AF"), (1, 20, "稀疏(选段策略的主场)"),
                    (20, 80, "中等"), (80, 101, "近持续(随便看都能诊断)")]:
    c = sum(1 for _, _, p in rows if lo <= p < hi)
    print(f"AF 占比 {lo:3d}–{hi:3d}%: {c:3d} 人  {tag}")
