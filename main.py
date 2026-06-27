import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PORT = int(os.environ.get("PORT", "3000"))
LOCAL_URL = f"http://localhost:{PORT}"


def wait_for_server(url, timeout=15):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1):
                return True
        except (urllib.error.URLError, TimeoutError):
            time.sleep(0.3)
    return False


def main():
    server_file = ROOT / "server.js"
    if not server_file.exists():
        print("未找到 server.js，无法启动项目。")
        return 1

    env = os.environ.copy()
    env.setdefault("PORT", str(PORT))

    print(f"正在启动中控平台：{LOCAL_URL}")
    server = subprocess.Popen(
        ["node", str(server_file)],
        cwd=ROOT,
        env=env,
    )

    try:
        if wait_for_server(LOCAL_URL):
            webbrowser.open(LOCAL_URL)
            print("页面已自动打开。按 Ctrl+C 停止服务。")
        else:
            print("服务启动超时，请检查 Node.js 是否已安装或端口是否被占用。")
            return 1

        server.wait()
        return server.returncode
    except KeyboardInterrupt:
        print("\n正在停止服务...")
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
