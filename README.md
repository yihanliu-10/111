# 多智能体信贷决策 Demo

模型出数，Agent 做决策：双头模型输出 p_want（意愿）和 p_risk（风险），
后接营销/风控辩论 + 裁判裁决的 Agent 链。设计文档见 [docs/辩论模块设计.md](docs/辩论模块设计.md)。

## 流程

```
案件包(scores + SHAP + 当期政策)
  → S1 硬规则闸门(纯代码)  ──► AUTO_APPROVE / AUTO_REJECT（零 LLM 成本）
  → S2 营销/风控独立立论
  → S3 反驳轮(最多1轮，收敛则跳过)
  → S4 裁判裁决(结构化输出)
  → S5 确定性校验(档位/等级边界/硬线双保险；违规打回一次，再违规转人工)
  → S6 审计落盘(audit/*.json，每案完整辩论记录)
```

## 运行

```bash
pip install -r requirements.txt
```

不花 token 先跑通管道（确定性 mock，验证状态机/校验/审计）：

```bash
python run_demo.py --mock
```

真实调用（需要 `ANTHROPIC_API_KEY`，或已 `ant auth login`）：

```bash
python run_demo.py --case C003_灰区_高意愿高风险
```

灰区案件每案约 5 次 LLM 调用（2 立论 + 2 反驳 + 1 裁决），建议先单案跑。

## 目录

| 文件 | 职责 |
|---|---|
| `src/schemas.py` | 案件包 / 辩论输出 / 裁决的 Pydantic 模型（同时是 LLM 结构化输出 schema） |
| `src/policy.py` | 当期政策：档位、等级边界、风险偏好、闸门参数。政策变了只改这里 |
| `src/case_packet.py` | 案件包组装。接真模型时把入参换成 LightGBM 预测 + SHAP 即可 |
| `src/gate.py` | S1 硬规则闸门 |
| `src/prompts.py` | 三个角色的 prompt（营销/风控除立场段外逐字对称） |
| `src/agents.py` | Agent 调用入口，含 mock 路径 |
| `src/llm.py` | Anthropic 封装（claude-opus-5 + messages.parse 结构化输出） |
| `src/validator.py` | S5 确定性校验 |
| `src/orchestrator.py` | 状态机 |
| `src/audit.py` | 审计落盘 |
| `data/mock_cases.json` | 4 个手工案件：快速通过 / 硬拒绝 / 两个灰区 |

## 已知约束与后续

- claude-opus-5 不接受 temperature 参数；裁判一致性靠 prompt 约束 + 同案多跑验收。
- 二期：SHAP 归因摘要 Agent（面向客户经理的中文解释）、复盘 Agent（swap set 离线评估）、
  双头 LightGBM 真模型接入。
