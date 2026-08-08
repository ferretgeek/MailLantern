# 部署教程

## 方案一：本机运行（推荐）

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install .
.\.venv\Scripts\mail-lantern.exe
```

终端会显示 `http://127.0.0.1:8769/#token=...`。打开后，令牌会从地址栏移除且不会写入浏览器存储。停止服务请在终端按 `Ctrl+C`。

演示模式：

```powershell
.\.venv\Scripts\mail-lantern.exe --demo
```

## 方案二：服务器 + SSH 隧道（最小暴露面）

服务器上安装后保持默认回环监听，并设置自己的随机令牌：

```bash
python3 -m venv /opt/mail-lantern/.venv
/opt/mail-lantern/.venv/bin/pip install /opt/mail-lantern
export LANTERN_ACCESS_TOKEN="$(/opt/mail-lantern/.venv/bin/mail-lantern token)"
/opt/mail-lantern/.venv/bin/mail-lantern
```

本机建立隧道：

```bash
ssh -N -L 8769:127.0.0.1:8769 user@example.invalid
```

然后访问 `http://127.0.0.1:8769/`，输入服务器终端生成的令牌。示例域名是保留值，请替换为自己的服务器。

## 方案三：Docker Compose

创建不提交到 Git 的 `.env`：

```dotenv
LANTERN_ACCESS_TOKEN=replace-with-at-least-24-random-characters
LANTERN_ALLOWED_HOSTS=localhost,127.0.0.1
```

```bash
docker compose up -d --build
docker compose ps
```

Compose 默认只映射到宿主机 `127.0.0.1:8769`，容器只读、移除 Linux capabilities，并禁止提权。应用需要向外连接 Apple IMAP 的 TCP 993 端口。

## HTTPS 反向代理

应用继续监听 `127.0.0.1:8769`。生成强令牌并配置真实域名：

```dotenv
LANTERN_BIND_HOST=127.0.0.1
LANTERN_PORT=8769
LANTERN_ACCESS_TOKEN=replace-with-a-random-secret
LANTERN_ALLOWED_HOSTS=lantern.example.invalid
```

参考 [`deploy/nginx.conf.example`](../deploy/nginx.conf.example) 与 [`deploy/mail-lantern.service`](../deploy/mail-lantern.service)。把 `.invalid` 示例域名、证书路径、用户和安装路径替换为自己的值。

## 环境变量

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `LANTERN_BIND_HOST` | `127.0.0.1` | 监听地址 |
| `LANTERN_PORT` | `8769` | 监听端口 |
| `LANTERN_ACCESS_TOKEN` | 本机临时生成 | 至少 24 字符；非回环部署必须显式设置 |
| `LANTERN_ALLOWED_HOSTS` | 本机安全值 | 逗号分隔的精确浏览器主机名 |
| `LANTERN_DEMO` | `0` | 设为 `1` 时只返回虚构数据 |
| `LANTERN_ALLOW_PRIVATE_HTTP` | `0` | 仅隔离私网直连时显式启用；公网仍必须 HTTPS |

## 上线核验

```bash
curl -fsS http://127.0.0.1:8769/health
```

同时确认：公网只能到达 HTTPS；HTTP 重定向到 HTTPS；代理不记录请求体或 Authorization；Host 白名单精确；访问令牌独立且足够随机；服务账户无管理员权限；主机出站只需 DNS、系统更新和 Apple IMAP 993。
