# beancount_bot

适用于 Beancount 记账的 Telegram 机器人

![GitHub](https://img.shields.io/github/license/kaaass/beancount_bot)
![GitHub tag (latest by date)](https://img.shields.io/github/v/tag/kaaass/beancount_bot?color=green&label=version)
![PyPI](https://img.shields.io/pypi/v/beancount_bot)
[![Test and Lint](https://github.com/kaaass/beancount_bot/actions/workflows/test-with-lint.yml/badge.svg?branch=master)](https://github.com/kaaass/beancount_bot/actions/workflows/test-with-lint.yml)

## Features

- 支持简易鉴权
- 支持交易创建、撤回
- 内建自由且强大的模板语法，适用于各种记账需求
- 允许通过插件扩展记账语法
- 支持定时任务
- 支持多个用户同时记账，设置不同的标签

## 安装

### 通过 Pip (Pypi)

```shell
pip install python-telegram-bot==21.4
pip install "python-telegram-bot[job-queue]"
pip install beancount_bot  #通过该方法下载到原始的代码，再替换成本仓库对应的修改过的文件（bot.py main.py session_config.py task.py util.py）

```

另外还要修改`/usr/local/bin/beancount_bot` 文件
```shell
#from beancount_bot import main #这是原来的条目
from beancount_bot.main import main  #修改为这个条目

```

然后去到包含`beancount_bot.yml`、  `bot.session`、  `costflow.json`、  `template.yml`的目录运行beancount_bot即可。

最后配置一个新增一个 `/etc/systemd/system/beancount_bot.service`

```
[Unit]
Description=Beancount Bot Service
After=network.target

[Service]
Type=simple
WorkingDirectory=/data/bean/config/
ExecStart=/usr/local/bin/beancount_bot


Restart=always
RestartSec=10

Environment="PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games:/snap/bin:/install/nodejs/node-v22.9.0/bin"
#如果 NodeJS 没有配置到默认环境变量里面，就需要补充，可通过echo $PATH查看nodejs的环境

StandardOutput=file:/var/log/beancount/bot.log
StandardError=file:/var/log/beancount/bot.error.log


[Install]
WantedBy=multi-user.target

```
再通过配置守护进程

```shell
sudo systemctl daemon-reload
sudo systemctl start beancount_bot
sudo systemctl beancount_bot
```

### 通过 Docker

- [kaaass/beancount_bot_docker](https://github.com/kaaass/beancount_bot_docker)：beancount_bot 的 Docker 镜像
- [kaaass/beancount_bot_costflow_docker](https://github.com/kaaass/beancount_bot_costflow_docker)：包含 beancount_bot 与 Costflow 插件的 Docker 镜像

## 使用

1. 下载示例配置文件 `beancount_bot.example.yml`、`template.example.yml`
2. 修改后保存为 `beancount_bot.yml`、`template.yml`
3. 执行 `beancount_bot`

## 推荐插件

1. [kaaass/beancount_bot_costflow](https://github.com/kaaass/beancount_bot_costflow)：支持 Costflow 语法

欢迎在 Issue 推荐优秀插件。

## 插件开发

请查阅项目 Wiki。

## Roadmap

1. [x] ~~支持定时备份~~ 使用定时任务支持
2. [ ] ~~支持账单导入~~ 暂时搁置
3. [ ] i18n support
4. [ ] 完善对多人记账的支持
