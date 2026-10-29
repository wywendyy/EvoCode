"""对照 s01/s02 阅读：主流程仍然在一个普通函数中直接展开。"""

from ..trace import record_event
from . import tools
from .context import build_system
from .tools import TOOLS, TOOL_HANDLERS


def agent_loop(messages: list, client, model: str, max_rounds: int = 12,
               trace_path=None) -> dict:
    system = build_system(tools.WORKDIR)

    # 相比 s01 的 while True，只增加轮数上限，防止一直调用模型。
    for _ in range(max_rounds):
        # 1. 发送系统提示、完整消息历史和工具定义。
        record_event(trace_path, "model_request", model=model, system=system, messages=messages)
        try:
            response = client.messages.create(
                model=model, system=system, messages=messages,
                tools=TOOLS, max_tokens=4096,
            )
        except Exception as exc:
            record_event(trace_path, "model_error", error_type=type(exc).__name__)
            return {"status": "error", "answer": f"模型请求失败：{type(exc).__name__}"}

        # 2. 保存模型响应，保证后面的工具结果有对应的请求。
        messages.append({"role": "assistant", "content": response.content})
        record_event(trace_path, "model_response", content=response.content,
                     stop_reason=response.stop_reason, usage=response.usage)

        # 3. 没有工具调用时结束本次任务；这不等于代码一定修复成功。
        tool_calls = [block for block in response.content if block.type == "tool_use"]
        if not tool_calls:
            answer = "\n".join(block.text for block in response.content if block.type == "text")
            status = "completed" if response.stop_reason == "end_turn" else "incomplete"
            return {"status": status, "answer": answer}

        # 4. 与 s02 相同：按名称查函数，展开参数，然后调用。
        results = []
        for block in tool_calls:
            handler = TOOL_HANDLERS.get(block.name)
            try:
                output = handler(**block.input) if handler else f"Unknown: {block.name}"
            except Exception as exc:
                # 文件不存在、参数错误、命令超时等，作为观察结果交回模型。
                output = f"Error: {type(exc).__name__}: {exc}"

            print(f"> {block.name}\n{output[:200]}")
            record_event(trace_path, "tool_result", tool_use_id=block.id,
                         name=block.name, arguments=block.input, output=output)
            results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                # Trace 保留完整结果，模型上下文只接收截短后的副本。
                "content": output[:tools.OUTPUT_LIMIT],
            })

        # 5. 将本轮所有工具结果交回模型，进入下一轮。
        messages.append({"role": "user", "content": results})

    return {"status": "budget_exhausted", "answer": "达到模型调用轮数上限，任务尚未确认完成。"}
