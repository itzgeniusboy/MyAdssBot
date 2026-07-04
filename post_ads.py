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

def reply_to_private_messages(bot_token, channel_id):
    """
    Fetches pending updates and replies to users sending direct / private messages.
    This provides immediate feedback that the bot is running successfully in the background!
    """
    print("Checking for pending private user messages...")
    url_get_updates = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    try:
        response = requests.get(url_get_updates, params={"limit": 100, "allowed_updates": ["message"]}, timeout=10)
        if response.status_code != 200:
            return
        res_json = response.json()
        if not res_json.get("ok"):
            return
        
        updates = res_json.get("result", [])
        if not updates:
            print("No pending user messages to reply to.")
            return

        last_update_id = None
        for update in updates:
            update_id = update.get("update_id")
            last_update_id = update_id
            
            message = update.get("message")
            if not message:
                continue
                
            chat = message.get("chat", {})
            chat_id = chat.get("id")
            chat_type = chat.get("type")
            text = message.get("text", "")
            sender = message.get("from", {})
            first_name = sender.get("first_name", "User")

            # We only reply to private chats (direct messages to bot)
            if chat_type == "private" and chat_id:
                print(f"Replying to direct message from {first_name} (Chat ID: {chat_id})...")
                url_send_message = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                
                reply_text = (
                    f"👋 <b>Namaste {first_name}! Aapka Ad Posting Bot Bilkul Chalu Hai!</b> 🚀\n\n"
                    f"Mujhe aapka message mila: <i>\"{text}\"</i>\n\n"
                    f"📢 <b>Target Channel:</b> {channel_id}\n"
                    f"⏰ <b>Schedule Check:</b> Har 10 mins me GitHub Actions automatically check karta hai.\n"
                    f"💻 <b>Status:</b> GitHub Actions par background run bilkul active aur 24x7 running hai!\n\n"
                    f"Aap run details aur logs dekhne ke liye apne GitHub Repository ke <b>Actions</b> tab par ja sakte hain! ✨"
                )
                
                payload = {
                    "chat_id": chat_id,
                    "text": reply_text,
                    "parse_mode": "HTML"
                }
                requests.post(url_send_message, json=payload, timeout=10)

        # Confirm/Clear updates so they are not processed in the next run
        if last_update_id is not None:
            requests.get(url_get_updates, params={"offset": last_update_id + 1}, timeout=5)
            print("Successfully cleared processed Telegram updates.")

    except Exception as e:
        print(f"Error handling private replies: {e}")

def main():
    # 1. Retrieve bot token and channel ID from Environment
    bot_token = os.environ.get("BOT_TOKEN")
    chat_id = os.environ.get("CHANNEL_ID")

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

    # Process direct messages sent to the bot (instant reply proof of life!)
    reply_to_private_messages(bot_token, chat_id)

    # 2. Load configurations and current state
    config_data = load_json_file(DEFAULT_CONFIG_FILE, [])
    state_data = load_json_file(DEFAULT_STATE_FILE, {})

    if not config_data:
        print("No ads configured in ads_config.json. Exiting.")
        return

    print(f"Loaded {len(config_data)} ads from configuration.")
    
    current_time = time.time()
    state_updated = False

    # 3. Process each ad
    for ad in config_data:
        ad_id = str(ad.get("id"))
        interval_minutes = ad.get("interval_minutes", 120) # Default to 2 hours if not specified
        
        # Determine last post time
        last_posted = state_data.get(ad_id, 0)
        elapsed_minutes = (current_time - last_posted) / 60.0

        print(f"Ad '{ad_id}': Last posted: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(last_posted)) if last_posted else 'Never'}, Elapsed: {elapsed_minutes:.1f} min, Interval: {interval_minutes} min")

        if elapsed_minutes >= interval_minutes:
            # Try posting
            success = post_ad_to_telegram(bot_token, chat_id, ad)
            if success:
                # Update state timestamp
                state_data[ad_id] = current_time
                state_updated = True
        else:
            minutes_left = interval_minutes - elapsed_minutes
            print(f"Ad '{ad_id}' skipped. {minutes_left:.1f} minutes remaining before next post.")

    # 4. Save state if any ads were successfully posted
    if state_updated:
        print("Saving updated state back to state.json...")
        save_json_file(DEFAULT_STATE_FILE, state_data)
    else:
        print("No updates to state.json.")

    print("Ad Posting Run Completed.")

if __name__ == "__main__":
    main()
