"""与 s02 相同：普通工具函数 + TOOLS + TOOL_HANDLERS。

文件操作直接读写目标文件，不创建候选版本，不加入文件保护或审批规则。
WORKDIR 由 CLI 设置；这一版只支持同一进程中运行一个工作区。
"""

from pathlib import Path
import subprocess
import sys


WORKDIR = Path.cwd()
OUTPUT_LIMIT = 12000
SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", ".evocode", "node_modules"}


def run_read(path: str, limit: int = 200) -> str:
    lines = (WORKDIR / path).read_text(encoding="utf-8").splitlines()
    text = "\n".join(f"{number}: {line}" for number, line in enumerate(lines[:limit], 1))
    if len(lines) > limit:
        text += f"\n... 还有 {len(lines) - limit} 行"
    return text


def run_write(path: str, content: str) -> str:
    target = WORKDIR / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return f"已写入 {path}"


def run_edit(path: str, old_text: str, new_text: str) -> str:
    target = WORKDIR / path
    text = target.read_text(encoding="utf-8")
    if not old_text or old_text not in text:
        return "Error: old_text 为空或未找到"
    # 与 s02 一样，只替换首次匹配的位置，然后直接写回原文件。
    target.write_text(text.replace(old_text, new_text, 1), encoding="utf-8")
    return f"已修改 {path}"


def iter_files():
    """搜索时跳过依赖和生成目录，减少无关结果；这不是权限检查。"""
    for path in WORKDIR.rglob("*"):
        if path.is_file() and not any(part in SKIP_DIRS for part in path.relative_to(WORKDIR).parts):
            yield path


def run_glob(pattern: str) -> str:
    matches = [str(path.relative_to(WORKDIR)) for path in iter_files()
               if path.relative_to(WORKDIR).match(pattern)]
    return "\n".join(matches[:200]) or "未找到匹配文件"


def run_search(query: str) -> str:
    """P0 使用字面文本搜索；P1 再升级为 Code RAG。"""
    matches = []
    for path in iter_files():
        if path.stat().st_size > 1_000_000:
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeError:
            continue
        for number, line in enumerate(lines, 1):
            if query in line:
                matches.append(f"{path.relative_to(WORKDIR)}:{number}: {line}")
                if len(matches) >= 100:
                    return "\n".join(matches)
    return "\n".join(matches) or "未找到匹配内容"


def command_output(result: subprocess.CompletedProcess) -> str:
    # 退出码必须交给模型；没有输出并不代表命令成功。
    text = (result.stdout + result.stderr).strip()
    return f"exit_code: {result.returncode}\n{text or '(no output)'}"


def run_bash(command: str) -> str:
    result = subprocess.run(command, shell=True, cwd=WORKDIR,
                            capture_output=True, text=True, encoding="utf-8",
                            errors="replace", timeout=120)
    return command_output(result)


def run_tests(path: str = "tests") -> str:
    # 参数列表不经过 Shell；sys.executable 保证 pytest 使用当前 Python 环境。
    result = subprocess.run([sys.executable, "-m", "pytest", path, "-q"],
                            cwd=WORKDIR, capture_output=True, text=True,
                            encoding="utf-8", errors="replace", timeout=120)
    return command_output(result)


# TOOLS 给模型阅读：工具名称、用途、参数 Schema。
# 直接展开定义，便于与 s02 对照，不再使用额外的 Schema 构造函数。
TOOLS = [
    {"name": "bash", "description": "在当前工作目录执行本地 Shell 命令。",
     "input_schema": {"type": "object", "properties": {"command": {"type": "string"}},
                      "required": ["command"]}},
    {"name": "read_file", "description": "读取 UTF-8 文本文件，显示行号。",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "limit": {"type": "integer"}},
                      "required": ["path"]}},
    {"name": "write_file", "description": "写入文件；文件存在则覆盖内容。",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                      "required": ["path", "content"]}},
    {"name": "edit_file", "description": "将文件中首次出现的 old_text 替换为 new_text。",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"}},
                      "required": ["path", "old_text", "new_text"]}},
    {"name": "glob", "description": "按路径模式查找文件，如 *.py 或 **/*.py。",
     "input_schema": {"type": "object", "properties": {"pattern": {"type": "string"}},
                      "required": ["pattern"]}},
    {"name": "search_code", "description": "按字面文本搜索代码，返回文件路径和行号。",
     "input_schema": {"type": "object", "properties": {"query": {"type": "string"}},
                      "required": ["query"]}},
    {"name": "run_tests", "description": "使用当前 Python 环境运行 pytest，返回退出码和日志。",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}},
                      "required": []}},
]

# TOOL_HANDLERS 给 Python 使用：工具名称 → 函数本身，不在这里调用函数。
TOOL_HANDLERS = {
    "bash": run_bash,
    "read_file": run_read,
    "write_file": run_write,
    "edit_file": run_edit,
    "glob": run_glob,
    "search_code": run_search,
    "run_tests": run_tests,
}
