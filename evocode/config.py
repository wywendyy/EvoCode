"""读取配置：普通函数返回字典，暂不引入配置类。"""

import os
from pathlib import Path


def load_config(workspace: str | Path) -> dict:
    workspace = Path(workspace).resolve()
    if not workspace.is_dir():
        raise ValueError(f"工作目录不存在：{workspace}")
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    model = os.getenv("MODEL_ID", "")
    if not api_key or not model:
        raise ValueError("请设置 ANTHROPIC_API_KEY 和 MODEL_ID")
    return {
        "workspace": workspace,
        "api_key": api_key,
        "model": model,
        "base_url": os.getenv("ANTHROPIC_BASE_URL") or None,
    }
