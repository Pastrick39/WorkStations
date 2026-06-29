# WorkStation 企业中控平台

WorkStation 是一个放在飞书企业自建应用里的应用入口页。用户从飞书进入 WorkStation 后，平台会通过飞书 OAuth 获取当前用户信息。用户点击某个应用时，WorkStation 会把当前用户信息发送给该应用配置的后端接口，由目标系统决定如何登录、跳转或展示页面。

## 本地运行

```bash
uvicorn main:app --reload --port 3000
```

默认访问：

```text
http://localhost:3000
```

## 环境变量

配置 `.env`：

```env
PORT=3000
APP_BASE_URL=http://localhost:3000
FEISHU_APP_ID=cli_xxx
FEISHU_APP_SECRET=xxx
```

正式部署时，`APP_BASE_URL` 改成飞书用户能访问到的 HTTPS 地址：

```text
https://workstation.example.com
```

## 飞书应用配置

在飞书开放平台的企业自建应用中配置：

- 网页应用地址：`https://workstation.example.com`
- 重定向 URL：`https://workstation.example.com/`
- 权限：按飞书后台要求开通获取登录用户信息相关权限

本地测试时，重定向 URL 可配置：

```text
http://localhost:3000/
```

## 应用入口保存

应用入口保存在 `TC.dbo.YingYong` 表。

页面打开时会调用：

```text
GET /api/apps
```

新增应用时会调用：

```text
POST /api/apps
```

新增应用时填写的 `URL` 不是普通页面地址，而是目标系统用于接收用户信息的后端接口地址。

例如：

```text
https://sample-system.example.com/api/workstation-login
```

## 新项目接入方式

一个新系统想接入 WorkStation，需要做 3 件事：

1. 在新系统里提供一个接收用户信息的后端接口。
2. 这个接口允许 WorkStation 页面跨域请求。
3. 接口返回一个 `redirectUrl`，WorkStation 会打开这个地址。

### 接口协议

请求方式：

```text
POST
```

请求头：

```text
Content-Type: application/json; charset=utf-8
```

请求体：

```json
{
  "appId": 1,
  "appName": "运营打样申请与验收",
  "portal": "运营端",
  "user": {
    "name": "张三",
    "openId": "ou_xxx",
    "unionId": "on_xxx",
    "email": "zhangsan@example.com",
    "mobile": "13800000000"
  }
}
```

字段说明：

| 字段 | 说明 |
| --- | --- |
| `appId` | WorkStation 里的应用 ID |
| `appName` | WorkStation 里的应用名称 |
| `portal` | 所属端口，例如 `运营端`、`采购端` |
| `user.name` | 飞书用户名 |
| `user.openId` | 飞书用户 open_id，建议作为用户匹配优先字段 |
| `user.unionId` | 飞书 union_id |
| `user.email` | 飞书邮箱，可能为空 |
| `user.mobile` | 飞书手机号，可能为空 |

响应体必须是 JSON，并且包含 `redirectUrl`：

```json
{
  "redirectUrl": "https://sample-system.example.com/dashboard"
}
```

WorkStation 收到 `redirectUrl` 后，会在新窗口打开它。

### 推荐登录逻辑

目标系统接口收到用户信息后，建议按这个顺序处理：

1. 优先用 `user.openId` 查找本系统账号。
2. 如果没有绑定关系，可以用 `user.name` 或 `user.email` 做兜底匹配。
3. 找到用户后，生成目标系统自己的登录态或一次性 token。
4. 返回带登录态的 `redirectUrl`。

例如：

```json
{
  "redirectUrl": "https://sample-system.example.com/dashboard?token=一次性token"
}
```

目标系统打开页面后，再用这个 token 换取正式登录态。

## 跨域要求

因为当前方案是浏览器 JavaScript 直接请求目标系统接口，所以目标系统必须允许 WorkStation 的域名跨域访问。

正式环境示例：

