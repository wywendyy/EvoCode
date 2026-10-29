"""离线验证核心行为；假模型不依赖 Anthropic SDK。

测试创建新的产物目录并保留；文件覆盖、编辑和外部命令使用 mock 验证。
"""

import copy
import io
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import uuid
from contextlib import redirect_stdout

from evocode.agent import tools
from evocode.agent.loop import agent_loop
from evocode.trace import create_trace


class Block(SimpleNamespace):
    def model_dump(self):
        return vars(self)


def text_response(text="完成", stop_reason="end_turn"):
    return SimpleNamespace(content=[Block(type="text", text=text)],
                           stop_reason=stop_reason, usage=Block(input_tokens=10, output_tokens=5))


def tool_response(name, arguments, call_id="call_1"):
    return SimpleNamespace(content=[Block(type="tool_use", name=name, input=arguments, id=call_id)],
                           stop_reason="tool_use", usage=Block(input_tokens=10, output_tokens=5))


class FakeClient:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.requests = []
        self.messages = SimpleNamespace(create=self.create)

    def create(self, **request):
        self.requests.append(copy.deepcopy(request))
        return next(self.responses)


class AgentTests(unittest.TestCase):
    def setUp(self):
        self.workspace = Path(__file__).parent / "artifacts" / uuid.uuid4().hex
        self.workspace.mkdir(parents=True)
        self.previous = tools.WORKDIR
        tools.WORKDIR = self.workspace

    def tearDown(self):
        tools.WORKDIR = self.previous

    def run_agent(self, client, **kwargs):
        with redirect_stdout(io.StringIO()):
            return agent_loop([{"role": "user", "content": "检查代码"}], client, "fake-model", **kwargs)

    def test_loop_pairs_tool_request_and_result(self):
        with (self.workspace / "hello.py").open("x", encoding="utf-8") as stream:
            stream.write("print('hello')\n")
        client = FakeClient([tool_response("read_file", {"path": "hello.py"}), text_response()])
        result = self.run_agent(client)
        history = client.requests[1]["messages"]
        self.assertEqual(history[1]["content"][0].id, history[2]["content"][0]["tool_use_id"])
        self.assertIn("print('hello')", history[2]["content"][0]["content"])
        self.assertEqual(result["status"], "completed")

    def test_unknown_tool_and_bad_arguments_are_observations(self):
        for name, arguments in [("missing", {}), ("read_file", {})]:
            with self.subTest(name=name):
                client = FakeClient([tool_response(name, arguments), text_response()])
                self.run_agent(client)
                observation = client.requests[1]["messages"][-1]["content"][0]["content"]
                self.assertTrue(observation.startswith(("Unknown:", "Error:")))

    def test_direct_write_and_edit_have_no_candidate_layer(self):
        # mock 验证直接写回目标路径，不需要真实覆盖任何已有文件。
        with patch.object(Path, "write_text") as write:
            tools.run_write("new.py", "new content")
            write.assert_called_once_with("new content", encoding="utf-8")
        with patch.object(Path, "read_text", return_value="old old"), patch.object(Path, "write_text") as write:
            tools.run_edit("module.py", "old", "new")
            write.assert_called_once_with("new old", encoding="utf-8")

    def test_shell_and_pytest_return_exit_code(self):
        with patch.object(subprocess, "run", return_value=SimpleNamespace(
            returncode=1, stdout="failed", stderr="details"
        )) as run:
            self.assertIn("exit_code: 1", tools.run_bash("example-command"))
            self.assertTrue(run.call_args.kwargs["shell"])
            self.assertIn("exit_code: 1", tools.run_tests("tests/test_sample.py"))
            self.assertEqual(run.call_args.args[0][1:], ["-m", "pytest", "tests/test_sample.py", "-q"])
            self.assertNotIn("shell", run.call_args.kwargs)

    def test_timeout_is_returned_to_model(self):
        client = FakeClient([tool_response("bash", {"command": "example"}), text_response()])
        with patch.object(subprocess, "run", side_effect=subprocess.TimeoutExpired("example", 120)):
            self.run_agent(client)
        self.assertIn("TimeoutExpired", client.requests[1]["messages"][-1]["content"][0]["content"])

    def test_budget_and_truncated_response(self):
        result = self.run_agent(FakeClient([tool_response("glob", {"pattern": "*.py"})]), max_rounds=1)
        self.assertEqual(result["status"], "budget_exhausted")
        result = self.run_agent(FakeClient([text_response("未完成", "max_tokens")]))
        self.assertEqual(result["status"], "incomplete")

    def test_trace_preserves_messages_and_usage(self):
        trace = create_trace(self.workspace)
        self.run_agent(FakeClient([text_response()]), trace_path=trace)
        events = [json.loads(line) for line in trace.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(events[0]["messages"][0]["role"], "user")
        self.assertEqual(events[1]["usage"]["input_tokens"], 10)

    def test_search_returns_file_and_line(self):
        with (self.workspace / "sample.py").open("x", encoding="utf-8") as stream:
            stream.write("def target():\n    pass\n")
        self.assertIn("sample.py", tools.run_glob("*.py"))
        self.assertIn("sample.py:1: def target", tools.run_search("target"))

    def test_model_failure_returns_error(self):
        client = SimpleNamespace(messages=SimpleNamespace(create=lambda **kwargs: 1 / 0))
        result = self.run_agent(client)
        self.assertEqual(result["status"], "error")


if __name__ == "__main__":
    unittest.main()
