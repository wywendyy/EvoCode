"""只负责创建 SDK 客户端，模型调用本身直接写在 loop.py 中。"""


def create_client(config: dict):
    # 延迟导入：查看 CLI 帮助、运行离线测试时不需要安装 SDK。
    from anthropic import Anthropic

    return Anthropic(
        api_key=config["api_key"],
        base_url=config["base_url"],
        timeout=60.0,
        max_retries=0,
    )
