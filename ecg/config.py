"""数据路径统一配置——只需要改这一个文件。"""
import pathlib

# LTAF 数据目录:里面直接躺着 00.dat / 00.atr / 00.hea 这些文件。
# 填 stats_ltaf.py 当时能跑通的那个路径。
LTAF_DIR = pathlib.Path(r"C:\Users\li.ruili\Desktop\ltafdb")

# Icentia11k 全量下载目录(dl_icentia_full.py 的 OUT,一致即可)
ICENTIA_DIR = pathlib.Path(r"C:\Users\li.ruili\Desktop\icentia11k")
