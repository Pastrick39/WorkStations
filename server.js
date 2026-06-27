const http = require("http");
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");

const PORT = Number(process.env.PORT || 3000);
const APP_ID = process.env.FEISHU_APP_ID;
const APP_SECRET = process.env.FEISHU_APP_SECRET;
const APP_BASE_URL = process.env.APP_BASE_URL || `http://localhost:${PORT}`;
const FEISHU_OPEN_API = "https://open.feishu.cn/open-apis";

const mimeTypes = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "application/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".svg": "image/svg+xml"
};

function sendJson(res, statusCode, data) {
  res.writeHead(statusCode, {
    "Content-Type": "application/json; charset=utf-8",
    "Cache-Control": "no-store"
  });
  res.end(JSON.stringify(data));
}

function getRedirectUri() {
  return `${APP_BASE_URL.replace(/\/$/, "")}/`;
}

function createState() {
  return crypto.randomBytes(12).toString("hex");
}

async function requestFeishu(pathname, options) {
  const response = await fetch(`${FEISHU_OPEN_API}${pathname}`, options);
  const payload = await response.json();

  if (!response.ok || payload.code !== 0) {
    const message = payload.msg || `Feishu API error: ${response.status}`;
    throw new Error(message);
  }

  return payload;
}

async function getAppAccessToken() {
  const payload = await requestFeishu("/auth/v3/app_access_token/internal", {
    method: "POST",
    headers: {
      "Content-Type": "application/json; charset=utf-8"
    },
    body: JSON.stringify({
      app_id: APP_ID,
      app_secret: APP_SECRET
    })
  });

  return payload.app_access_token;
}

async function getUserAccessToken(code) {
  const appAccessToken = await getAppAccessToken();
  const payload = await requestFeishu("/authen/v1/access_token", {
    method: "POST",
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      Authorization: `Bearer ${appAccessToken}`
    },
    body: JSON.stringify({
      grant_type: "authorization_code",
      code
    })
  });

  return payload.data.access_token;
}

async function getFeishuUser(code) {
  const userAccessToken = await getUserAccessToken(code);
  const payload = await requestFeishu("/authen/v1/user_info", {
    method: "GET",
    headers: {
      Authorization: `Bearer ${userAccessToken}`
    }
  });

  return payload.data;
}

function serveStatic(req, res) {
  const url = new URL(req.url, APP_BASE_URL);
  const pathname = decodeURIComponent(url.pathname);
  const filePath = path.join(__dirname, pathname === "/" ? "index.html" : pathname);

  if (!filePath.startsWith(__dirname)) {
    res.writeHead(403);
    res.end("Forbidden");
    return;
  }

  fs.readFile(filePath, (error, content) => {
    if (error) {
      res.writeHead(404);
      res.end("Not found");
      return;
    }

    const contentType = mimeTypes[path.extname(filePath)] || "application/octet-stream";
    res.writeHead(200, { "Content-Type": contentType });
    res.end(content);
  });
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, APP_BASE_URL);

  if (url.pathname === "/api/feishu/config") {
    if (!APP_ID || !APP_SECRET) {
      sendJson(res, 500, {
        error: "请先配置 FEISHU_APP_ID 和 FEISHU_APP_SECRET"
      });
      return;
    }

    const redirectUri = getRedirectUri();
    const state = createState();
    const authUrl = new URL(`${FEISHU_OPEN_API}/authen/v1/index`);
    authUrl.searchParams.set("app_id", APP_ID);
    authUrl.searchParams.set("redirect_uri", redirectUri);
    authUrl.searchParams.set("state", state);

    sendJson(res, 200, {
      appId: APP_ID,
      redirectUri,
      state,
      authUrl: authUrl.toString()
    });
    return;
  }

  if (url.pathname === "/api/feishu/me") {
    const code = url.searchParams.get("code");
    if (!code) {
      sendJson(res, 400, { error: "缺少飞书授权 code" });
      return;
    }

    try {
      const user = await getFeishuUser(code);
      sendJson(res, 200, {
        name: user.name || user.en_name || user.open_id,
        avatarUrl: user.avatar_url,
        openId: user.open_id,
        unionId: user.union_id,
        email: user.email,
        mobile: user.mobile
      });
    } catch (error) {
      sendJson(res, 502, { error: error.message });
    }
    return;
  }

  serveStatic(req, res);
});

server.listen(PORT, () => {
  console.log(`WorkStation is running at http://localhost:${PORT}`);
});
