#!/usr/bin/env python3
"""
post_ads.py - Main script for Telegram Ad Posting Bot.
Runs via GitHub Actions cron or manual dispatch.
"""

import os
import sys
import json
import time
import requests

# Default Configuration
DEFAULT_CONFIG_FILE = "ads_config.json"
DEFAULT_STATE_FILE = "state.json"

def load_json_file(file_path, default_value):
    if not os.path.exists(file_path):
        return default_value
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return default_value

def save_json_file(file_path, data):
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving {file_path}: {e}")
        return False

def post_ad_to_telegram(bot_token, chat_id, ad):
    """
    Posts a single ad to Telegram using the appropriate endpoint.
    Supports photo and animation (GIF) types.
    """
    media_type = ad.get("media_type", "photo")
    file_id = ad.get("file_id")
    caption = ad.get("caption", "")
    button_text = ad.get("button_text")
    button_url = ad.get("button_url")

    if not file_id:
        print(f"Error: No file_id specified for ad {ad.get('id')}")
        return False

    # Construct the inline keyboard
    reply_markup = {}
    if button_text and button_url:
        reply_markup = {
            "inline_keyboard": [
                [
                    {"text": button_text, "url": button_url}
                ]
            ]
        }

    # Decide API Endpoint
    if media_type == "animation":
        url = f"https://api.telegram.org/bot{bot_token}/sendAnimation"
        payload = {
            "chat_id": chat_id,
            "animation": file_id,
            "caption": caption,
            "parse_mode": "HTML",
            "reply_markup": json.dumps(reply_markup) if reply_markup else None
        }
    else: # Default to photo
        url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
        payload = {
            "chat_id": chat_id,
            "photo": file_id,
            "caption": caption,
            "parse_mode": "HTML",
            "reply_markup": json.dumps(reply_markup) if reply_markup else None
        }

    print(f"Posting ad {ad.get('id')} ({media_type}) to {chat_id}...")
    try:
        response = requests.post(url, data=payload, timeout=15)
        res_json = response.json()
        if response.status_code == 200 and res_json.get("ok"):
            print(f"Successfully posted ad {ad.get('id')}!")
            return True
        else:
            print(f"Failed to post ad {ad.get('id')}. Telegram Response: {res_json}")
            return False
    except Exception as e:
        print(f"Exception while posting ad {ad.get('id')}: {e}")
        return False

