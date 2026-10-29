"""入口负责读取参数、创建客户端、调用循环和打印结果。"""

import argparse
from pathlib import Path

from .agent import tools
from .agent.loop import agent_loop
from .config import load_config
from .llm import create_client
from .trace import create_trace, record_event


def main() -> None:
    parser = argparse.ArgumentParser(description="EvoCode：s01/s02 风格的最小 Agent")
    parser.add_argument("--workspace", type=Path, default=Path.cwd(), help="工具执行的当前目录")
    parser.add_argument("--task", help="省略则在终端输入一次任务")
    parser.add_argument("--max-rounds", type=int, default=12)
    args = parser.parse_args()
    if args.max_rounds < 1:
        parser.error("--max-rounds 必须大于 0")

    try:
        config = load_config(args.workspace)
        client = create_client(config)
    except (ValueError, ImportError) as exc:
        parser.exit(2, f"启动失败：{exc}\n请参照 README 配置环境和依赖。\n")

    tools.WORKDIR = config["workspace"]
    query = args.task if args.task is not None else input("任务 > ")
    if not query.strip():
        parser.error("任务不能为空")

    messages = [{"role": "user", "content": query}]
    trace_path = create_trace(tools.WORKDIR)
    record_event(trace_path, "task_started", query=query, workspace=str(tools.WORKDIR), model=config["model"])
    result = agent_loop(messages, client, config["model"], args.max_rounds, trace_path)
    record_event(trace_path, "task_finished", **result)
    print(f"\n{result['answer']}\n\n状态：{result['status']}\nTrace：{trace_path}")
    if result["status"] != "completed":
        raise SystemExit(1)
