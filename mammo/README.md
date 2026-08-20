# Mammo 域偏移基线(W1–2:掉点表 / go-no-go)

FlowBayes 项目第一步:5 个公开数据集合并训分类器,leave-2-out 测跨域掉点。
方案文档见 [docs/mammo域偏移研究构思.md](../docs/mammo域偏移研究构思.md)(顶部 v15 流程)。

## 结构

```
mammo/
  src/
    datasets.py   # 数据集注册表:5 个公开集的加载桩 + mock 数据(无真数据先跑通管道)
    model.py      # backbone(EfficientNet-B2)+ 判别头
    metrics.py    # AUC / sens@spec / ECE
    train.py      # 合并若干数据集训练,存 checkpoint
    features.py   # S2:冻结 backbone 倒特征
    eval_l2o.py   # leave-2-out 全组合,输出 results/drop_table.md
  requirements.txt
```

## 快速开始(mock 模式,验证管道)

```bash
pip install -r mammo/requirements.txt
python -m mammo.src.train --datasets vindr,rsna,cmmd --mock --epochs 2 --out runs/mock
python -m mammo.src.eval_l2o --datasets vindr,rsna,cmmd,inbreast,cbis --mock --epochs 2 --out results/
```

mock 模式用合成图像(每个"数据集"模拟不同厂商的 gamma/对比度风格),
只为验证训练/评测/出表全链路,数字无意义。

## 接真数据

在 `src/datasets.py` 的注册表里为每个数据集填 `root` 路径并实现 `_load_index`
(返回 `[(图路径, 0/1 标签), ...]`,病人级切分)。其余代码不用动。

数据获取:VinDr-Mammo(PhysioNet)/ RSNA 2023(Kaggle)/ CMMD(TCIA)/
INbreast(申请)/ CBIS-DDSM(TCIA)。

## Go/No-Go 判据

`results/drop_table.md` 中 OOD 相对 ID 的 AUC 掉点:
**< 3 点 → 换方向;≥ 5 点 → 方法空间充足,继续 S2–S4。**
