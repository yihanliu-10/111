"""LTAF 下载(S3 匿名 + 16 线程,断点续传:重跑即续)。目标目录 = config.LTAF_DIR。"""
import pathlib
from concurrent.futures import ThreadPoolExecutor

import boto3
from botocore import UNSIGNED
from botocore.config import Config

from config import LTAF_DIR as OUT

BUCKET, PREFIX = "physionet-open", "ltafdb/1.0.0/"

s3 = boto3.client("s3", region_name="us-east-1",
                  config=Config(signature_version=UNSIGNED, max_pool_connections=64))

keys = []
for page in s3.get_paginator("list_objects_v2").paginate(Bucket=BUCKET, Prefix=PREFIX):
    keys += [o["Key"] for o in page.get("Contents", [])]
print(f"{len(keys)} 个文件 → {OUT}")

def grab(key):
    dst = OUT / key[len(PREFIX):]
    dst.parent.mkdir(parents=True, exist_ok=True)
    if not dst.exists():
        s3.download_file(BUCKET, key, str(dst))

with ThreadPoolExecutor(16) as ex:
    for i, _ in enumerate(ex.map(grab, keys), 1):
        print(f"\r{i}/{len(keys)}", end="")
print("\n完成")
