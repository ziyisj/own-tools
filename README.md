# AdsPower 自动打开 ChatGPT

这个脚本会通过 AdsPower Local API：

1. 新建一个浏览器环境
2. 从 `proxies.txt` 随机选择一个 SOCKS5 代理
3. 打开浏览器
4. 访问 `https://www.chatgpt.com`

## 使用

先确保 AdsPower 已打开，并且 Local API 可用。

网页控制台：

```bash
ADSPOWER_API_KEY="你的API密钥" python3 adspower_web.py
```

窗口版：

```bash
python3 adspower_gui.py
```

窗口版支持：

- 导入 TXT/CSV 邮箱列表
- 按选中邮箱或全部邮箱创建环境
- 创建多个空环境
- 查看环境列表
- 批量打开选中环境或全部环境
- 删除选中环境

邮箱只会写入环境名称和备注，用于人工管理；脚本不会自动填写 ChatGPT 注册页面。

命令行版：

```bash
python3 adspower_open_chatgpt.py
```

可选参数：

```bash
python3 adspower_open_chatgpt.py --group-id 0 --name "ChatGPT Auto" --url https://www.chatgpt.com
```

如果 AdsPower 开启了 API 安全校验：

```bash
ADSPOWER_API_KEY="你的API密钥" python3 adspower_open_chatgpt.py
```

API Key 一般在 AdsPower 的 `设置` / `Local API` / `安全校验` 相关位置查看或复制。

如果你的 AdsPower Local API 不是默认端口：

```bash
ADSPOWER_BASE_URL="http://localhost:50325" python3 adspower_open_chatgpt.py
```

## 说明

`proxies.txt` 每行格式：

```text
host:port:username:password
```

如果 `proxies.txt` 不存在，脚本会回退到 AdsPower 已保存代理的随机模式：`proxyid=random`。

## 在线更新

先把项目绑定到 GitHub 仓库：

```bash
git remote add origin git@github.com:你的用户名/你的仓库.git
git add README.md adspower_open_chatgpt.py adspower_web.py update_project.py .gitignore
git commit -m "Initial AdsPower automation console"
git push -u origin main
```

之后更新代码只需要推送到 GitHub，本机可在网页控制台点 `在线更新`，或运行：

```bash
python3 update_project.py
```

## Windows 应用

推送到 GitHub 后，仓库里的 GitHub Actions 会自动构建 Windows 版本：

1. 打开 GitHub 仓库的 `Actions`
2. 进入 `Build Windows App`
3. 下载 `AdsPowerConsole-Windows` artifact
4. 解压后运行 `start.bat`

也可以在 Windows 本地构建：

```bat
build_windows.bat
```

构建完成后 exe 在：

```text
dist\AdsPowerConsole.exe
```

Windows 运行时的敏感文件仍然只保存在本地目录：

```text
proxies.txt
mail_accounts.json
completed_accounts.txt
completed_profiles.json
```
