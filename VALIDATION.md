# P0 精简版验证记录

日期：2026-10-28；环境：Windows，Python 3.12.1。

实际运行：

```powershell
Set-Location D:\agent\EvoCode
python -B -m unittest discover -s tests -p 'test_*.py' -v
python -B -m evocode --help
```

9 项离线测试全部通过，测试耗时约 0.047 秒；CLI 帮助入口退出码为 0。
覆盖工具请求与结果配对、字典工具分发、错误反馈、命令超时、退出码、
轮数上限、响应提前中止、Trace 消息与 Token usage、文件搜索。
直接写入与编辑行为通过 mock 验证，测试没有真实覆盖已有文件。
外部命令和模型调用均为模拟，测试产物保留在 tests/artifacts 下。

当前环境未安装 anthropic 和 pytest，未调用真实 API，未运行真实模型驱动的修复验收。
依赖安装与 average 示例运行方法见 README。测试通过仅代表核心 Harness 离线检查通过。

旧实现（含旧文档与测试）保存在：
`.evocode/source-history/simple-2c0a39e170ae40b8a81be55da829038d/`。
旧版文件不参与当前代码执行。
