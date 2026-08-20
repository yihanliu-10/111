# ECG-RLVR 项目(预算化长时程 ECG 判读)

本目录是项目代码的正本,由 Claude 在云端维护;本地 `Desktop\RLVR` 是同步副本。

## 同步方式(Windows 本机)

方式 A(推荐,装好 git 后一次配置):
```
winget install -e --id Git.Git --scope user
git clone -b claude/medical-mammo-domain-shift-40ffln https://github.com/yihanliu-10/111.git RLVR
# 之后每次更新只需:
git pull
```

方式 B(无 git,浏览器下载 ZIP):
打开 https://github.com/yihanliu-10/111/archive/refs/heads/claude/medical-mammo-domain-shift-40ffln.zip
解压,把 `ecg/` 内容覆盖到 `Desktop\RLVR\`。

## 环境(每个新终端先设代理)

```
set HTTP_PROXY=http://172.30.2.11:8080
set HTTPS_PROXY=http://172.30.2.11:8080
py -m pip install --user wfdb numpy boto3 requests
```

## 脚本清单与运行顺序

| 脚本 | 作用 | 前置 |
|---|---|---|
| `stats_ltaf.py` | 预实验 0:84 病人 AF 负荷分布 → 判断"事件稀疏"前提 | LTAF 已下载,改脚本内 DATA 路径 |
| (待添加)`embed_ltaf.py` | 切 10s 窗 + 提特征缓存 | 预实验 0 通过 |
| (待添加)`gonogo_uniform.py` | go/no-go:均匀采 K% vs 全量 MIL | 特征缓存 |

## 数据路径约定

- LTAF:`C:\Users\li.ruili\ltafdb`(或自定义后改脚本 DATA)
- Icentia11k 全量:后台下载中,落盘路径见 `dl_icentia_full.py` 的 OUT
