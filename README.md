# 校园搭把手 · 开源源码

校园顺路互助与公益平台原型。简笔画猫 IP、喵币视觉、七校区切换；首页左侧是“校园小事”与发布/接单入口，右侧是公益海报。最新管理后台一并包含。

## 你要的三个文件

- `public/index.html`：网页结构。
- `public/styles.css`：基础样式。
- `public/app.js`：页面与业务交互。

请保留同目录 `cat-theme.css`、`brand.js`、`community.js`、`assets/` 以及管理页文件，这些也是当前网站实际依赖。不能只拿走三个文件就完整运行。前端全部使用原生 HTML/CSS/JavaScript，可直接编辑，无 npm 构建步骤。

## 本地运行

需要 Python 3.10 或更新版本，无第三方 Python 依赖。

```sh
python3 server.py
```

打开 http://127.0.0.1:8787/ 。Mac/Linux 可双击 `启动网站.command`，Windows 双击 `启动网站.bat`。端口占用时，Mac/Linux 用 `PORT=8790 python3 server.py`；Windows PowerShell 用 `$env:PORT=8790; python server.py`。

不要直接双击 index.html 或仅使用静态托管：任务与公益功能需要包内 Python API。SQLite 空库会在首次启动时自动创建；本包没有携带原作者数据库、邀请码关系或管理密码。

## 管理账号

打开 http://127.0.0.1:8787/admin.html 。账号 `admin`，密码首次运行随机生成，保存在根目录 `.admin-account.json`。启动后在本机查看该文件，勿上传 GitHub。没有通用默认密码。管理页面为密码保护的只读总览，可查看订单、帮带、用户身份、公益意向、社团申请、邀请关系；重启会清空已登录会话。

## 目录

```text
public/
  index.html       # 主页面
  styles.css       # 基础样式
  app.js           # 主交互
  cat-theme.css    # 猫咪主题和首页左右布局
  brand.js         # 猫咪组件
  community.js     # 公益交互
  admin.html       # 管理页
  admin.css
  admin.js
  assets/          # 本地 SVG 插画、图标
server.py          # HTTP 服务、任务与帮带 API
community.py       # 公益、邀请、社团 API
admin.py           # 管理登录和只读总览
LICENSE            # MIT
开发交接说明.md     # 产品约定、接口和下一步
公益与认证接入说明.md
```

## 当前实现与边界

已实现发布、接单、提交完成、确认、待接取消、分类搜索、一起带、收藏与一键再来、七校区切换、公益意向、邀请绑定及社团申请。新库为空，没有示例订单；可发布需求后在个人中心切换演示身份体验接单。

普通用户身份仍为开发演示字符串，未接真实校园认证与全业务权限。喵币为意向奖励，没有支付、充值、发币账本或兑换；公益组织为拟合作预览，意向不代表正式报名。已移除地图与导航，仅保留预设地点顺路匹配。收藏、常用需求与当前身份保存在浏览器，不随源码迁移。

此版本适合开源协作、公开演示和本地开发，不可直接作为真实交易系统公开运行。正式发布需完成用户认证、服务端鉴权、HTTPS 和账本核验。只部署到 GitHub Pages 无法运行后端。

## 部署公开演示站

本仓库包含 `render.yaml`，推送到 GitHub 后可在 [Render](https://render.com/) 选择 **New +** -> **Blueprint**，连接此仓库并创建服务。Render 会自动运行 `python3 server.py`，部署完成后提供一个 `https://...onrender.com` 网址。

免费实例适合演示：闲置后会冷启动，且 SQLite 数据不会作为长期持久化存储。不要在这个版本中录入真实身份、联系方式、交易或管理数据。用于真实校园服务前，应替换为持久化数据库，并实现服务端认证、授权、审计与隐私合规。

## 发布到 GitHub

在 GitHub 新建空仓库，解压并进入本目录，再按下面操作（将仓库地址替换为你自己的）：

```sh
git init
git add .
git commit -m "Initial campus mutual-help prototype"
git branch -M main
git remote add origin https://github.com/YOUR_NAME/YOUR_REPO.git
git push -u origin main
```

提交前用 `git status` 确认没有数据库、密码或 .env。`.gitignore` 已排除这些文件。本包只是整理好源码，没有代你创建或发布 GitHub 仓库。

## 许可证

本源码包使用 MIT License，允许修改、复用和再发布，需保留许可证。学校、社团及商家的名称不代表官方授权或合作。
