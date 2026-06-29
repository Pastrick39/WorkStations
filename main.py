import asyncio
import json
import mimetypes
import os
import threading
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path

import DBtools


ROOT = Path(__file__).resolve().parent
FEISHU_OPEN_API = "https://open.feishu.cn/open-apis"


def load_env_file():
    env_file = ROOT / ".env"
    if not env_file.exists():
        return

    for line in env_file.read_text(encoding="utf-8").splitlines():
        value = line.strip()
        if not value or value.startswith("#") or "=" not in value:
            continue

        key, raw_value = value.split("=", 1)
        os.environ.setdefault(key.strip(), raw_value.strip().strip('"').strip("'"))


load_env_file()


def get_port():
    return int(os.environ.get("PORT", "3000"))


def get_base_url():
    return os.environ.get("APP_BASE_URL") or f"http://localhost:{get_port()}"


def json_response(status, data):
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    return {
        "status": status,
        "headers": [
            (b"content-type", b"application/json; charset=utf-8"),
            (b"cache-control", b"no-store"),
        ],
        "body": body,
    }


def text_response(status, text):
    return {
        "status": status,
        "headers": [(b"content-type", b"text/plain; charset=utf-8")],
        "body": text.encode("utf-8"),
    }


async def send_response(send, response):
    await send(
        {
            "type": "http.response.start",
            "status": response["status"],
            "headers": response["headers"],
        }
    )
    await send(
        {
            "type": "http.response.body",
            "body": response["body"],
        }
    )


async def read_json_body(receive):
    body = b""
    more_body = True

    while more_body:
        message = await receive()
        body += message.get("body", b"")
        more_body = message.get("more_body", False)

    if not body:
        return {}

    return json.loads(body.decode("utf-8"))


def request_feishu(pathname, method="GET", token=None, payload=None):
    headers = {"Content-Type": "application/json; charset=utf-8"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        f"{FEISHU_OPEN_API}{pathname}",
        data=data,
        headers=headers,
        method=method,
    )

    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="ignore")
        raise RuntimeError(detail or f"Feishu API HTTP {error.code}") from error

    if result.get("code") != 0:
        raise RuntimeError(result.get("msg") or "Feishu API 调用失败")

    return result


def get_app_access_token():
    app_id = os.environ.get("FEISHU_APP_ID")
    app_secret = os.environ.get("FEISHU_APP_SECRET")

    result = request_feishu(
        "/auth/v3/app_access_token/internal",
        method="POST",
        payload={
            "app_id": app_id,
            "app_secret": app_secret,
        },
    )
    return result["app_access_token"]


def get_feishu_user(code):
    app_access_token = get_app_access_token()
    token_result = request_feishu(
        "/authen/v1/access_token",
        method="POST",
        token=app_access_token,
        payload={
            "grant_type": "authorization_code",
            "code": code,
        },
    )

    user_access_token = token_result["data"]["access_token"]
    user_result = request_feishu(
        "/authen/v1/user_info",
        method="GET",
        token=user_access_token,
    )
    return user_result["data"]


def build_auth_url():
    base_url = get_base_url().rstrip("/")
    query = urllib.parse.urlencode(
        {
            "app_id": os.environ.get("FEISHU_APP_ID"),
            "redirect_uri": f"{base_url}/",
            "state": "workstation",
        }
    )
    return f"{FEISHU_OPEN_API}/authen/v1/index?{query}"


def get_operator(body):
    operator = body.get("operator") if isinstance(body, dict) else {}
    return operator if isinstance(operator, dict) else {}


async def is_zhongkong_admin(operator):
    try:
        return await asyncio.to_thread(DBtools.is_zhongkong_admin, operator)
    except Exception:
        return False


async def require_zhongkong_admin(body):
    operator = get_operator(body)
    if await is_zhongkong_admin(operator):
        return None
    return json_response(403, {"error": "只有中控平台管理员可以新增、修改或删除应用"})


async def handle_apps_api(method, receive):
    if method == "GET":
        try:
            apps = await asyncio.to_thread(DBtools.get_yingyong_apps)
            return json_response(200, {"apps": apps})
        except Exception as error:
            return json_response(500, {"error": str(error)})

    if method == "POST":
        try:
            body = await read_json_body(receive)
        except json.JSONDecodeError:
            return json_response(400, {"error": "请求 JSON 格式不正确"})

        forbidden = await require_zhongkong_admin(body)
        if forbidden:
            return forbidden

        name = str(body.get("name", "")).strip()
        url = str(body.get("url", "")).strip()
        portal = str(body.get("portal", "")).strip()
        created_by = str(body.get("createdBy", "")).strip() or None

        if not name or not url or not portal:
            return json_response(400, {"error": "应用名称、URL 和所属端不能为空"})

        try:
            app_row = await asyncio.to_thread(
                DBtools.add_yingyong_app,
                name,
                url,
                portal,
                created_by,
            )
            return json_response(201, {"app": app_row})
        except Exception as error:
            return json_response(500, {"error": str(error)})

    return json_response(405, {"error": "不支持的请求方法"})


