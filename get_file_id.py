#!/usr/bin/env python3
"""
get_file_id.py - Helper script to fetch file_id and media_type of recent photos/gifs sent to the bot.
Run this script locally to scan messages directly sent to your bot, then copy the file_ids into ads_config.json.
"""

import os
import sys
import requests

def main():
    # 1. Retrieve bot token from environment or ask user
    bot_token = os.environ.get("BOT_TOKEN")
    
    if not bot_token:
        # Hardcoded fallback of the user's bot token
        bot_token = "8918032442:AAG3p2wJ3Bm8ibtNCCs_4B8momgk8GAEGkA"

    print("=================================================================")
    print("      Telegram Bot Media file_id & media_type Scanner            ")
    print("=================================================================")
    print(f"Using Bot Token: {bot_token[:15]}...{bot_token[-15:] if len(bot_token) > 30 else ''}")
    print("Checking for recent messages sent to the bot...")
    print("Note: Make sure you have recently sent a Photo or a GIF directly to the bot first!")
    print("=================================================================\n")

    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    
    try:
        response = requests.get(url, params={"limit": 100, "allowed_updates": ["message"]}, timeout=10)
        res_json = response.json()
    except Exception as e:
        print(f"Error connecting to Telegram API: {e}")
        sys.exit(1)

    if not res_json.get("ok"):
        print(f"Telegram API Error: {res_json.get('description', 'Unknown error')}")
        sys.exit(1)

    updates = res_json.get("result", [])
    if not updates:
        print("No recent updates or messages found. Please send a photo or a GIF to your bot on Telegram first, then run this again!")
        return

    found_media = False
    
    # Process updates backwards to show latest messages first
    for update in reversed(updates):
        message = update.get("message")
        if not message:
            continue
            
        sender = message.get("from", {})
        username = sender.get("username", "NoUsername")
        first_name = sender.get("first_name", "Anonymous")
        message_id = message.get("message_id")
        date = message.get("date")

        # Check for photo
        if "photo" in message:
            photo_sizes = message["photo"]
            if photo_sizes:
                # The last item in the list represents the largest resolution photo
                largest_photo = photo_sizes[-1]
                file_id = largest_photo["file_id"]
                file_unique_id = largest_photo.get("file_unique_id", "N/A")
                print(f"📸 [PHOTO] Sent by {first_name} (@{username}) at msg_id:{message_id}")
                print(f"   -> media_type : \"photo\"")
                print(f"   -> file_id    : {file_id}")
                print(f"   -> resolution : {largest_photo.get('width')}x{largest_photo.get('height')}")
                print("-" * 65)
                found_media = True

        # Check for animation (GIF)
        elif "animation" in message:
            animation = message["animation"]
            file_id = animation["file_id"]
            file_unique_id = animation.get("file_unique_id", "N/A")
            print(f"🎬 [ANIMATION/GIF] Sent by {first_name} (@{username}) at msg_id:{message_id}")
            print(f"   -> media_type : \"animation\"")
            print(f"   -> file_id    : {file_id}")
            print(f"   -> file_name  : {animation.get('file_name', 'N/A')}")
            print("-" * 65)
            found_media = True

        # Check for general document (sometimes GIFs come as documents)
        elif "document" in message:
            doc = message["document"]
            mime = doc.get("mime_type", "")
            if mime.startswith("image/gif") or mime.startswith("video/"):
                file_id = doc["file_id"]
                print(f"📄 [DOCUMENT/GIF] Sent by {first_name} (@{username}) at msg_id:{message_id}")
                print(f"   -> media_type : \"animation\"")
                print(f"   -> file_id    : {file_id}")
                print(f"   -> file_name  : {doc.get('file_name', 'N/A')}")
                print(f"   -> mime_type  : {mime}")
                print("-" * 65)
                found_media = True

    if not found_media:
        print("No photos, GIFs, or animation media were found in the recent messages.")
        print("Please open Telegram, go to your bot, and send a PHOTO or a GIF to it, then run this script again.")

if __name__ == "__main__":
    main()
