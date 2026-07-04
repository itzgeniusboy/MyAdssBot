#!/usr/bin/env python3
"""
post_ads.py - Main script for Telegram Ad Posting Bot.
Runs via GitHub Actions cron or manual dispatch.
Supports interactive /admin menu, step-by-step ad creation/deletion,
automatic channel deep linking, and multiple active channel tracking.
"""

import os
import sys
import json
import time
import requests

# Default Configuration Files
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
    Supports photo, animation (GIF), and text-only ad layouts.
    """
    media_type = ad.get("media_type", "text")
    file_id = ad.get("file_id")
    caption = ad.get("caption", "")
    button_text = ad.get("button_text")
    button_url = ad.get("button_url")

    # Force formatting to be Bold and Quote (blockquote) as requested:
    # "Adss se Spoiler htaao or uski jgaa Quote rakhoo"
    if caption:
        import re
        clean = caption.strip()
        while clean.startswith("<b>") and clean.endswith("</b>"):
            clean = clean[3:-4].strip()
        while clean.startswith("<strong>") and clean.endswith("</strong>"):
            clean = clean[8:-9].strip()
        
        clean = re.sub(r'</?tg-spoiler>', '', clean)
        clean = re.sub(r'<span\s+class=["\']tg-spoiler["\']>', '', clean)
        clean = re.sub(r'</?blockquote>', '', clean)
        clean = re.sub(r'</span>', '', clean)
        caption = f"<blockquote><b>{clean.strip()}</b></blockquote>"

    # Construct the inline keyboard button if specified
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
    if media_type == "animation" and file_id:
        url = f"https://api.telegram.org/bot{bot_token}/sendAnimation"
        payload = {
            "chat_id": chat_id,
            "animation": file_id,
            "caption": caption,
            "parse_mode": "HTML",
            "reply_markup": json.dumps(reply_markup) if reply_markup else None
        }
    elif media_type == "photo" and file_id:
        url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
        payload = {
            "chat_id": chat_id,
            "photo": file_id,
            "caption": caption,
            "parse_mode": "HTML",
            "reply_markup": json.dumps(reply_markup) if reply_markup else None
        }
    else:
        # Standard text-only ad
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": caption,
            "parse_mode": "HTML",
            "reply_markup": json.dumps(reply_markup) if reply_markup else None
        }

    print(f"Posting ad {ad.get('id')} ({media_type}) to {chat_id}...", flush=True)
    try:
        response = requests.post(url, data=payload, timeout=15)
        res_json = response.json()
        if response.status_code == 200 and res_json.get("ok"):
            print(f"Successfully posted ad {ad.get('id')} to {chat_id}!", flush=True)
            return True
        else:
            print(f"Failed to post ad {ad.get('id')} to {chat_id}. Response: {res_json}", flush=True)
            return False
    except Exception as e:
        print(f"Exception while posting ad {ad.get('id')} to {chat_id}: {e}", flush=True)
        return False

def show_admin_panel(session, bot_token, chat_id, num_channels, num_ads):
    """Sends or updates the admin control center menu."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    reply_text = (
        "💎 <b>Telegram Ad Poster - Admin Control Center</b> 💎\n\n"
        "Welcome to your Premium Management Dashboard. Control your ad operations, monitor stats, and configure direct channels seamlessly! 🚀\n\n"
        "⚡ <b>Quick Statistics:</b>\n"
        f"• 📢 <b>Connected Channels:</b> {num_channels}\n"
        f"• 📋 <b>Configured Ads:</b> {num_ads}\n"
        "• 🟢 <b>Status:</b> Online & Continuous Polling\n\n"
        "✨ <i>Choose an action below to start managing:</i>"
    )
    
    reply_markup = {
        "inline_keyboard": [
            [
                {"text": "➕ Create Custom Ad", "callback_data": "admin_create"},
                {"text": "📋 View & Delete Ads", "callback_data": "admin_list"}
            ],
            [
                {"text": "📢 Manage Channels", "callback_data": "admin_channels"},
                {"text": "🔄 Refresh Stats", "callback_data": "admin_refresh"}
            ],
            [
                {"text": "❌ Close Panel", "callback_data": "admin_close"}
            ]
        ]
    }
    
    payload = {
        "chat_id": chat_id,
        "text": reply_text,
        "parse_mode": "HTML",
        "reply_markup": json.dumps(reply_markup)
    }
    session.post(url, json=payload, timeout=10)