async def handle_app_api(app_id, method, receive):
    if method == "PUT":
        try:
            body = await read_json_body(receive)
        except json.JSONDecodeError:
            return json_response(400, {"error": "请求 JSON 格式不正确"})

        forbidden = await require_zhongkong_admin(body)
        if forbidden:
            return forbidden

        name = str(body.get("name", "")).strip()
        url = str(body.get("url", "")).strip()

        if not name or not url:
            return json_response(400, {"error": "应用名称和 URL 不能为空"})

        try:
            app_row = await asyncio.to_thread(
                DBtools.update_yingyong_app,
                app_id,
                name,
                url,
            )
            if not app_row:
                return json_response(404, {"error": "应用不存在或已删除"})
            return json_response(200, {"app": app_row})
        except Exception as error:
            return json_response(500, {"error": str(error)})

    if method == "DELETE":
        try:
            body = await read_json_body(receive)
        except json.JSONDecodeError:
            return json_response(400, {"error": "请求 JSON 格式不正确"})

        forbidden = await require_zhongkong_admin(body)
        if forbidden:
            return forbidden

        try:
            deleted = await asyncio.to_thread(DBtools.delete_yingyong_app, app_id)
            if not deleted:
                return json_response(404, {"error": "应用不存在或已删除"})
            return json_response(200, {"ok": True})
        except Exception as error:
            return json_response(500, {"error": str(error)})

    return json_response(405, {"error": "不支持的请求方法"})


async def handle_api(path, query, method, receive):
    if path == "/api/apps":
        return await handle_apps_api(method, receive)

    if path.startswith("/api/apps/"):
        raw_app_id = path.removeprefix("/api/apps/").strip("/")
        if not raw_app_id.isdigit():
            return json_response(400, {"error": "应用 ID 不正确"})
        return await handle_app_api(int(raw_app_id), method, receive)

    if path == "/api/me/permissions":
        if method != "POST":
            return json_response(405, {"error": "不支持的请求方法"})

        try:
            body = await read_json_body(receive)
        except json.JSONDecodeError:
            return json_response(400, {"error": "请求 JSON 格式不正确"})

        is_admin = await is_zhongkong_admin(get_operator(body))
        return json_response(200, {"isAdmin": is_admin})

    if path == "/api/feishu/config":
        if not os.environ.get("FEISHU_APP_ID") or not os.environ.get("FEISHU_APP_SECRET"):
            return json_response(
                500,
                {"error": "请先在 .env 中配置 FEISHU_APP_ID 和 FEISHU_APP_SECRET"},
            )

        base_url = get_base_url().rstrip("/")
        return json_response(
            200,
            {
                "appId": os.environ.get("FEISHU_APP_ID"),
                "redirectUri": f"{base_url}/",
                "authUrl": build_auth_url(),
            },
        )

    if path == "/api/feishu/me":
        code = urllib.parse.parse_qs(query).get("code", [""])[0]
        if not code:
            return json_response(400, {"error": "缺少飞书授权 code"})

        try:
            user = await asyncio.to_thread(get_feishu_user, code)
            return json_response(
                200,
                {
                    "name": user.get("name") or user.get("en_name") or user.get("open_id"),
                    "avatarUrl": user.get("avatar_url"),
                    "openId": user.get("open_id"),
                    "unionId": user.get("union_id"),
                    "email": user.get("email"),
                    "mobile": user.get("mobile"),
                },
            )
        except Exception as error:
            return json_response(502, {"error": str(error)})

    return json_response(404, {"error": "接口不存在"})


def get_static_file(path):
    safe_path = urllib.parse.unquote(path)
    file_path = ROOT / ("index.html" if safe_path == "/" else safe_path.lstrip("/"))
    resolved = file_path.resolve()

    if not str(resolved).startswith(str(ROOT)):
        return text_response(403, "Forbidden")

    if not resolved.exists() or not resolved.is_file():
        return text_response(404, "Not found")

    content_type = mimetypes.guess_type(resolved.name)[0] or "application/octet-stream"
    if content_type.startswith("text/") or resolved.suffix in {".js", ".css"}:
        content_type = f"{content_type}; charset=utf-8"

    return {
        "status": 200,
        "headers": [(b"content-type", content_type.encode("utf-8"))],
        "body": resolved.read_bytes(),
    }


def open_browser_once():
    if os.environ.get("AUTO_OPEN_BROWSER", "1") == "0":
        return

    url = f"http://localhost:{get_port()}"
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()


async def app(scope, receive, send):
    if scope["type"] == "lifespan":
        while True:
            message = await receive()
            if message["type"] == "lifespan.startup":
                open_browser_once()
                await send({"type": "lifespan.startup.complete"})
            elif message["type"] == "lifespan.shutdown":
                await send({"type": "lifespan.shutdown.complete"})
                return

    if scope["type"] != "http":
        return

    path = scope.get("path", "/")
    query = scope.get("query_string", b"").decode("utf-8")

    if path.startswith("/api/"):
        method = scope.get("method", "GET").upper()
        response = await handle_api(path, query, method, receive)
    else:
        response = get_static_file(path)

    await send_response(send, response)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=get_port(), reload=True)
