<div align="center">

<img width="100%" alt="header" src="https://capsule-render.vercel.app/api?type=waving&height=210&text=Sweet%20Drope%20Bot&fontAlign=50&fontAlignY=36&fontSize=56&desc=Daily%20Bonus%20%7C%20Ad%20Rewards%20%7C%20Channel%20Tasks%20%7C%20Social%20Claims%20%7C%20Multi-Account&descAlign=50&descAlignY=58"/>

<img alt="typing" src="https://readme-typing-svg.demolab.com?font=Inter&size=18&duration=3000&pause=650&center=true&vCenter=true&width=900&lines=Daily+Bonus+%7C+Claim+%26+Streak+Tracking;Ad+Rewards+%7C+Server+Wait+Gate+Handled;Channel+Tasks+%7C+Verified+Per+Channel;Social+Claims+%7C+Credit+Read+Per+Task;Multi-Account+%7C+Proxy+%26+Live+Countdown"/>

<p>
  <img alt="python" src="https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white"/>
  <img alt="platform" src="https://img.shields.io/badge/Platform-SweetDrope%20Miniapp-111111"/>
  <img alt="multi-account" src="https://img.shields.io/badge/Multi--Account-Supported-111111"/>
  <img alt="proxy" src="https://img.shields.io/badge/Proxy-Supported-111111"/>
  <img alt="author" src="https://img.shields.io/badge/by-Yuurisandesu-111111"/>
</p>

<p>
  <b>SweetDrope Bot</b> is a full automation bot for the SweetDrope Telegram Miniapp.<br/>
  It handles the complete daily cycle: claiming the daily bonus, collecting ad rewards, verifying channel tasks, claiming social tasks, tracking the referral state, all running automatically across multiple accounts with its own referral link per account, proxy support, and a live countdown between cycles.<br/>
  Built and distributed by <b>Yuurisandesu</b>.
</p>

</div>

---

## Table of Contents

- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Bot](#running-the-bot)
- [Features](#features)
- [File Structure](#file-structure)
- [Disclaimer](#disclaimer)

---

## Requirements

- Python `3.12+`
- Git

---

## Installation

**Clone the repository:**

```bash
git clone https://github.com/Yuurisan-N1/SweetDropebot-Miniapp.git
cd SweetDropebot-Miniapp
```

**Install dependencies:**

```bash
pip install aiohttp yuurisan
```

---

## Configuration

### 1. Accounts (data.txt)

Fill `data.txt` with Telegram WebApp `initData` for each account, one per line:

```
user=%7B%22id%22...&hash=abc123
user=%7B%22id%22...&hash=def456
```

> `initData` can be obtained from the browser DevTools when opening SweetDrope on Telegram Web.

> An optional `|address` suffix is tolerated and ignored, because no phase in this bot needs a wallet address.

### 2. Proxy (proxy.txt)

Fill `proxy.txt` with proxies, one per line (optional, leave empty to run without proxy):

```
host:port
host:port:user:pass
http://user:pass@host:port
```

Proxies are assigned to accounts by index in round-robin order.

### 3. Bot Settings (config.json)

`sleep_seconds` controls how many seconds the bot waits between cycles. If `config.json` is missing, it is created automatically with a default of `3600` seconds.

---

## Running the Bot

```bash
python bot.py
```

Press `Ctrl+C` at any time to stop the bot cleanly.

---

## Features

### Auto Daily Bonus
The check-in state is read from the account overview first, and the claim is only sent when the server reports that today is still open. The credited amount and the streak day count are logged, and an already claimed day is reported instead of being retried.

### Auto Ad Rewards
An ad slot is requested from the server, which returns a task id. The bot waits out the server wait gate, then claims the reward for that task id and logs the credited balance straight from the claim response. When the hourly allowance is used up, the phase stops for that hour instead of hammering the endpoint.

### Auto Channel Tasks
Every channel task listed by the server is verified through the verification endpoint, and the credited balance is logged per channel. Tasks that genuinely need a hand action, such as a real channel join, are reported with the server reason instead of being retried in a loop.

### Auto Social Claims
Social tasks are claimed per task id, and the balance delta is read from the claim response so only a real credit is logged. Tasks that were already claimed, or that the server refuses, are reported with the server reason.

### Auto Referral State
The referral friend count and the referral earnings are read from the account overview, and the per-account referral link is derived from the Telegram id inside each `initData`, so no link is hardcoded.

### Multi Account
All accounts in `data.txt` are processed sequentially within every cycle. Each account signs in with its own `initData`, and the balance plus the credited amount per phase are logged per account. The cycle number is tracked and logged at the start of each round.

### Proxy Support
Proxies are loaded from `proxy.txt` and assigned to accounts by position in round-robin order. Proxy credentials are masked in log output. Running without proxies is fully supported.

### Auto Countdown
After all accounts complete a cycle, the bot displays a live `HH:MM:SS` countdown until the next cycle starts.

---

## File Structure

```text
SweetDropebot-Miniapp/
├── bot.py          # Main bot, full daily cycle automation
├── config.json     # Sleep duration between cycles
├── data.txt        # Account initData, one per line
├── proxy.txt       # Proxy list, one per line (optional)
├── LICENSE         # License file
└── utils/
    └── banner.py   # Banner using yuurisan module
```

---

## Disclaimer

This tool is built for educational and technical exploration purposes. Use it wisely and at your own responsibility.

---

<div align="center">
<img width="100%" alt="footer" src="https://capsule-render.vercel.app/api?type=waving&height=120&section=footer"/>
</div>
