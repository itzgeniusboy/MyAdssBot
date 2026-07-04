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

    # Get Bot Username dynamically to build deep linking 'Add to Channel' URLs!
    bot_username = "bot"
    try:
        me_res = session.get(f"https://api.telegram.org/bot{bot_token}/getMe", timeout=10).json()
        if me_res.get("ok"):
            bot_username = me_res["result"].get("username", "bot")
            print(f"Fetched Bot details successfully. Username: @{bot_username}", flush=True)
    except Exception as e:
        print(f"Could not fetch bot details: {e}", flush=True)

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

        # 1. Long-polling for private messages & admin addition updates
        try:
            params = {
                "limit": 100,
                "allowed_updates": json.dumps(["message", "my_chat_member"]),
                "timeout": 5
            }
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
                        
                        # --- Check for Channel Member Addition Updates (Added as Admin) ---
                        my_chat_member = update.get("my_chat_member")
                        if my_chat_member:
                            chat = my_chat_member.get("chat", {})
                            chat_id_channel = chat.get("id")
                            chat_title = chat.get("title", "Channel")
                            chat_type = chat.get("type")
                            
                            new_chat_member = my_chat_member.get("new_chat_member", {})
                            status = new_chat_member.get("status")
                            
                            if chat_type in ["channel", "supergroup"]:
                                # Reload state to keep it fresh
                                state_data = load_json_file(DEFAULT_STATE_FILE, {})
                                if "active_channels" not in state_data or not isinstance(state_data["active_channels"], list):
                                    state_data["active_channels"] = [chat_id]
                                    
                                if status == "administrator":
                                    # Bot is now added as admin to this channel!
                                    if chat_id_channel not in state_data["active_channels"] and str(chat_id_channel) not in state_data["active_channels"]:
                                        state_data["active_channels"].append(chat_id_channel)
                                        print(f"🎉 Bot successfully added as Admin to: {chat_title} (ID: {chat_id_channel})", flush=True)
                                        
                                        # Send a cheerful confirmation message directly to the new channel!
                                        try:
                                            welcome_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                                            welcome_text = (
                                                f"🚀 <b>Ad Posting Bot Active!</b>\n\n"
                                                f"Aapne is bot ko successfully admin banaya hai. Ab is channel par automatic scheduled ads post hona shuru ho jayenge! ✨\n\n"
                                                f"📢 <b>Status:</b> Active & Running 24x7!"
                                            )
                                            session.post(welcome_url, json={"chat_id": chat_id_channel, "text": welcome_text, "parse_mode": "HTML"}, timeout=10)
                                        except Exception as ex:
                                            print(f"Could not send welcome message to channel: {ex}", flush=True)
                                        
                                        save_json_file(DEFAULT_STATE_FILE, state_data)
                                elif status in ["left", "kicked", "member"]:
                                    # Bot was removed or demoted from admin
                                    active_channels = state_data.get("active_channels", [])
                                    if chat_id_channel in active_channels:
                                        active_channels.remove(chat_id_channel)
                                    if str(chat_id_channel) in active_channels:
                                        active_channels.remove(str(chat_id_channel))
                                    state_data["active_channels"] = active_channels
                                    print(f"⚠️ Bot removed or demoted from: {chat_title} (ID: {chat_id_channel})", flush=True)
                                    save_json_file(DEFAULT_STATE_FILE, state_data)

                        # --- Check for User direct/private Messages ---
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
                                f"👋 <b>Hello {first_name}! Welcome to Telegram Ad Poster Bot!</b> 🌟\n\n"
                                f"Aapka automated scheduled ad poster system fully active aur 24x7 running hai! ✨\n\n"
                                f"📢 <b>How to Run Ads on Your Channel:</b>\n"
                                f"1️⃣ Niche diye gaye <b>\"Add Me to Your Channel\"</b> button par click karein.\n"
                                f"2️⃣ Apna desired channel select karein aur bot ko add karein.\n"
                                f"3️⃣ Bot ko <b>Admin permissions</b> (Post, Edit, and Delete Messages) dein.\n"
                                f"4️⃣ Bus! Bot automatically scheduled intervals par configured ads post karna shuru kar dega.\n\n"
                                f"💻 <b>System Status:</b> Online 🟢\n"
                                f"⏰ <b>Uptime Cycle:</b> Continuous loops via GitHub Actions."
                            )
                            
                            # Build the 'Add to Channel' direct deep link button with admin permissions!
                            add_to_channel_url = f"https://t.me/{bot_username}?startchannel=true&admin=post_messages+edit_messages+delete_messages+invite_users"
                            
                            reply_markup = {
                                "inline_keyboard": [
                                    [
                                        {"text": "🚀 Add Me to Your Channel (Run Ads)", "url": add_to_channel_url}
                                    ]
                                ]
                            }
                            
                            payload = {
                                "chat_id": chat_id_private,
                                "text": reply_text,
                                "parse_mode": "HTML",
                                "reply_markup": json.dumps(reply_markup)
                            }
                            session.post(url_send_message, json=payload, timeout=10)
        except Exception as e:
            print(f"Error checking Telegram updates: {e}", flush=True)

        # 2. Check scheduled ads - only check every 60 seconds to avoid wasting disk resources
        if (current_time - last_ad_check_time) >= 60 or last_ad_check_time == 0:
            should_log_ad_status = (current_time - last_ad_check_time) >= 600 or last_ad_check_time == 0
            last_ad_check_time = current_time
            
            config_data = load_json_file(DEFAULT_CONFIG_FILE, [])
            state_data = load_json_file(DEFAULT_STATE_FILE, {})

            # Initialize active channels list if not present
            if "active_channels" not in state_data or not isinstance(state_data["active_channels"], list):
                state_data["active_channels"] = [chat_id]
                save_json_file(DEFAULT_STATE_FILE, state_data)

            active_channels = state_data["active_channels"]
            # Ensure the configured default channel is in the active list
            if chat_id not in active_channels and str(chat_id) not in active_channels:
                active_channels.insert(0, chat_id)

            if "channel_states" not in state_data or not isinstance(state_data["channel_states"], dict):
                state_data["channel_states"] = {}

            state_updated = False

            if config_data and active_channels:
                if should_log_ad_status:
                    print(f"Checking scheduled ads for {len(active_channels)} channels...", flush=True)

                for active_chan in active_channels:
                    chan_str = str(active_chan)
                    if chan_str not in state_data["channel_states"]:
                        state_data["channel_states"][chan_str] = {}

                    chan_state = state_data["channel_states"][chan_str]

                    for ad in config_data:
                        ad_id = str(ad.get("id"))
                        interval_minutes = ad.get("interval_minutes", 120)
                        
                        # Fallback to general timestamp if channel state is not populated
                        last_posted = chan_state.get(ad_id, state_data.get(ad_id, 0))
                        ad_elapsed_minutes = (time.time() - last_posted) / 60.0

                        if should_log_ad_status:
                            print(f" - Channel {active_chan} | Ad '{ad_id}': Interval: {interval_minutes}m, Last posted: {time.strftime('%M:%S', time.localtime(last_posted)) if last_posted else 'Never'}, Elapsed: {ad_elapsed_minutes:.1f}m", flush=True)

                        if ad_elapsed_minutes >= interval_minutes:
                            # Try posting to this specific channel
                            success = post_ad_to_telegram(bot_token, active_chan, ad)
                            if success:
                                chan_state[ad_id] = time.time()
                                state_data["channel_states"][chan_str] = chan_state
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