def main():
    # 1. Retrieve environment configuration
    bot_token = os.environ.get("BOT_TOKEN")
    chat_id = os.environ.get("CHANNEL_ID")

    # Run duration in minutes (defaults to 350 minutes / 5 hours 50 mins as requested)
    run_duration_min = float(os.environ.get("RUN_DURATION_MINUTES", "350"))

    # Hardcoded Fallbacks (for robust local testing and development)
    if not bot_token:
        bot_token = "8918032442:AAG3p2wJ3Bm8ibtNCCs_4B8momgk8GAEGkA"
    if not chat_id:
        chat_id = "@FeaturesticLeaks"

    if not bot_token or bot_token.startswith("YOUR_") or not chat_id:
        print("Error: Telegram BOT_TOKEN and CHANNEL_ID must be configured.")
        sys.exit(1)

    print(f"Ad Posting Run Started at {time.strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    print(f"Target Channel: {chat_id}", flush=True)
    print(f"Loop duration limit set to {run_duration_min} minutes.", flush=True)

    # Enable unbuffered output to see logs in real-time
    sys.stdout.reconfigure(line_buffering=True) if hasattr(sys.stdout, 'reconfigure') else None

    start_time = time.time()
    last_update_id = None
    last_ad_check_time = 0  # Force first-time check immediately

    # Create a persistent session to keep the TCP connection alive
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

        # 1. Long-polling for private messages, admin commands & inline button clicks
        try:
            params = {
                "limit": 100,
                "allowed_updates": json.dumps(["message", "my_chat_member", "callback_query"]),
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

                        # --- Check for Inline Keyboard Button Clicks ---
                        callback_query = update.get("callback_query")
                        if callback_query:
                            cq_id = callback_query.get("id")
                            chat_cq = callback_query.get("message", {}).get("chat", {})
                            chat_id_private = chat_cq.get("id")
                            cq_data = callback_query.get("data", "")
                            cq_from = callback_query.get("from", {})
                            first_name = cq_from.get("first_name", "User")
                            msg_id_cq = callback_query.get("message", {}).get("message_id")

                            print(f"Callback button pressed: {cq_data} by {first_name}", flush=True)

                            # Acknowledge callback immediately to remove loading spinner in Telegram
                            try:
                                session.post(f"https://api.telegram.org/bot{bot_token}/answerCallbackQuery", json={"callback_query_id": cq_id}, timeout=5)
                            except Exception:
                                pass

                            state_data = load_json_file(DEFAULT_STATE_FILE, {})
                            config_data = load_json_file(DEFAULT_CONFIG_FILE, [])

                            # Authenticate / Register Admin
                            if "admin_chat_id" not in state_data or not state_data["admin_chat_id"]:
                                state_data["admin_chat_id"] = chat_id_private
                                save_json_file(DEFAULT_STATE_FILE, state_data)

                            if state_data.get("admin_chat_id") == chat_id_private:
                                if "admin_states" not in state_data or not isinstance(state_data["admin_states"], dict):
                                    state_data["admin_states"] = {}
                                
                                user_state = state_data["admin_states"].get(str(chat_id_private), {"step": "None", "temp_ad": {}})

                                if cq_data == "admin_create":
                                    user_state["step"] = "awaiting_text"
                                    user_state["temp_ad"] = {}
                                    state_data["admin_states"][str(chat_id_private)] = user_state
                                    save_json_file(DEFAULT_STATE_FILE, state_data)
                                    
                                    # Prompt for step 1 (removed formatting advice)
                                    prompt_text = (
                                        "✍️ <b>Step 1 of 5: Enter Ad Description/Caption</b>\n\n"
                                        "Please type or paste the ad caption/description text.\n\n"
                                        "<i>Example:</i>\n"
                                        "🔥 <b>Premium Leaks & News</b>\n"
                                        "Join us for instant exclusive tech news!"
                                    )
                                    reply_markup = {
                                        "inline_keyboard": [[{"text": "❌ Cancel Process", "callback_data": "admin_cancel"}]]
                                    }
                                    session.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={
                                        "chat_id": chat_id_private,
                                        "text": prompt_text,
                                        "parse_mode": "HTML",
                                        "reply_markup": json.dumps(reply_markup)
                                    }, timeout=10)

                                elif cq_data == "admin_list":
                                    if not config_data:
                                        text_list = "📋 <b>Currently, no active ads are configured.</b>"
                                        reply_markup = {
                                            "inline_keyboard": [[{"text": "➕ Create Ad Now", "callback_data": "admin_create"}], [{"text": "⬅️ Back", "callback_data": "admin_refresh"}]]
                                        }
                                    else:
                                        text_list = "📋 <b>Your Active Configured Ads:</b>\n\n"
                                        keyboard = []
                                        import re
                                        for i, ad in enumerate(config_data):
                                            ad_id = ad.get("id", f"ad_{i}")
                                            cap_snippet = ad.get("caption", ad.get("text", ""))
                                            # Strip HTML tags to show clean preview snippet
                                            clean_snippet = re.sub(r'<[^>]+>', '', cap_snippet).strip()
                                            clean_snippet = clean_snippet[:45] + "..." if len(clean_snippet) > 45 else clean_snippet
                                            
                                            text_list += f"📌 <b>Ad ID:</b> <code>{ad_id}</code>\n"
                                            text_list += f"⏰ <b>Interval:</b> {ad.get('interval_minutes')} mins | 🎬 <b>Format:</b> {ad.get('media_type', 'text').upper()}\n"
                                            text_list += f"📝 <b>Preview:</b> <i>{clean_snippet}</i>\n\n"
                                            
                                            # Add Edit, Send Now and Delete buttons side-by-side
                                            keyboard.append([
                                                {"text": f"✏️ Edit ({ad_id})", "callback_data": f"admin_edit_{ad_id}"},
                                                {"text": f"🚀 Send Now", "callback_data": f"admin_post_now_{ad_id}"},
                                                {"text": f"🗑️ Delete", "callback_data": f"admin_del_{ad_id}"}
                                            ])
                                        
                                        keyboard.append([{"text": "⬅️ Back to Admin Control", "callback_data": "admin_refresh"}])
                                        reply_markup = {"inline_keyboard": keyboard}
                                    
                                    # Update message or send a new one
                                    session.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={
                                        "chat_id": chat_id_private,
                                        "text": text_list,
                                        "parse_mode": "HTML",
                                        "reply_markup": json.dumps(reply_markup)
                                    }, timeout=10)

                                elif cq_data.startswith("admin_del_"):
                                    del_id = cq_data.replace("admin_del_", "")
                                    # Remove ad from config
                                    updated_config = [ad for ad in config_data if str(ad.get("id")) != str(del_id)]
                                    save_json_file(DEFAULT_CONFIG_FILE, updated_config)
                                    
                                    # Confirm deletion
                                    session.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={
                                        "chat_id": chat_id_private,
                                        "text": f"✅ <b>Ad with ID '{del_id}' deleted successfully!</b>\n\nChanges saved and scheduled updates will take effect instantly.",
                                        "parse_mode": "HTML",
                                        "reply_markup": json.dumps({"inline_keyboard": [[{"text": "⬅️ Back to List", "callback_data": "admin_list"}]]})
                                    }, timeout=10)

                                elif cq_data.startswith("admin_post_now_"):
                                    post_id = cq_data.replace("admin_post_now_", "")
                                    target_ad = next((ad for ad in config_data if str(ad.get("id")) == str(post_id)), None)
                                    if target_ad:
                                        state_data = load_json_file(DEFAULT_STATE_FILE, {})
                                        active_channels = state_data.get("active_channels", [chat_id])
                                        if chat_id not in active_channels and str(chat_id) not in active_channels:
                                            active_channels.insert(0, chat_id)
                                        
                                        success_count = 0
                                        for active_chan in active_channels:
                                            if post_ad_to_telegram(bot_token, active_chan, target_ad):
                                                success_count += 1
                                        
                                        session.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={
                                            "chat_id": chat_id_private,
                                            "text": f"🚀 <b>Instant Ad Broadcast Complete!</b>\n\nSent Ad ID: <code>{post_id}</code> successfully to {success_count} channel(s) right now!",
                                            "parse_mode": "HTML",
                                            "reply_markup": json.dumps({"inline_keyboard": [[{"text": "⬅️ Back to List", "callback_data": "admin_list"}]]})
                                        }, timeout=10)
                                    else:
                                        session.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={
                                            "chat_id": chat_id_private,
                                            "text": "⚠️ Ad not found or already deleted.",
                                            "parse_mode": "HTML",
                                            "reply_markup": json.dumps({"inline_keyboard": [[{"text": "⬅️ Back to List", "callback_data": "admin_list"}]]})
                                        }, timeout=10)

                                elif cq_data == "admin_refresh":
                                    num_channels = len(state_data.get("active_channels", [chat_id]))
                                    show_admin_panel(session, bot_token, chat_id_private, num_channels, len(config_data))

                                elif cq_data.startswith("admin_edit_") and not cq_data.startswith("admin_editopt_"):
                                    edit_id = cq_data.replace("admin_edit_", "")
                                    target_ad = next((ad for ad in config_data if str(ad.get("id")) == str(edit_id)), None)
                                    if target_ad:
                                        text_list = (
                                            f"✏️ <b>Edit Ad Console</b> (ID: <code>{edit_id}</code>)\n\n"
                                            f"📝 <b>Current Caption:</b>\n{target_ad.get('caption', '')}\n\n"
                                            f"🔗 <b>Button Label:</b> {target_ad.get('button_text')}\n"
                                            f"🔗 <b>Button URL:</b> {target_ad.get('button_url')}\n"
                                            f"⏰ <b>Interval:</b> {target_ad.get('interval_minutes')} mins\n\n"
                                            f"Choose what you would like to edit below:"
                                        )
                                        keyboard = [
                                            [{"text": "📝 Edit Caption", "callback_data": f"admin_editopt_caption_{edit_id}"}],
                                            [{"text": "🏷️ Edit Button Label", "callback_data": f"admin_editopt_label_{edit_id}"}],
                                            [{"text": "🔗 Edit Button URL", "callback_data": f"admin_editopt_url_{edit_id}"}],
                                            [{"text": "⏰ Edit Posting Interval", "callback_data": f"admin_editopt_interval_{edit_id}"}],
                                            [{"text": "⬅️ Back to Ads List", "callback_data": "admin_list"}]
                                        ]
                                        session.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={
                                            "chat_id": chat_id_private,
                                            "text": text_list,
                                            "parse_mode": "HTML",
                                            "reply_markup": json.dumps({"inline_keyboard": keyboard})
                                        }, timeout=10)
                                    else:
                                        session.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={
                                            "chat_id": chat_id_private,
                                            "text": "⚠️ Ad not found or already deleted.",
                                            "parse_mode": "HTML",
                                            "reply_markup": json.dumps({"inline_keyboard": [[{"text": "⬅️ Back to List", "callback_data": "admin_list"}]]})
                                        }, timeout=10)

                                elif cq_data.startswith("admin_editopt_"):
                                    parts = cq_data.split("_")
                                    if len(parts) >= 4:
                                        opt = parts[2]
                                        ad_id = "_".join(parts[3:])
                                        
                                        user_state["step"] = f"awaiting_edit_{opt}"
                                        user_state["editing_ad_id"] = ad_id
                                        state_data["admin_states"][str(chat_id_private)] = user_state
                                        save_json_file(DEFAULT_STATE_FILE, state_data)
                                        
                                        prompts = {
                                            "caption": "✍️ <b>Edit Caption/Description</b>\n\nPlease enter the new caption/description text for your ad below. It will automatically be formatted nicely as a blockquote:",
                                            "label": "🏷️ <b>Edit Button Label</b>\n\nPlease enter the new text/label for the button (e.g. <i>Join Now! 🚀</i>):",
                                            "url": "🔗 <b>Edit Button URL</b>\n\nPlease enter the new destination URL (e.g. <i>https://t.me/FeaturesticLeaks</i>):",
                                            "interval": "⏰ <b>Edit Posting Interval</b>\n\nPlease enter the new posting interval in minutes (e.g. <i>120</i> or <i>350</i>):"
                                        }
                                        
                                        prompt_text = prompts.get(opt, "Please type the new value below:")
                                        reply_markup = {
                                            "inline_keyboard": [[{"text": "❌ Cancel", "callback_data": f"admin_edit_{ad_id}"}]]
                                        }
                                        session.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={
                                            "chat_id": chat_id_private,
                                            "text": prompt_text,
                                            "parse_mode": "HTML",
                                            "reply_markup": json.dumps(reply_markup)
                                        }, timeout=10)

                                elif cq_data == "admin_channels":
                                    current_chans = state_data.get("active_channels", [chat_id])
                                    if chat_id not in current_chans and str(chat_id) not in current_chans:
                                        current_chans.insert(0, chat_id)
                                    
                                    text_list = "📢 <b>Active Ad-Posting Channels Network:</b>\n\n"
                                    text_list += "The bot will automatically post scheduled ads to all channels listed below:\n\n"
                                    
                                    keyboard = []
                                    for i, c in enumerate(current_chans):
                                        is_primary = str(c) == str(chat_id)
                                        tag = "👑 Primary" if is_primary else "Channel"
                                        text_list += f"• <code>{c}</code> (<b>{tag}</b>)\n"
                                        
                                        # Only show a delete button for non-primary channels
                                        if not is_primary:
                                            keyboard.append([
                                                {"text": f"🗑️ Remove {c}", "callback_data": f"admin_remchan_{c}"}
                                            ])
                                    
                                    keyboard.append([{"text": "➕ Add Channel Manually", "callback_data": "admin_addchan_prompt"}])
                                    keyboard.append([{"text": "⬅️ Back to Admin Console", "callback_data": "admin_refresh"}])
                                    
                                    reply_markup = {"inline_keyboard": keyboard}
                                    session.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={
                                        "chat_id": chat_id_private,
                                        "text": text_list,
                                        "parse_mode": "HTML",
                                        "reply_markup": json.dumps(reply_markup)
                                    }, timeout=10)

                                elif cq_data == "admin_addchan_prompt":
                                    user_state["step"] = "awaiting_add_channel"
                                    state_data["admin_states"][str(chat_id_private)] = user_state
                                    save_json_file(DEFAULT_STATE_FILE, state_data)
                                    
                                    prompt_text = (
                                        "📢 <b>Add Channel Manually</b>\n\n"
                                        "Please type or paste the channel's public username (e.g., <code>@MyNewChannel</code>) or private channel ID (e.g., <code>-1001234567890</code>).\n\n"
                                        "<i>Make sure the bot is already an administrator in that channel with 'Post Messages' permission!</i>"
                                    )
                                    reply_markup = {
                                        "inline_keyboard": [[{"text": "❌ Cancel", "callback_data": "admin_channels"}]]
                                    }
                                    session.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={
                                        "chat_id": chat_id_private,
                                        "text": prompt_text,
                                        "parse_mode": "HTML",
                                        "reply_markup": json.dumps(reply_markup)
                                    }, timeout=10)

                                elif cq_data.startswith("admin_remchan_"):
                                    to_rem = cq_data.replace("admin_remchan_", "")
                                    current_chans = state_data.get("active_channels", [chat_id])
                                    
                                    matched_item = None
                                    for item in current_chans:
                                        if str(item) == str(to_rem):
                                            matched_item = item
                                            break
                                            
                                    if matched_item is not None:
                                        current_chans.remove(matched_item)
                                        state_data["active_channels"] = current_chans
                                        save_json_file(DEFAULT_STATE_FILE, state_data)
                                        confirm_text = f"✅ <b>Successfully removed channel:</b> <code>{to_rem}</code> from the ad queue."
                                    else:
                                        confirm_text = f"⚠️ Channel <code>{to_rem}</code> was not found in the active list."
                                        
                                    session.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={
                                        "chat_id": chat_id_private,
                                        "text": confirm_text,
                                        "parse_mode": "HTML",
                                        "reply_markup": json.dumps({"inline_keyboard": [[{"text": "⬅️ Back to Channels", "callback_data": "admin_channels"}]]})
                                    }, timeout=10)

                                elif cq_data == "skip_media":
                                    if user_state["step"] == "awaiting_media":
                                        temp_ad = user_state.get("temp_ad", {})
                                        new_id = f"ad_{int(time.time())}"
                                        
                                        # Save text ad configuration
                                        ad_object = {
                                            "id": new_id,
                                            "media_type": "text",
                                            "caption": temp_ad.get("caption"),
                                            "button_text": temp_ad.get("button_text"),
                                            "button_url": temp_ad.get("button_url"),
                                            "interval_minutes": temp_ad.get("interval_minutes", 120)
                                        }
                                        
                                        config_data.append(ad_object)
                                        save_json_file(DEFAULT_CONFIG_FILE, config_data)
                                        
                                        # Instantly post the newly created ad to all active channels!
                                        active_channels = state_data.get("active_channels", [chat_id])
                                        if chat_id not in active_channels and str(chat_id) not in active_channels:
                                            active_channels.insert(0, chat_id)
                                        
                                        success_count = 0
                                        for active_chan in active_channels:
                                            if post_ad_to_telegram(bot_token, active_chan, ad_object):
                                                success_count += 1
                                                
                                        # Clear state
                                        user_state["step"] = "None"
                                        user_state["temp_ad"] = {}
                                        state_data["admin_states"][str(chat_id_private)] = user_state
                                        save_json_file(DEFAULT_STATE_FILE, state_data)
                                        
                                        # Success message
                                        confirm_text = (
                                            f"🎉 <b>Premium Ad Configured & Sent Successfully!</b>\n\n"
                                            f"📝 <b>Ad Type:</b> Text-Only Ad\n"
                                            f"⏰ <b>Interval:</b> {ad_object['interval_minutes']} minutes\n"
                                            f"🔗 <b>Button:</b> {ad_object['button_text']} ({ad_object['button_url']})\n\n"
                                            f"🚀 <b>Immediate BroadCast:</b> Successfully sent to {success_count} channel(s) right now!\n\n"
                                            f"Your new ad has been loaded into the active scheduled queue!"
                                        )
                                        session.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={
                                            "chat_id": chat_id_private,
                                            "text": confirm_text,
                                            "parse_mode": "HTML",
                                            "reply_markup": json.dumps({"inline_keyboard": [[{"text": "⬅️ Back to Admin Console", "callback_data": "admin_refresh"}]]})
                                        }, timeout=10)

                                elif cq_data == "admin_cancel":
                                    user_state["step"] = "None"
                                    user_state["temp_ad"] = {}
                                    state_data["admin_states"][str(chat_id_private)] = user_state
                                    save_json_file(DEFAULT_STATE_FILE, state_data)
                                    session.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={
                                        "chat_id": chat_id_private,
                                        "text": "❌ <b>Ad creation process was cancelled.</b>",
                                        "parse_mode": "HTML",
                                        "reply_markup": json.dumps({"inline_keyboard": [[{"text": "⬅️ Admin Console", "callback_data": "admin_refresh"}]]})
                                    }, timeout=10)

                                elif cq_data == "admin_close":
                                    session.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={
                                        "chat_id": chat_id_private,
                                        "text": "🔒 <b>Admin Control Console Closed.</b>\nType /admin anytime to reopen.",
                                        "parse_mode": "HTML"
                                    }, timeout=10)

                        # --- Check for User direct/private Messages ---
                        message = update.get("message")
                        if not message:
                            continue
                        
                        chat = message.get("chat", {})
                        chat_id_private = chat.get("id")
                        chat_type = chat.get("type")
                        text = message.get("text", "").strip()
                        sender = message.get("from", {})
                        first_name = sender.get("first_name", "User")

                        if chat_type == "private" and chat_id_private:
                            print(f"Received private chat message from {first_name}: {text or '[Media]'}", flush=True)
                            
                            # Load configuration and state files
                            state_data = load_json_file(DEFAULT_STATE_FILE, {})
                            config_data = load_json_file(DEFAULT_CONFIG_FILE, [])

                            # Set Admin ID if not defined
                            if "admin_chat_id" not in state_data or not state_data["admin_chat_id"]:
                                state_data["admin_chat_id"] = chat_id_private
                                save_json_file(DEFAULT_STATE_FILE, state_data)

                            is_admin = (state_data.get("admin_chat_id") == chat_id_private)

                            if "admin_states" not in state_data or not isinstance(state_data["admin_states"], dict):
                                state_data["admin_states"] = {}
                            
                            user_state = state_data["admin_states"].get(str(chat_id_private), {"step": "None", "temp_ad": {}})
                            current_step = user_state.get("step", "None")

                            # --- Interactive State Machine Handler for Admin Ad Creation ---
                            if is_admin and current_step != "None":
                                if text == "/cancel":
                                    user_state["step"] = "None"
                                    user_state["temp_ad"] = {}
                                    state_data["admin_states"][str(chat_id_private)] = user_state
                                    save_json_file(DEFAULT_STATE_FILE, state_data)
                                    session.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={
                                        "chat_id": chat_id_private,
                                        "text": "❌ Ad creation cancelled. Main menu loaded.",
                                        "reply_markup": json.dumps({"inline_keyboard": [[{"text": "⬅️ Back", "callback_data": "admin_refresh"}]]})
                                    }, timeout=10)
                                    continue

                                if current_step == "awaiting_edit_caption":
                                    if not text:
                                        session.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={
                                            "chat_id": chat_id_private,
                                            "text": "⚠️ Please send a valid text description."
                                        }, timeout=10)
                                        continue
                                    
                                    ad_id = user_state.get("editing_ad_id")
                                    import re
                                    clean = text.strip()
                                    while clean.startswith("<b>") and clean.endswith("</b>"):
                                        clean = clean[3:-4].strip()
                                    while clean.startswith("<strong>") and clean.endswith("</strong>"):
                                        clean = clean[8:-9].strip()
                                    
                                    clean = re.sub(r'</?tg-spoiler>', '', clean)
                                    clean = re.sub(r'<span\s+class=["\']tg-spoiler["\']>', '', clean)
                                    clean = re.sub(r'</?blockquote>', '', clean)
                                    clean = re.sub(r'</span>', '', clean)
                                    formatted_caption = f"<blockquote><b>{clean.strip()}</b></blockquote>"
                                    
                                    updated = False
                                    for ad in config_data:
                                        if str(ad.get("id")) == str(ad_id):
                                            ad["caption"] = formatted_caption
                                            updated = True
                                            break
                                            
                                    if updated:
                                        save_json_file(DEFAULT_CONFIG_FILE, config_data)
                                        user_state["step"] = "None"
                                        user_state["editing_ad_id"] = None
                                        state_data["admin_states"][str(chat_id_private)] = user_state
                                        save_json_file(DEFAULT_STATE_FILE, state_data)
                                        
                                        session.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={
                                            "chat_id": chat_id_private,
                                            "text": f"✅ <b>Caption updated successfully for Ad ID:</b> <code>{ad_id}</code>!",
                                            "parse_mode": "HTML",
                                            "reply_markup": json.dumps({"inline_keyboard": [[{"text": "⬅️ Back to Ad", "callback_data": f"admin_edit_{ad_id}"}]]})
                                        }, timeout=10)
                                    else:
                                        session.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={
                                            "chat_id": chat_id_private,
                                            "text": "⚠️ Ad not found or was deleted.",
                                            "parse_mode": "HTML",
                                            "reply_markup": json.dumps({"inline_keyboard": [[{"text": "⬅️ Back to List", "callback_data": "admin_list"}]]})
                                        }, timeout=10)
                                    continue

                                if current_step == "awaiting_edit_label":
                                    if not text:
                                        session.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={
                                            "chat_id": chat_id_private,
                                            "text": "⚠️ Please send a valid button label text."
                                        }, timeout=10)
                                        continue
                                    
                                    ad_id = user_state.get("editing_ad_id")
                                    updated = False
                                    for ad in config_data:
                                        if str(ad.get("id")) == str(ad_id):
                                            ad["button_text"] = text.strip()
                                            updated = True
                                            break
                                            
                                    if updated:
                                        save_json_file(DEFAULT_CONFIG_FILE, config_data)
                                        user_state["step"] = "None"
                                        user_state["editing_ad_id"] = None
                                        state_data["admin_states"][str(chat_id_private)] = user_state
                                        save_json_file(DEFAULT_STATE_FILE, state_data)
                                        
                                        session.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={
                                            "chat_id": chat_id_private,
                                            "text": f"✅ <b>Button label updated successfully for Ad ID:</b> <code>{ad_id}</code>!",
                                            "parse_mode": "HTML",
                                            "reply_markup": json.dumps({"inline_keyboard": [[{"text": "⬅️ Back to Ad", "callback_data": f"admin_edit_{ad_id}"}]]})
                                        }, timeout=10)
                                    else:
                                        session.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={
                                            "chat_id": chat_id_private,
                                            "text": "⚠️ Ad not found or was deleted.",
                                            "parse_mode": "HTML",
                                            "reply_markup": json.dumps({"inline_keyboard": [[{"text": "⬅️ Back to List", "callback_data": "admin_list"}]]})
                                        }, timeout=10)
                                    continue

                                if current_step == "awaiting_edit_url":
                                    if not text or not (text.startswith("http://") or text.startswith("https://") or text.startswith("t.me/")):
                                        session.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={
                                            "chat_id": chat_id_private,
                                            "text": "⚠️ Please enter a valid URL starting with <code>http://</code> or <code>https://</code>.",
                                            "parse_mode": "HTML"
                                        }, timeout=10)
                                        continue
                                    
                                    normalized_link = text.strip()
                                    if normalized_link.startswith("t.me/"):
                                        normalized_link = "https://" + normalized_link
                                        
                                    ad_id = user_state.get("editing_ad_id")
                                    updated = False
                                    for ad in config_data:
                                        if str(ad.get("id")) == str(ad_id):
                                            ad["button_url"] = normalized_link
                                            updated = True
                                            break
                                            
                                    if updated:
                                        save_json_file(DEFAULT_CONFIG_FILE, config_data)
                                        user_state["step"] = "None"
                                        user_state["editing_ad_id"] = None
                                        state_data["admin_states"][str(chat_id_private)] = user_state
                                        save_json_file(DEFAULT_STATE_FILE, state_data)
                                        
                                        session.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={
                                            "chat_id": chat_id_private,
                                            "text": f"✅ <b>Button URL updated successfully for Ad ID:</b> <code>{ad_id}</code>!",
                                            "parse_mode": "HTML",
                                            "reply_markup": json.dumps({"inline_keyboard": [[{"text": "⬅️ Back to Ad", "callback_data": f"admin_edit_{ad_id}"}]]})
                                        }, timeout=10)
                                    else:
                                        session.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={
                                            "chat_id": chat_id_private,
                                            "text": "⚠️ Ad not found or was deleted.",
                                            "parse_mode": "HTML",
                                            "reply_markup": json.dumps({"inline_keyboard": [[{"text": "⬅️ Back to List", "callback_data": "admin_list"}]]})
                                        }, timeout=10)
                                    continue

                                if current_step == "awaiting_edit_interval":
                                    try:
                                        interval_min = int(text)
                                        if interval_min <= 0:
                                            raise ValueError()
                                    except ValueError:
                                        session.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={
                                            "chat_id": chat_id_private,
                                            "text": "⚠️ Please enter a valid positive integer for minutes.",
                                            "parse_mode": "HTML"
                                        }, timeout=10)
                                        continue
                                        
                                    ad_id = user_state.get("editing_ad_id")
                                    updated = False
                                    for ad in config_data:
                                        if str(ad.get("id")) == str(ad_id):
                                            ad["interval_minutes"] = interval_min
                                            updated = True
                                            break
                                            
                                    if updated:
                                        save_json_file(DEFAULT_CONFIG_FILE, config_data)
                                        user_state["step"] = "None"
                                        user_state["editing_ad_id"] = None
                                        state_data["admin_states"][str(chat_id_private)] = user_state
                                        save_json_file(DEFAULT_STATE_FILE, state_data)
                                        
                                        session.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={
                                            "chat_id": chat_id_private,
                                            "text": f"✅ <b>Posting interval updated successfully to {interval_min} minutes for Ad ID:</b> <code>{ad_id}</code>!",
                                            "parse_mode": "HTML",
                                            "reply_markup": json.dumps({"inline_keyboard": [[{"text": "⬅️ Back to Ad", "callback_data": f"admin_edit_{ad_id}"}]]})
                                        }, timeout=10)
                                    else:
                                        session.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={
                                            "chat_id": chat_id_private,
                                            "text": "⚠️ Ad not found or was deleted.",
                                            "parse_mode": "HTML",
                                            "reply_markup": json.dumps({"inline_keyboard": [[{"text": "⬅️ Back to List", "callback_data": "admin_list"}]]})
                                        }, timeout=10)
                                    continue

                                if current_step == "awaiting_add_channel":
                                    if not text:
                                        session.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={
                                            "chat_id": chat_id_private,
                                            "text": "⚠️ Please send a valid channel username (e.g., @MyNewChannel) or ID."
                                        }, timeout=10)
                                        continue
                                    
                                    new_chan = text.strip()
                                    if "active_channels" not in state_data or not isinstance(state_data["active_channels"], list):
                                        state_data["active_channels"] = [chat_id]
                                    
                                    if new_chan not in state_data["active_channels"] and str(new_chan) not in state_data["active_channels"]:
                                        state_data["active_channels"].append(new_chan)
                                        user_state["step"] = "None"
                                        state_data["admin_states"][str(chat_id_private)] = user_state
                                        save_json_file(DEFAULT_STATE_FILE, state_data)
                                        
                                        session.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={
                                            "chat_id": chat_id_private,
                                            "text": f"✅ <b>Successfully added channel:</b> <code>{new_chan}</code> to active posting list!",
                                            "parse_mode": "HTML",
                                            "reply_markup": json.dumps({"inline_keyboard": [[{"text": "📢 Manage Channels", "callback_data": "admin_channels"}]]})
                                        }, timeout=10)
                                    else:
                                        user_state["step"] = "None"
                                        state_data["admin_states"][str(chat_id_private)] = user_state
                                        save_json_file(DEFAULT_STATE_FILE, state_data)
                                        session.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={
                                            "chat_id": chat_id_private,
                                            "text": f"ℹ️ Channel <code>{new_chan}</code> is already in active posting list.",
                                            "parse_mode": "HTML",
                                            "reply_markup": json.dumps({"inline_keyboard": [[{"text": "📢 Manage Channels", "callback_data": "admin_channels"}]]})
                                        }, timeout=10)
                                    continue

                                if current_step == "awaiting_text":
                                    if not text:
                                        session.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={
                                            "chat_id": chat_id_private,
                                            "text": "⚠️ Please send a valid text description for your ad."
                                        }, timeout=10)
                                        continue
                                    
                                    # Ensure caption stays bold and quote (blockquote) as requested
                                    import re
                                    clean = text.strip()
                                    while clean.startswith("<b>") and clean.endswith("</b>"):
                                        clean = clean[3:-4].strip()
                                    while clean.startswith("<strong>") and clean.endswith("</strong>"):
                                        clean = clean[8:-9].strip()
                                    
                                    clean = re.sub(r'</?tg-spoiler>', '', clean)
                                    clean = re.sub(r'<span\s+class=["\']tg-spoiler["\']>', '', clean)
                                    clean = re.sub(r'</?blockquote>', '', clean)
                                    clean = re.sub(r'</span>', '', clean)
                                    formatted_caption = f"<blockquote><b>{clean.strip()}</b></blockquote>"
                                        
                                    user_state["temp_ad"]["caption"] = formatted_caption
                                    user_state["step"] = "awaiting_link"
                                    state_data["admin_states"][str(chat_id_private)] = user_state
                                    save_json_file(DEFAULT_STATE_FILE, state_data)

                                    prompt = (
                                        "🔗 <b>Step 2 of 5: Enter Join Link</b>\n\n"
                                        "Please paste the destination link / channel URL that you want to attach as a button at the bottom of your ad.\n\n"
                                        "<i>Example: https://t.me/FeaturesticLeaks</i>"
                                    )
                                    session.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={
                                        "chat_id": chat_id_private,
                                        "text": prompt,
                                        "parse_mode": "HTML",
                                        "reply_markup": json.dumps({"inline_keyboard": [[{"text": "❌ Cancel", "callback_data": "admin_cancel"}]]})
                                    }, timeout=10)

                                elif current_step == "awaiting_link":
                                    if not text or not (text.startswith("http://") or text.startswith("https://") or text.startswith("t.me/")):
                                        session.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={
                                            "chat_id": chat_id_private,
                                            "text": "⚠️ <b>Invalid Link!</b> Please enter a valid URL starting with <code>http://</code> or <code>https://</code>.",
                                            "parse_mode": "HTML"
                                        }, timeout=10)
                                        continue
                                    
                                    # Normalize t.me/ links to https://t.me/
                                    normalized_link = text
                                    if text.startswith("t.me/"):
                                        normalized_link = "https://" + text

                                    user_state["temp_ad"]["button_url"] = normalized_link
                                    user_state["step"] = "awaiting_button_text"
                                    state_data["admin_states"][str(chat_id_private)] = user_state
                                    save_json_file(DEFAULT_STATE_FILE, state_data)

                                    prompt = (
                                        "🏷️ <b>Step 3 of 5: Enter Button Label/Text</b>\n\n"
                                        "Please type the text to display inside the join button under your ad.\n\n"
                                        "<i>Example: Join Channel 🚀</i>"
                                    )
                                    session.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={
                                        "chat_id": chat_id_private,
                                        "text": prompt,
                                        "parse_mode": "HTML",
                                        "reply_markup": json.dumps({"inline_keyboard": [[{"text": "❌ Cancel", "callback_data": "admin_cancel"}]]})
                                    }, timeout=10)

                                elif current_step == "awaiting_button_text":
                                    if not text:
                                        session.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={
                                            "chat_id": chat_id_private,
                                            "text": "⚠️ Please send a valid button label text."
                                        }, timeout=10)
                                        continue

                                    user_state["temp_ad"]["button_text"] = text
                                    user_state["step"] = "awaiting_interval"
                                    state_data["admin_states"][str(chat_id_private)] = user_state
                                    save_json_file(DEFAULT_STATE_FILE, state_data)

                                    prompt = (
                                        "⏰ <b>Step 4 of 5: Enter Posting Interval</b>\n\n"
                                        "Please enter the posting interval (in minutes).\n\n"
                                        "<i>Example: 120 (for every 2 hours) or 350 (for every 5 hours and 50 mins)</i>"
                                    )
                                    session.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={
                                        "chat_id": chat_id_private,
                                        "text": prompt,
                                        "parse_mode": "HTML",
                                        "reply_markup": json.dumps({"inline_keyboard": [[{"text": "❌ Cancel", "callback_data": "admin_cancel"}]]})
                                    }, timeout=10)

                                elif current_step == "awaiting_interval":
                                    try:
                                        interval_min = int(text)
                                        if interval_min <= 0:
                                            raise ValueError()
                                    except ValueError:
                                        reply_markup = {
                                            "inline_keyboard": [
                                                [{"text": "❌ Cancel Ad Creation", "callback_data": "admin_cancel"}]
                                            ]
                                        }
                                        session.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={
                                            "chat_id": chat_id_private,
                                            "text": "⚠️ <b>Invalid Input!</b> Please enter a valid positive number of minutes (e.g., 120 or 350).\n\n<i>Or cancel using the button below:</i>",
                                            "parse_mode": "HTML",
                                            "reply_markup": json.dumps(reply_markup)
                                        }, timeout=10)
                                        continue

                                    user_state["temp_ad"]["interval_minutes"] = interval_min
                                    user_state["step"] = "awaiting_media"
                                    state_data["admin_states"][str(chat_id_private)] = user_state
                                    save_json_file(DEFAULT_STATE_FILE, state_data)

                                    prompt = (
                                        "📸 <b>Step 5 of 5: Attach Photo or GIF (Optional)</b>\n\n"
                                        "Please send a <b>Photo (Image)</b> or a <b>GIF (Animation)</b> to attach as media to this ad.\n\n"
                                        "If you prefer to make this a simple <b>Text-Only Ad</b>, click the button below to complete the setup instantly!"
                                    )
                                    reply_markup = {
                                        "inline_keyboard": [
                                            [{"text": "📄 Make Text-Only Ad", "callback_data": "skip_media"}],
                                            [{"text": "❌ Cancel Process", "callback_data": "admin_cancel"}]
                                        ]
                                    }
                                    session.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={
                                        "chat_id": chat_id_private,
                                        "text": prompt,
                                        "parse_mode": "HTML",
                                        "reply_markup": json.dumps(reply_markup)
                                    }, timeout=10)

                                elif current_step == "awaiting_media":
                                    media_type = "text"
                                    file_id = None
                                    
                                    # Inspect message content for photo or animation
                                    if "photo" in message:
                                        photo_sizes = message["photo"]
                                        if photo_sizes:
                                            file_id = photo_sizes[-1]["file_id"]
                                            media_type = "photo"
                                    elif "animation" in message:
                                        file_id = message["animation"]["file_id"]
                                        media_type = "animation"

                                    if not file_id:
                                        session.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={
                                            "chat_id": chat_id_private,
                                            "text": "⚠️ <b>Invalid Media!</b> Please send an image photo or a GIF, or click the 'Make Text-Only Ad' button above."
                                        }, timeout=10)
                                        continue

                                    temp_ad = user_state.get("temp_ad", {})
                                    new_id = f"ad_{int(time.time())}"
                                    
                                    ad_object = {
                                        "id": new_id,
                                        "media_type": media_type,
                                        "file_id": file_id,
                                        "caption": temp_ad.get("caption"),
                                        "button_text": temp_ad.get("button_text"),
                                        "button_url": temp_ad.get("button_url"),
                                        "interval_minutes": temp_ad.get("interval_minutes", 120)
                                    }
                                    
                                    config_data.append(ad_object)
                                    save_json_file(DEFAULT_CONFIG_FILE, config_data)
                                    
                                    # Instantly post the newly created ad to all active channels!
                                    active_channels = state_data.get("active_channels", [chat_id])
                                    if chat_id not in active_channels and str(chat_id) not in active_channels:
                                        active_channels.insert(0, chat_id)
                                    
                                    success_count = 0
                                    for active_chan in active_channels:
                                        if post_ad_to_telegram(bot_token, active_chan, ad_object):
                                            success_count += 1
                                            
                                    # Reset state
                                    user_state["step"] = "None"
                                    user_state["temp_ad"] = {}
                                    state_data["admin_states"][str(chat_id_private)] = user_state
                                    save_json_file(DEFAULT_STATE_FILE, state_data)
                                    
                                    # Success confirmation
                                    confirm_text = (
                                        f"🎉 <b>Premium Ad Configured & Sent Successfully!</b>\n\n"
                                        f"🎬 <b>Ad Type:</b> {media_type.capitalize()}\n"
                                        f"⏰ <b>Interval:</b> {ad_object['interval_minutes']} minutes\n"
                                        f"🔗 <b>Button:</b> {ad_object['button_text']} ({ad_object['button_url']})\n\n"
                                        f"🚀 <b>Immediate BroadCast:</b> Successfully sent to {success_count} channel(s) right now!\n\n"
                                        f"Your new media ad is fully synchronized and operational!"
                                    )
                                    session.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={
                                        "chat_id": chat_id_private,
                                        "text": confirm_text,
                                        "parse_mode": "HTML",
                                        "reply_markup": json.dumps({"inline_keyboard": [[{"text": "⬅️ Back to Admin Console", "callback_data": "admin_refresh"}]]})
                                    }, timeout=10)
                                continue

                            # --- Check for forwarded message from channel to register it ---
                            forward_from_chat = message.get("forward_from_chat")
                            if is_admin and forward_from_chat and forward_from_chat.get("type") in ["channel", "supergroup"]:
                                chan_id = forward_from_chat.get("id")
                                chan_title = forward_from_chat.get("title", "Channel")
                                chan_username = forward_from_chat.get("username")
                                
                                chan_identifier = f"@{chan_username}" if chan_username else chan_id
                                
                                if "active_channels" not in state_data or not isinstance(state_data["active_channels"], list):
                                    state_data["active_channels"] = [chat_id]
                                
                                if chan_identifier not in state_data["active_channels"] and str(chan_id) not in state_data["active_channels"] and str(chan_identifier) not in state_data["active_channels"]:
                                    state_data["active_channels"].append(chan_identifier)
                                    save_json_file(DEFAULT_STATE_FILE, state_data)
                                    session.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={
                                        "chat_id": chat_id_private,
                                        "text": f"🎉 <b>Channel Registered Successfully!</b>\n\n📢 <b>Name:</b> {chan_title}\n🆔 <b>ID/User:</b> <code>{chan_identifier}</code>\n\nThis channel has been added to your active ad-posting network and will receive automated ads!",
                                        "parse_mode": "HTML"
                                    }, timeout=10)
                                else:
                                    session.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={
                                        "chat_id": chat_id_private,
                                        "text": f"ℹ️ <b>Channel Already Registered!</b>\n\n📢 <b>Name:</b> {chan_title}\n🆔 <b>ID/User:</b> <code>{chan_identifier}</code> is already in your active list.",
                                        "parse_mode": "HTML"
                                    }, timeout=10)
                                continue

                            # --- Normal Non-state commands (/start and /admin) ---
                            if text == "/start":
                                reply_text = (
                                    f"👑 <b>Hello {first_name}! Welcome to Telegram Ad Poster Bot!</b> 🌟\n\n"
                                    f"Aapka automated scheduled ad poster system fully active aur 24x7 running hai! ✨\n\n"
                                    f"📢 <b>How to Run Ads on Your Channel:</b>\n"
                                    f"1️⃣ Niche diye gaye <b>\"Add Me to Your Channel\"</b> button par click karein.\n"
                                    f"2️⃣ Apna desired channel select karein aur bot ko add karein.\n"
                                    f"3️⃣ Bot ko <b>Admin permissions</b> (Post, Edit, and Delete Messages) dein.\n"
                                    f"4️⃣ Bus! Bot automatically scheduled intervals par configured ads post karna shuru kar dega.\n\n"
                                    f"🛠️ <b>Admin Commands:</b>\n"
                                    f"• <code>/addchannel @channelname</code> - Add channel manually\n"
                                    f"• <code>/removechannel @channelname</code> - Remove channel\n"
                                    f"• <code>/listchannels</code> - List all active channels\n"
                                    f"• <i>Forward any post from your channel to this bot to register it automatically!</i>\n\n"
                                    f"💻 <b>System Status:</b> Online 🟢\n"
                                    f"⏰ <b>Uptime Cycle:</b> Continuous loops via GitHub Actions."
                                )
                                
                                add_to_channel_url = f"https://t.me/{bot_username}?startchannel=true&admin=post_messages+edit_messages+delete_messages+invite_users"
                                
                                inline_kb = [
                                    [{"text": "📢 Add Me to Your Channel (Run Ads)", "url": add_to_channel_url}]
                                ]
                                
                                # If sender is admin, show Admin Panel and other shortcuts too
                                if is_admin:
                                    inline_kb.append([
                                        {"text": "🛠️ Admin Control Panel", "callback_data": "admin_refresh"},
                                        {"text": "📢 Manage Channels", "callback_data": "admin_channels"}
                                    ])
                                    inline_kb.append([
                                        {"text": "➕ Create Ad", "callback_data": "admin_create"},
                                        {"text": "📋 View Ads", "callback_data": "admin_list"}
                                    ])

                                reply_markup = {"inline_keyboard": inline_kb}
                                
                                session.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={
                                    "chat_id": chat_id_private,
                                    "text": reply_text,
                                    "parse_mode": "HTML",
                                    "reply_markup": json.dumps(reply_markup)
                                }, timeout=10)

                            elif is_admin and text.startswith("/addchannel"):
                                parts = text.split(maxsplit=1)
                                if len(parts) < 2:
                                    session.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={
                                        "chat_id": chat_id_private,
                                        "text": "⚠️ <b>Usage:</b> <code>/addchannel @channel_username</code> or <code>/addchannel -100123456789</code>",
                                        "parse_mode": "HTML",
                                        "reply_markup": json.dumps({"inline_keyboard": [[{"text": "➕ Add Channel Manually", "callback_data": "admin_addchan_prompt"}]]})
                                    }, timeout=10)
                                else:
                                    new_chan = parts[1].strip()
                                    if "active_channels" not in state_data or not isinstance(state_data["active_channels"], list):
                                        state_data["active_channels"] = [chat_id]
                                    
                                    if new_chan not in state_data["active_channels"] and str(new_chan) not in state_data["active_channels"]:
                                        state_data["active_channels"].append(new_chan)
                                        save_json_file(DEFAULT_STATE_FILE, state_data)
                                        session.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={
                                            "chat_id": chat_id_private,
                                            "text": f"✅ <b>Successfully added channel:</b> <code>{new_chan}</code> to active posting list!",
                                            "parse_mode": "HTML",
                                            "reply_markup": json.dumps({"inline_keyboard": [[{"text": "📢 Manage Channels", "callback_data": "admin_channels"}]]})
                                        }, timeout=10)
                                    else:
                                        session.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={
                                            "chat_id": chat_id_private,
                                            "text": f"ℹ️ Channel <code>{new_chan}</code> is already in active posting list.",
                                            "parse_mode": "HTML",
                                            "reply_markup": json.dumps({"inline_keyboard": [[{"text": "📢 Manage Channels", "callback_data": "admin_channels"}]]})
                                        }, timeout=10)
                                continue

                            elif is_admin and text.startswith("/removechannel"):
                                parts = text.split(maxsplit=1)
                                if len(parts) < 2:
                                    session.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={
                                        "chat_id": chat_id_private,
                                        "text": "⚠️ <b>Usage:</b> <code>/removechannel @channel_username</code> or <code>/removechannel -100123456789</code>",
                                        "parse_mode": "HTML",
                                        "reply_markup": json.dumps({"inline_keyboard": [[{"text": "🗑️ Manage Channels", "callback_data": "admin_channels"}]]})
                                    }, timeout=10)
                                else:
                                    to_rem = parts[1].strip()
                                    if "active_channels" not in state_data or not isinstance(state_data["active_channels"], list):
                                        state_data["active_channels"] = [chat_id]
                                    
                                    current_chans = state_data["active_channels"]
                                    # Handle string or int matching
                                    matched_item = None
                                    for item in current_chans:
                                        if str(item) == str(to_rem):
                                            matched_item = item
                                            break
                                            
                                    if matched_item is not None:
                                        current_chans.remove(matched_item)
                                        state_data["active_channels"] = current_chans
                                        save_json_file(DEFAULT_STATE_FILE, state_data)
                                        session.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={
                                            "chat_id": chat_id_private,
                                            "text": f"✅ <b>Successfully removed channel:</b> <code>{to_rem}</code>.",
                                            "parse_mode": "HTML",
                                            "reply_markup": json.dumps({"inline_keyboard": [[{"text": "📢 Manage Channels", "callback_data": "admin_channels"}]]})
                                        }, timeout=10)
                                    else:
                                        session.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={
                                            "chat_id": chat_id_private,
                                            "text": f"⚠️ Channel <code>{to_rem}</code> not found in active list.",
                                            "parse_mode": "HTML",
                                            "reply_markup": json.dumps({"inline_keyboard": [[{"text": "📢 Manage Channels", "callback_data": "admin_channels"}]]})
                                        }, timeout=10)
                                continue

                            elif is_admin and text == "/listchannels":
                                current_chans = state_data.get("active_channels", [chat_id])
                                if chat_id not in current_chans and str(chat_id) not in current_chans:
                                    current_chans.insert(0, chat_id)
                                
                                chan_list_text = "📢 <b>Active Ad-Posting Channels Network:</b>\n\n"
                                for i, c in enumerate(current_chans, 1):
                                    is_primary = " (Primary)" if str(c) == str(chat_id) else ""
                                    chan_list_text += f"{i}. <code>{c}</code>{is_primary}\n"
                                
                                inline_kb = [
                                    [{"text": "➕ Add Channel Manually", "callback_data": "admin_addchan_prompt"}],
                                    [{"text": "📢 Manage Channels", "callback_data": "admin_channels"}],
                                    [{"text": "⬅️ Back to Admin Console", "callback_data": "admin_refresh"}]
                                ]
                                session.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={
                                    "chat_id": chat_id_private,
                                    "text": chan_list_text,
                                    "parse_mode": "HTML",
                                    "reply_markup": json.dumps({"inline_keyboard": inline_kb})
                                }, timeout=10)
                                continue

                            elif text == "/admin":
                                if is_admin:
                                    num_channels = len(state_data.get("active_channels", [chat_id]))
                                    show_admin_panel(session, bot_token, chat_id_private, num_channels, len(config_data))
                                else:
                                    session.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={
                                        "chat_id": chat_id_private,
                                        "text": "⚠️ <b>Access Denied:</b> You are not authorized to access the Admin Console.",
                                        "parse_mode": "HTML"
                                    }, timeout=10)
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
        # If we had updates, process next updates IMMEDIATELY without sleep
        # If no updates, rest for 1 second to keep CPU low
        if not had_updates:
            time.sleep(1)

    print("Ad Posting Run Completed.")

if __name__ == "__main__":
    main()
