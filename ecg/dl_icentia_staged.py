"""Icentia11k 三步定向下载(全量 ~1.1TB 不现实,按段定向压到几十 GB)。

第 1 步  py dl_icentia_staged.py annotations   全部 .atr(约 5–10GB,可挂过夜)
第 2 步  py dl_icentia_staged.py scan          本地扫出各段的 AF/AFL 含量
第 3 步  py dl_icentia_staged.py signals       定向下信号:阳性段 + 配比正常段

断点续传:任一步中断后重跑同一命令即续。路径在 config.ICENTIA_DIR。
"""
import sys
import random
import pathlib
import collections
from concurrent.futures import ThreadPoolExecutor

import boto3
from botocore import UNSIGNED
from botocore.config import Config

from config import ICENTIA_DIR as OUT

BUCKET = "physionet-open"
PREFIX = "icentia11k-continuous-ecg/1.0/"
THREADS = 64   # 小文件多、往返延迟是瓶颈,靠并发堆吞吐
SEED = 0

MAX_POS_SEG_PER_PATIENT = 6   # 每病人最多收的含 AF/AFL 段数
NEG_SEG_PER_PATIENT = 2       # 阴性病人每人收的正常段数
N_NEG_PATIENTS = 2500         # 抽多少个阴性病人

s3 = boto3.client("s3", region_name="us-east-1",
                  config=Config(signature_version=UNSIGNED, max_pool_connections=128))

def list_all_keys():
    cache = OUT / "_all_keys.txt"
    if cache.exists():
        return cache.read_text().splitlines()
    print("列 S3 目录(两百万级对象,几分钟)...")
    keys = []
    for page in s3.get_paginator("list_objects_v2").paginate(Bucket=BUCKET, Prefix=PREFIX):
        keys += [o["Key"] for o in page.get("Contents", [])]
        print(f"\r已列 {len(keys)}", end="")
    OUT.mkdir(parents=True, exist_ok=True)
    cache.write_text("\n".join(keys))
    print()
    return keys

def download(keys, tag):
    def grab(key):
        dst = OUT / key[len(PREFIX):]
        dst.parent.mkdir(parents=True, exist_ok=True)
        if not dst.exists():
            s3.download_file(BUCKET, key, str(dst))
    with ThreadPoolExecutor(THREADS) as ex:
        for i, _ in enumerate(ex.map(grab, keys), 1):
            if i % 200 == 0 or i == len(keys):
                print(f"\r[{tag}] {i}/{len(keys)}", end="")
    print()

cmd = sys.argv[1] if len(sys.argv) > 1 else ""

if cmd == "annotations":
    keys = [k for k in list_all_keys() if k.endswith(".atr")]
    print(f"{len(keys)} 个标注文件")
    download(keys, "atr")

elif cmd == "scan":
    import wfdb
    seg_af = {}                      # 段名(p00000_s00) -> 是否含 AF/AFL
    atrs = sorted(OUT.rglob("*.atr"))
    for i, f in enumerate(atrs, 1):
        try:
            ann = wfdb.rdann(str(f)[:-4], "atr")
            has = any(a and ("AFIB" in a or "AFL" in a) for a in ann.aux_note)
        except Exception:
            has = False
        seg_af[f.stem] = has
        if i % 2000 == 0:
            print(f"\r扫描 {i}/{len(atrs)}", end="")
    by_pat = collections.defaultdict(dict)
    for seg, has in seg_af.items():
        by_pat[seg.split("_")[0]][seg] = has
    pos_lines, neg_lines = [], []
    for pat, segs in sorted(by_pat.items()):
        pos_segs = sorted(s for s, h in segs.items() if h)
        if pos_segs:
            pos_lines.append(pat + "," + ";".join(pos_segs))
        else:
            neg_lines.append(pat + "," + ";".join(sorted(segs)))
    (OUT / "_pos_patients.txt").write_text("\n".join(pos_lines))
    (OUT / "_neg_patients.txt").write_text("\n".join(neg_lines))
    n_pos_seg = sum(len(l.split(",")[1].split(";")) for l in pos_lines)
    print(f"\n病人:阳性 {len(pos_lines)}(含 AF/AFL 段共 {n_pos_seg}),阴性 {len(neg_lines)}")

elif cmd == "signals":
    rnd = random.Random(SEED)
    chosen = set()
    for line in (OUT / "_pos_patients.txt").read_text().splitlines():
        pat, segs = line.split(",")
        segs = segs.split(";")
        rnd.shuffle(segs)
        chosen.update(segs[:MAX_POS_SEG_PER_PATIENT])
    neg = (OUT / "_neg_patients.txt").read_text().splitlines()
    rnd.shuffle(neg)
    for line in neg[:N_NEG_PATIENTS]:
        pat, segs = line.split(",")
        segs = segs.split(";")
        rnd.shuffle(segs)
        chosen.update(segs[:NEG_SEG_PER_PATIENT])
    keys = [k for k in list_all_keys()
            if k.endswith((".dat", ".hea"))
            and k.split("/")[-1].rsplit(".", 1)[0] in chosen]
    est_gb = sum(1 for k in keys if k.endswith(".dat")) * 2.1 / 1024
    print(f"选中 {len(chosen)} 个段,{len(keys)} 个文件,估计 {est_gb:.0f} GB")
    if input("确认下载?(y/n) ").lower() == "y":
        download(keys, "sig")
else:
    print("用法: py dl_icentia_staged.py annotations | scan | signals")
