# Telegram Ad Posting Bot

An automated Python script that posts scheduled media advertisements (images/GIFs) to a Telegram channel. The bot runs on an interval schedule entirely for free using GitHub Actions cron (no persistent servers required!).

## Tech Stack
* **Python 3.11**
* **requests** library (lightweight, standard HTTP request client)
* **Telegram Bot API** (`sendPhoto` and `sendAnimation` endpoints)
* **GitHub Actions** (Scheduled workflows, cron run every 10 minutes)

---

## 🚀 Setup Steps

### 1. Create your Bot via @BotFather
1. Search for `@BotFather` on Telegram and open a chat.
2. Send the `/newbot` command.
3. Choose a friendly name for your bot and a unique username ending in `bot` (e.g., `FeaturesticAdBot`).
4. Copy the long HTTP API token provided (e.g., `8918032442:AAG3p2wJ3Bm8ibtNCCs_4B8momgk8GAEGkA`). This is your `TELEGRAM_BOT_TOKEN`.

### 2. Add the Bot as an Admin to your Channel
1. Go to your target Telegram Channel (e.g., `@FeaturesticLeaks`).
2. Open **Channel Info** &gt; **Administrators** &gt; **Add Administrator**.
3. Search for your bot's username and select it.
4. Make sure the bot has permission to **Post Messages** and save.

### 3. Send Media to the Bot to Retrieve `file_id`s
Telegram handles media by caching it on its servers and assigning a unique `file_id`. We do not upload heavy image/GIF files from our repository; instead, we refer to these cached IDs.
1. Open a direct chat with your bot on Telegram and click **Start** or send `/start`.
2. Directly upload the **Photos** or **GIFs/Animations** you wish to schedule as ads.

### 4. Run `get_file_id.py` to Scan IDs
To obtain the correct `file_id` and `media_type` values for your ads:
1. Run the helper script locally on your machine or click **Scan Bot Updates** on our web control panel:
   ```bash
   pip install requests
   python get_file_id.py
   ```
2. The script queries Telegram's `getUpdates` API and lists recent media you sent to the bot.
3. Copy the `file_id` and note its `media_type` ("photo" or "animation").

### 5. Paste File IDs into `ads_config.json`
Modify `ads_config.json` to schedule your campaigns:
```json
[
  {
    "id": "promo_ad_1",
    "media_type": "photo",
    "file_id": "PASTE_EXTRACTED_PHOTO_FILE_ID_HERE",
    "caption": "<b>🔥 Joint the ultimate channel! 🔥</b>\n\nClick below to sign up.",
    "button_text": "Join Channel 🚀",
    "button_url": "https://t.me/FeaturesticLeaks",
    "interval_minutes": 60
  }
]
```

### 6. Add Repository Secrets in GitHub
Push these files to your GitHub repository, then configure your environment secrets:
1. On GitHub, navigate to your repository's **Settings** &gt; **Secrets and variables** &gt; **Actions**.
2. Click **New repository secret** and add the following:
   * **TELEGRAM_BOT_TOKEN**: Paste the token received from @BotFather.
   * **TELEGRAM_CHANNEL_ID**: Paste your target channel username (e.g. `@FeaturesticLeaks`) or numeric ID.

---

## 🛠️ How it Works under the Hood

1. **GitHub Actions Schedule**: Every 10 minutes, the `.github/workflows/ad-bot.yml` workflow triggers automatically.
2. **Interval Check**: It runs `post_ads.py` which loads your campaigns from `ads_config.json` and compares the current timestamp against the last-posted timestamp saved in `state.json`.
3. **Telegram Post**: If the elapsed duration since the last run is greater than or equal to the ad's configured `interval_minutes`, the script:
   * Calls Telegram's `sendPhoto` or `sendAnimation` API.
   * Compiles the custom Inline keyboard (Join Channel button).
   * Parses text formatting using clean HTML style.
4. **State Commit**: Once posted, `post_ads.py` updates the timestamp for that campaign ID in `state.json`. GitHub Actions automatically commits this modified `state.json` file back to the repository so the next cron run knows the exact scheduling time!
