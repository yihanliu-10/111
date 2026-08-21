"""数据路径配置。

默认值是实验室 Windows 机的路径;其他机器不要改本文件,
在同目录新建 config_local.py 覆盖(已被 .gitignore 忽略,永不冲突):

    # ecg/config_local.py 示例(个人电脑 H 盘部署)
    import pathlib
    LTAF_DIR = pathlib.Path(r"H:\\npj\\data\\ltafdb")
    ICENTIA_DIR = pathlib.Path(r"H:\\npj\\data\\icentia11k")
"""
import pathlib

LTAF_DIR = pathlib.Path(r"C:\Users\li.ruili\Desktop\ltafdb")
ICENTIA_DIR = pathlib.Path(r"C:\Users\li.ruili\Desktop\icentia11k")

try:
    from config_local import *  # noqa: F401,F403  本机覆盖(可选)
except ImportError:
    pass
