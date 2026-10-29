"""用两个普通函数记录 JSONL；每行就是一个执行事件。"""

from datetime import datetime, timezone
import json
from pathlib import Path
import uuid


def create_trace(workspace: Path) -> Path:
    directory = workspace / ".evocode" / "traces"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"{uuid.uuid4().hex}.jsonl"


def record_event(path: Path | None, event: str, **data) -> None:
    if path is None:
        return
    entry = {"time": datetime.now(timezone.utc).isoformat(), "event": event, **data}
    with path.open("a", encoding="utf-8") as stream:
        # SDK 的内容块不是普通字典，model_dump() 将其转换成可保存的数据。
        stream.write(json.dumps(entry, ensure_ascii=False,
                                default=lambda value: value.model_dump()) + "\n")
