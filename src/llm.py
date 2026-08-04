"""Anthropic 封装：claude-opus-5 + messages.parse 结构化输出。

注意：claude-opus-5 不接受 temperature/top_p/top_k 参数，思考默认开启；
裁判一致性靠 prompt 约束 + 同案多跑验收（见 README）。
"""

from typing import TypeVar

import anthropic
from pydantic import BaseModel

MODEL = "claude-opus-5"
MAX_TOKENS = 8192

_client: anthropic.Anthropic | None = None

T = TypeVar("T", bound=BaseModel)


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        # 零参构造：依次解析 ANTHROPIC_API_KEY / ANTHROPIC_AUTH_TOKEN / ant auth 登录态
        _client = anthropic.Anthropic()
    return _client


def call_structured(system: str, user: str, output_model: type[T]) -> T:
    """单轮结构化调用：返回校验通过的 Pydantic 实例。"""
    response = get_client().messages.parse(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=system,
        messages=[{"role": "user", "content": user}],
        output_format=output_model,
    )
    if response.stop_reason == "refusal":
        raise RuntimeError(f"模型拒绝了请求：{response.stop_details}")
    if response.parsed_output is None:
        raise RuntimeError("结构化输出解析失败（parsed_output 为空）")
    return response.parsed_output
