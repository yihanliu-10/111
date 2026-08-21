# 新机器部署(以个人电脑 H:\npj 为例)

前提:机器上有 Python 3.11+ 和 git(个人电脑直接 winget 装,无管控限制):
```
winget install -e --id Python.Python.3.12
winget install -e --id Git.Git
```
(装完重开命令行。)

## 一条龙命令(逐行贴)

```bat
:: 1. 克隆代码
mkdir H:\npj 2>nul
cd /d H:\npj
git clone -b claude/medical-mammo-domain-shift-40ffln https://github.com/yihanliu-10/111.git RLVR
cd RLVR\ecg

:: 2. 装依赖(家庭网络直连,不需要代理;若在校内网则先 set HTTPS_PROXY=...)
py -m pip install --user wfdb numpy scikit-learn boto3 requests torch

:: 3. 本机路径覆盖(不改 config.py,建 config_local.py)
echo import pathlib> config_local.py
echo LTAF_DIR = pathlib.Path(r"H:\npj\data\ltafdb")>> config_local.py
echo ICENTIA_DIR = pathlib.Path(r"H:\npj\data\icentia11k")>> config_local.py

:: 4. 下数据(家庭宽带直连 S3,比实验室快得多)
py dl_ltaf.py
py dl_icentia_staged.py annotations

:: 5. 复现预实验(LTAF 下完即可跑)
py stats_ltaf.py
py embed_ltaf_v2.py
py gonogo_hour.py
```

## 说明

- `config_local.py` 被 .gitignore 忽略:每台机器路径各写各的,`git pull` 永不冲突;
- 实验室机器不需要动:它没有 config_local.py,继续用 config.py 里的默认路径;
- Icentia 三步(annotations → scan → signals)在哪台机器跑都行,建议挑网快、磁盘大的那台;两台都下也无妨(脚本断点续传、幂等);
- 特征缓存(*.npz)不进 git(体积大且各机器可再生),每台机器各自跑 embed 生成。