def main():
    # 1. Retrieve bot token and channel ID from Environment
    bot_token = os.environ.get("BOT_TOKEN")
    chat_id = os.environ.get("CHANNEL_ID")

    # Run duration in minutes (defaults to 350 minutes / 5 hours 50 mins as requested)
    run_duration_min = float(os.environ.get("RUN_DURATION_MINUTES", "350"))

    # Hardcoded Fallbacks (for testing or if not provided in Action)
    if not bot_token:
        bot_token = "8918032442:AAG3p2wJ3Bm8ibtNCCs_4B8momgk8GAEGkA"
    if not chat_id:
        chat_id = "@FeaturesticLeaks"

    if not bot_token or bot_token.startswith("YOUR_") or not chat_id:
        print("Error: Telegram BOT_TOKEN and CHANNEL_ID must be configured.")
        sys.exit(1)

    print(f"Ad Posting Run Started at {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Target Channel: {chat_id}")
    print(f"Loop duration limit set to {run_duration_min} minutes.")

    # Enable unbuffered output to see logs in real-time
    sys.stdout.reconfigure(line_buffering=True) if hasattr(sys.stdout, 'reconfigure') else None

    start_time = time.time()
    last_update_id = None
    last_ad_check_time = 0  # Force first-time check immediately

    # Create a persistent session to keep the TCP connection alive (extremely fast replies!)
    session = requests.Session()

    # Initialize Telegram update offset to only reply to NEW messages
    try:
        init_res = session.get(f"https://api.telegram.org/bot{bot_token}/getUpdates", params={"limit": 1}, timeout=10).json()
        if init_res.get("ok") and init_res.get("result"):
            last_update_id = init_res["result"][-1]["update_id"]
            print(f"Initialized update offset to {last_update_id + 1} to ignore previous messages.", flush=True)
    except Exception as e:
        print(f"Could not initialize update offset: {e}", flush=True)

    # Main continuous polling loop
    while True:
        current_time = time.time()
        elapsed_minutes = (current_time - start_time) / 60.0

        if elapsed_minutes >= run_duration_min:
            print(f"Reached configured run duration of {run_duration_min:.1f} minutes. Exiting gracefully to allow workflow restart...", flush=True)
            break

        had_updates = False

        # 1. Long-polling for private messages (Instant reply system)
        try:
            # Shortened timeout to 5 seconds to remain highly responsive and avoid blocking other events
            params = {"limit": 100, "allowed_updates": ["message"], "timeout": 5}
            if last_update_id is not None:
                params["offset"] = last_update_id + 1

            url_get_updates = f"https://api.telegram.org/bot{bot_token}/getUpdates"
            response = session.get(url_get_updates, params=params, timeout=10)
            if response.status_code == 200:
                res_json = response.json()
                if res_json.get("ok"):
                    updates = res_json.get("result", [])
                    if updates:
                        had_updates = True
                    for update in updates:
                        last_update_id = update.get("update_id")
                        message = update.get("message")
                        if not message:
                            continue
                        
                        chat = message.get("chat", {})
                        chat_id_private = chat.get("id")
                        chat_type = chat.get("type")
                        text = message.get("text", "")
                        sender = message.get("from", {})
                        first_name = sender.get("first_name", "User")

                        if chat_type == "private" and chat_id_private:
                            print(f"Received direct message from {first_name} (Chat ID: {chat_id_private}): {text}", flush=True)
                            url_send_message = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                            
                            reply_text = (
                                f"👋 <b>Namaste {first_name}! Aapka Ad Posting Bot Bilkul Active Hai!</b> 🚀\n\n"
                                f"Mujhe aapka message mila: <i>\"{text}\"</i>\n\n"
                                f"📢 <b>Target Channel:</b> {chat_id}\n"
                                f"⏰ <b>Uptime:</b> Active run: {elapsed_minutes:.1f} mins (Total cycle: {run_duration_min:.0f} mins).\n"
                                f"💻 <b>Status:</b> GitHub Actions par background continuous run bilkul live aur 24x7 active hai!\n\n"
                                f"Bot completely automatic chal rha hai aur har cycle end hone par safety restart hota hai! ✨"
                            )
                            
                            payload = {
                                "chat_id": chat_id_private,
                                "text": reply_text,
                                "parse_mode": "HTML"
                            }
                            # Send message using persistent session
                            session.post(url_send_message, json=payload, timeout=10)
        except Exception as e:
            print(f"Error checking Telegram updates: {e}", flush=True)

        # 2. Check scheduled ads - only check every 60 seconds to avoid wasting disk resources
        if (current_time - last_ad_check_time) >= 60 or last_ad_check_time == 0:
            should_log_ad_status = (current_time - last_ad_check_time) >= 600 or last_ad_check_time == 0
            last_ad_check_time = current_time
            
            config_data = load_json_file(DEFAULT_CONFIG_FILE, [])
            state_data = load_json_file(DEFAULT_STATE_FILE, {})

            if config_data:
                state_updated = False
                if should_log_ad_status:
                    print(f"Checking scheduled ads... (Next log in 10 mins or on post)", flush=True)

                for ad in config_data:
                    ad_id = str(ad.get("id"))
                    interval_minutes = ad.get("interval_minutes", 120)
                    
                    last_posted = state_data.get(ad_id, 0)
                    ad_elapsed_minutes = (time.time() - last_posted) / 60.0

                    if should_log_ad_status:
                        print(f" - Ad '{ad_id}': Interval: {interval_minutes}m, Last posted: {time.strftime('%M:%S', time.localtime(last_posted)) if last_posted else 'Never'}, Elapsed: {ad_elapsed_minutes:.1f}m", flush=True)

                    if ad_elapsed_minutes >= interval_minutes:
                        # Try posting using persistent session helper if available, or fall back
                        success = post_ad_to_telegram(bot_token, chat_id, ad)
                        if success:
                            state_data[ad_id] = time.time()
                            state_updated = True
                            # Force immediate refresh of logging status next check
                            last_ad_check_time = 0
                
                if state_updated:
                    print("Saving updated state back to state.json...", flush=True)
                    save_json_file(DEFAULT_STATE_FILE, state_data)

        # 3. Dynamic polling sleep:
        # If we had updates, process next updates IMMEDIATELY without sleep (0 seconds)
        # If no updates, rest for 1 second to keep CPU low and prevent rate limiting
        if not had_updates:
            time.sleep(1)

    print("Ad Posting Run Completed.")

if __name__ == "__main__":
    main()
