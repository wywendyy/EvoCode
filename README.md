# EvoCode · P0 学习版

沿用 learn-claude-code **章节目录**中 s01/s02 的写法：普通函数、TOOLS、
TOOL_HANDLERS 和直接展开的 Agent Loop。每个文件只负责一件事，核心代码有中文注释。

```text
evocode/
├── agent/
│   ├── loop.py       模型请求 → 工具调用 → 结果反馈
│   ├── tools.py      工具函数、TOOLS、TOOL_HANDLERS
│   └── context.py    系统提示
├── llm.py            创建 Anthropic SDK 客户端
├── config.py         读取环境变量，返回普通字典
├── trace.py          保存 JSONL 轨迹
└── cli.py            命令行入口
```

## 先读这两处

`loop.py` 中，熟悉的调用方式直接保留：

```python
response = client.messages.create(...)
messages.append({"role": "assistant", "content": response.content})
tool_calls = [block for block in response.content if block.type == "tool_use"]
```

工具分发仍然是：

```python
handler = TOOL_HANDLERS.get(block.name)
output = handler(**block.input) if handler else f"Unknown: {block.name}"
```

相比章节示例，只增加基础 Trace、错误反馈、最大模型调用轮数和 pytest 工具。
没有 Agent / Registry / Executor 类、协议适配类或自定义响应对象。

## 安装与配置

Python 3.11+，PowerShell：

```powershell
Set-Location D:\agent\EvoCode
python -m pip install -e '.[test]'
$env:ANTHROPIC_API_KEY = '你的密钥'
$env:MODEL_ID = '你的模型名称'
# 使用 Anthropic Messages 兼容服务时，可另外设置：
# $env:ANTHROPIC_BASE_URL = '服务商提供的接口地址'
```

`.env.example` 只是示例，程序不会自动加载 `.env`。
当前使用 Anthropic SDK，与 s01/s02 相同；OpenAI-compatible 接口需另写适配。

## 运行

```powershell
python -B -m evocode --help
python -B -m evocode --workspace D:\agent\EvoCode\examples\average_bug --task '读取 average.py 和测试，修复空列表输入异常，再运行测试。'
```

工具包括 bash、read_file、write_file、edit_file、glob、search_code、run_tests。
文件写入和编辑直接作用于目标文件；不生成候选工作区，没有文件保护规则、
路径权限检查、审批或 Docker 限制。`--workspace` 是当前目录，不是沙箱边界。
Windows 下 bash 工具通过 cmd.exe 执行；pytest 使用当前 Python 环境运行。
命令超时为 120 秒，模型每次最多看到 12000 字符工具输出。

每轮消息、响应、Token usage 和完整工具结果保存在工作区的
`.evocode/traces/<id>.jsonl`；API Key 配置字典不会写入 Trace。

## 状态与范围

- `completed`：模型正常结束工具调用，不代表测试一定通过。
- `incomplete`：模型因输出上限等原因提前停止。
- `budget_exhausted`：达到模型调用轮数上限，默认 12 轮。
- `error`：模型请求失败。

测试结果由 run_tests 返回的退出码与日志确认。当前没有自动判定修复成功的额外状态机，
也没有跨任务会话恢复、Git diff 集成、Code RAG、Memory Folding 或 Skill Evolution。
当前 WORKDIR 是模块变量，适合单工作区 CLI，不用于同进程并发任务。

## 离线测试

```powershell
python -B -m unittest discover -s tests -p 'test_*.py' -v
```

使用假模型和模拟进程，不调用 API、不执行模型生成的命令。
这些测试验证循环、分发和工具参数，不代表真实模型修复验收。
开发时的旧实现和测试产物保存在 `.evocode/source-history/`，不参与当前代码运行。