```text
Access-Control-Allow-Origin: https://workstation.example.com
Access-Control-Allow-Headers: Content-Type
Access-Control-Allow-Methods: POST, OPTIONS
```

本地开发时，如果 WorkStation 运行在 `http://localhost:3000`，目标系统也要允许：

```text
http://localhost:3000
```

## FastAPI 接入示例

安装依赖：

```bash
pip install fastapi uvicorn
```

示例代码：

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://workstation.example.com",
        "http://localhost:3000",
    ],
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


class UserInfo(BaseModel):
    name: str = ""
    openId: str = ""
    unionId: str = ""
    email: str = ""
    mobile: str = ""


class WorkstationLogin(BaseModel):
    appId: int
    appName: str
    portal: str
    user: UserInfo


@app.post("/api/workstation-login")
def workstation_login(data: WorkstationLogin):
    # 1. 通过 data.user.openId / data.user.name 匹配本系统账号
    # 2. 生成本系统自己的 token 或 session
    # 3. 返回最终需要打开的页面地址
    print("来自 WorkStation 的用户：", data.user)

    return {
        "redirectUrl": "https://sample-system.example.com/dashboard"
    }
```

本地启动：

```bash
uvicorn app:app --reload --port 8000
```

然后在 WorkStation 新增应用时填写：

```text
http://127.0.0.1:8000/api/workstation-login
```

## Flask 接入示例

安装依赖：

```bash
pip install flask flask-cors
```

示例代码：

```python
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)

CORS(
    app,
    origins=[
        "https://workstation.example.com",
        "http://localhost:3000",
    ],
    methods=["POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


@app.post("/api/workstation-login")
def workstation_login():
    data = request.get_json() or {}
    user = data.get("user", {})

    # user["name"] / user["openId"] 就是 WorkStation 传来的用户信息
    print("来自 WorkStation 的用户：", user)

    return jsonify({
        "redirectUrl": "https://sample-system.example.com/dashboard"
    })
```

本地启动：

```bash
flask --app app run --port 8000
```

然后在 WorkStation 新增应用时填写：

```text
http://127.0.0.1:8000/api/workstation-login
```

## Node.js Express 接入示例

安装依赖：

```bash
npm install express cors
```

示例代码：

```js
const express = require("express");
const cors = require("cors");

const app = express();

app.use(express.json());
app.use(
  cors({
    origin: ["https://workstation.example.com", "http://localhost:3000"],
    methods: ["POST", "OPTIONS"],
    allowedHeaders: ["Content-Type"]
  })
);

app.post("/api/workstation-login", (req, res) => {
  const { appId, appName, portal, user } = req.body;

  console.log("来自 WorkStation 的用户：", user);

  res.json({
    redirectUrl: "https://sample-system.example.com/dashboard"
  });
});

app.listen(8000, () => {
  console.log("sample system listening on http://127.0.0.1:8000");
});
```

然后在 WorkStation 新增应用时填写：

```text
http://127.0.0.1:8000/api/workstation-login
```

## 常见问题

### 点击应用后提示 Failed to fetch

通常是目标系统没有配置跨域，或者接口地址不可访问。

检查目标系统是否允许：

```text
Access-Control-Allow-Origin: http://localhost:3000
```

正式环境则允许：

```text
Access-Control-Allow-Origin: https://workstation.example.com
```

### 点击应用后提示目标系统未返回 redirectUrl

目标接口必须返回 JSON：

```json
{
  "redirectUrl": "https://sample-system.example.com/dashboard"
}
```

不能只返回字符串，也不能返回 HTML。

### 应用 URL 应该填页面地址还是接口地址

填接口地址。

正确示例：

```text
https://sample-system.example.com/api/workstation-login
```

不推荐直接填：

```text
https://sample-system.example.com/dashboard
```

因为 WorkStation 需要先把用户信息 POST 给目标系统，再根据目标系统返回的 `redirectUrl` 打开页面。
