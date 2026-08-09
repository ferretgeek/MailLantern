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

## 升级、备份与恢复

应用不建立邮箱数据库：iCloud 地址、应用专用密码、邮件和验证码只在单次请求内处理；浏览器只保存主题。因此无需备份业务数据。只需通过加密的基础设施流程保留 systemd/Compose、反向代理和秘密配置，且不要把秘密复制进源码归档。

升级时保留旧源码或镜像，在另一回环端口运行测试和 `/health`，再用演示模式及专门的低风险测试邮箱验证一次；随后切换服务。回滚恢复旧源码/镜像和成对的旧配置。若访问令牌或 iCloud 应用专用密码曾暴露，应在 Apple/部署侧撤销并重新生成，恢复旧文件不能消除泄露。

## 卸载与故障排查

- 停止/禁用 systemd 服务或运行 `docker compose down`，再删除虚拟环境或镜像；从秘密存储移除访问令牌。
- 清除浏览器站点数据只会删除主题；应用没有可恢复的本地邮箱历史。
- `401`：重新输入访问令牌；页面刻意不保存它。
- Host/Origin 拒绝：核对精确白名单和代理转发的 Host，不要关闭校验。
- IMAP 登录失败：确认使用 iCloud 应用专用密码、账号状态和 TCP 993；不要在日志中打印凭据。
- 查不到验证码：确认时间范围、目标邮箱与所选文件夹；解析是启发式结果，应人工确认。
- 远程故障先通过 SSH 隧道复现；不要以公开绑定或关闭 HTTPS/认证作为排错手段。
