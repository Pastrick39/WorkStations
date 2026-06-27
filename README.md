# WorkStation 企业中控平台

这是一个可放入飞书企业自建应用的中控入口页。用户从飞书点击应用进入页面后，页面会通过飞书 OAuth 自动获取当前飞书用户名称，并在右上角展示。

## 本地运行

```bash
npm start
```

默认访问：

```text
http://localhost:3000
```

## 飞书应用配置

在运行服务前配置环境变量：

```bash
FEISHU_APP_ID=cli_xxx
FEISHU_APP_SECRET=xxx
APP_BASE_URL=https://你的域名
PORT=3000
```

`APP_BASE_URL` 必须是飞书用户能访问到的公网 HTTPS 地址，例如：

```text
https://workstation.example.com
```

然后在飞书开放平台的企业自建应用中配置：

- 网页应用地址：`https://workstation.example.com`
- 重定向 URL：`https://workstation.example.com/`
- 权限：按飞书后台要求开通获取登录用户信息相关权限

## 新增系统入口

打开页面后，点击左侧各端口旁边的 `+`，输入：

- 应用名称
- 跳转 URL

保存后会在对应端口生成应用卡片。点击卡片即可跳转到对应系统。

当前版本应用入口保存在浏览器 `localStorage` 中，适合先做内部原型。如果需要多人共享同一份应用配置，后续需要接数据库或配置接口。
