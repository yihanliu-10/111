"""Icentia11k 全量下载(S3 匿名 + 32 线程,断点续传:重跑即续)。

用法:改 OUT 为目标盘目录(预留 200GB),设好代理环境变量后  py dl_icentia_full.py
"""
import pathlib
from concurrent.futures import ThreadPoolExecutor

import boto3
from botocore import UNSIGNED
from botocore.config import Config

from config import ICENTIA_DIR as OUT

BUCKET = "physionet-open"
PREFIX = "icentia11k-continuous-ecg/1.0/"
THREADS = 32

s3 = boto3.client("s3", region_name="us-east-1",
                  config=Config(signature_version=UNSIGNED, max_pool_connections=64))

cache = OUT / "_all_keys.txt"
OUT.mkdir(parents=True, exist_ok=True)
if cache.exists():
    keys = cache.read_text().splitlines()
else:
    print("列目录(百万级对象,几分钟)...")
    keys = []
    for page in s3.get_paginator("list_objects_v2").paginate(Bucket=BUCKET, Prefix=PREFIX):
        keys += [o["Key"] for o in page.get("Contents", [])]
        print(f"\r已列 {len(keys)}", end="")
    cache.write_text("\n".join(keys))
    print()

print(f"共 {len(keys)} 个文件")

def grab(key):
    dst = OUT / key[len(PREFIX):]
    dst.parent.mkdir(parents=True, exist_ok=True)
    if not dst.exists():
        s3.download_file(BUCKET, key, str(dst))

with ThreadPoolExecutor(THREADS) as ex:
    for i, _ in enumerate(ex.map(grab, keys), 1):
        if i % 200 == 0 or i == len(keys):
            print(f"\r{i}/{len(keys)}", end="")
print("\n全部完成")
