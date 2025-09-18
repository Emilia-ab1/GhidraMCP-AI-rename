import re
import requests
from typing import Dict

DEFAULT_ENDPOINT = "http://127.0.0.1:8080/methods?offset=0&limit=999999"
TIMEOUT_SECONDS = 1.5


def check_connection_and_count(pattern: str, endpoint: str = DEFAULT_ENDPOINT) -> Dict[str, object]:
    """
    在 1500ms 超时内请求 Ghidra 插件，统计总函数数量与正则匹配数量。

    返回字典：
    {
        "connected": bool,
        "total": int,
        "matched": int,
        "error": str | None
    }
    """
    result = {"connected": False, "total": 0, "matched": 0, "error": None}

    try:
        response = requests.get(endpoint, timeout=TIMEOUT_SECONDS)
        if not response.ok:
            result["error"] = f"HTTP {response.status_code}"
            return result

        lines = response.text.splitlines() if response.text else []
        result["connected"] = True
        result["total"] = len(lines)

        try:
            regex = re.compile(pattern) if pattern else re.compile("")
        except re.error as e:
            result["error"] = f"正则错误: {e}"
            return result

        matched = 0
        for line in lines:
            if regex.search(line):
                matched += 1
        result["matched"] = matched
        return result

    except requests.Timeout:
        result["error"] = "请求超时"
        return result
    except Exception as e:
        result["error"] = str(e)
        return result 


if __name__ == "__main__":
    print(check_connection_and_count("FUN_"))