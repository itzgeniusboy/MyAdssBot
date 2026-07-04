import React, { useState, useEffect } from "react";
import { 
  Bot, 
  Plus, 
  Trash2, 
  Edit, 
  Play, 
  RefreshCw, 
  FileText, 
  Terminal, 
  Settings, 
  Check, 
  AlertTriangle, 
  ExternalLink, 
  Image as ImageIcon, 
  Video, 
  Info, 
  Copy, 
  ArrowRight, 
  ChevronRight, 
  Calendar, 
  Clock, 
  Send,
  Sparkles,
  HelpCircle,
  FileCode
} from "lucide-react";
import { motion, AnimatePresence } from "motion/react";

interface Ad {
  id: string;
  media_type: "photo" | "animation";
  file_id: string;
  caption: string;
  button_text?: string;
  button_url?: string;
  interval_minutes: number;
}

interface StateData {
  active_channels?: (string | number)[];
  channel_states?: {
    [channelId: string]: {
      [adId: string]: number;
    };
  };
  [key: string]: any;
}

interface ScannedMedia {
  id: string;
  media_type: "photo" | "animation";
  file_id: string;
  caption: string;
  senderName: string;
  username: string;
  date: string;
  msgId: number;
  details: string;
}

export default function App() {
  // Config & State
  const [ads, setAds] = useState<Ad[]>([]);
  const [stateData, setStateData] = useState<StateData>({});
  const [loading, setLoading] = useState(true);
  const [newChannelInput, setNewChannelInput] = useState("");

  // Bot Credentials (local state initialized with default values from user specs)
  const [botToken, setBotToken] = useState("8918032442:AAG3p2wJ3Bm8ibtNCCs_4B8momgk8GAEGkA");
  const [channelId, setChannelId] = useState("@FeaturesticLeaks");

  // Bot Connection Test
  const [isTestingBot, setIsTestingBot] = useState(false);
  const [botTestResult, setBotTestResult] = useState<{ success: boolean; botName?: string; error?: string } | null>(null);

  // Telegram Media Scan
  const [scannedMedia, setScannedMedia] = useState<ScannedMedia[]>([]);
  const [isScanning, setIsScanning] = useState(false);
  const [scanError, setScanError] = useState<string | null>(null);
  const [scanSuccess, setScanSuccess] = useState(false);

  // Scheduler execution
  const [schedulerLogs, setSchedulerLogs] = useState<string[]>([]);
  const [isRunningScheduler, setIsRunningScheduler] = useState(false);
  const [schedulerSuccess, setSchedulerSuccess] = useState(false);

  // File Copying Feedback
  const [copiedFile, setCopiedFile] = useState<string | null>(null);

  // UI States
  const [activeTab, setActiveTab] = useState<"dashboard" | "scanner" | "files" | "instructions">("dashboard");
  const [codeViewerTab, setCodeViewerTab] = useState<string>("post_ads.py");
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingAd, setEditingAd] = useState<Ad | null>(null);
  
  // Ad testing status per ad
  const [adTestStatus, setAdTestStatus] = useState<{ [adId: string]: { loading: boolean; success?: boolean; error?: string } }>({});

  // Form Fields
  const [formId, setFormId] = useState("");
  const [formMediaType, setFormMediaType] = useState<"photo" | "animation">("photo");
  const [formFileId, setFormFileId] = useState("");
  const [formCaption, setFormCaption] = useState("");
  const [formButtonText, setFormButtonText] = useState("");
  const [formButtonUrl, setFormButtonUrl] = useState("");
  const [formInterval, setFormInterval] = useState<number>(60);
  const [formError, setFormError] = useState("");

  // Embedded File contents for reference in the Code Viewer tab
  const staticFiles: { [filename: string]: { code: string; language: string; description: string } } = {
    "post_ads.py": {
      language: "python",
      description: "Main scheduler script that checks intervals in state.json and posts eligible ads to Telegram.",
      code: `#!/usr/bin/env python3
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
    media_type = ad.get("media_type", "photo")
    file_id = ad.get("file_id")
    caption = ad.get("caption", "")
    button_text = ad.get("button_text")
    button_url = ad.get("button_url")

    if not file_id:
        print(f"Error: No file_id specified for ad {ad.get('id')}")
        return False

    # Construct inline keyboard
    reply_markup = {}
    if button_text and button_url:
        reply_markup = {
            "inline_keyboard": [
                [{"text": button_text, "url": button_url}]
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
    bot_token = os.environ.get("BOT_TOKEN")
    chat_id = os.environ.get("CHANNEL_ID")

    # Hardcoded Fallbacks (for manual triggers or local runs)
    if not bot_token:
        bot_token = "${botToken}"
    if not chat_id:
        chat_id = "${channelId}"

    if not bot_token or not chat_id:
        print("Error: BOT_TOKEN and CHANNEL_ID env variables must be configured.")
        sys.exit(1)

    print(f"Ad Posting Run Started at {time.strftime('%Y-%m-%d %H:%M:%S')}")
    config_data = load_json_file(DEFAULT_CONFIG_FILE, [])
    state_data = load_json_file(DEFAULT_STATE_FILE, {})

    if not config_data:
        print("No ads configured in ads_config.json.")
        return

    current_time = time.time()
    state_updated = False

    for ad in config_data:
        ad_id = str(ad.get("id"))
        interval_minutes = ad.get("interval_minutes", 120)
        
        last_posted = state_data.get(ad_id, 0)
        elapsed_minutes = (current_time - last_posted) / 60.0

        print(f"Ad '{ad_id}': Elapsed: {elapsed_minutes:.1f}m, Interval: {interval_minutes}m")

        if elapsed_minutes >= interval_minutes:
            success = post_ad_to_telegram(bot_token, chat_id, ad)
            if success:
                state_data[ad_id] = current_time
                state_updated = True
        else:
            print(f"Ad '{ad_id}' skipped. {interval_minutes - elapsed_minutes:.1f}m left.")

    if state_updated:
        save_json_file(DEFAULT_STATE_FILE, state_data)
        print("state.json updated.")

if __name__ == "__main__":
    main()`,
    },
    "get_file_id.py": {
      language: "python",
      description: "Run this script locally to fetch the Telegram file_id of recently uploaded photos or GIFs sent to your bot.",
      code: `#!/usr/bin/env python3
"""
get_file_id.py - Helper script to fetch file_id and media_type of recent photos/gifs sent to the bot.
Run this script locally to scan messages directly sent to your bot.
"""

import os
import sys
import requests

def main():
    bot_token = os.environ.get("BOT_TOKEN")
    if not bot_token:
        bot_token = "${botToken}"

    print("=================================================================")
    print("      Telegram Bot Media file_id & media_type Scanner            ")
    print("=================================================================")
    print(f"Checking updates for bot token: {bot_token[:15]}...")
    
    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    try:
        response = requests.get(url, params={"limit": 100, "allowed_updates": ["message"]}, timeout=10)
        res_json = response.json()
    except Exception as e:
        print(f"Error connecting to Telegram: {e}")
        sys.exit(1)

    if not res_json.get("ok"):
        print(f"Telegram API Error: {res_json.get('description')}")
        sys.exit(1)

    updates = res_json.get("result", [])
    if not updates:
        print("No updates found. Please send a photo or a GIF to your bot first!")
        return

    found_media = False
    for update in reversed(updates):
        message = update.get("message")
        if not message:
            continue
            
        sender = message.get("from", {})
        username = sender.get("username", "NoUsername")
        first_name = sender.get("first_name", "Anonymous")
        message_id = message.get("message_id")

        if "photo" in message:
            photo_sizes = message["photo"]
            if photo_sizes:
                largest_photo = photo_sizes[-1]
                print(f"📸 [PHOTO] Sent by {first_name} (@{username})")
                print(f"   -> media_type : \\"photo\\"")
                print(f"   -> file_id    : {largest_photo['file_id']}")
                print("-" * 50)
                found_media = True

        elif "animation" in message:
            animation = message["animation"]
            print(f"🎬 [ANIMATION/GIF] Sent by {first_name} (@{username})")
            print(f"   -> media_type : \\"animation\\"")
            print(f"   -> file_id    : {animation['file_id']}")
            print("-" * 50)
            found_media = True

    if not found_media:
        print("No photos or animation media found in recent updates.")

if __name__ == "__main__":
    main()`,
    },
    "ad-bot.yml": {
      language: "yaml",
      description: "GitHub Actions workflow file to run the scheduler cron. Place in your repo at .github/workflows/ad-bot.yml",
      code: `name: Telegram Ad Poster

on:
  schedule:
    - cron: '*/10 * * * *'  # Runs every 10 minutes
  workflow_dispatch:        # Allows manual triggering from Actions panel

permissions:
  contents: write           # Critical permission to commit state.json back

jobs:
  post-ads:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v3

      - name: Set up Python 3.11
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          if [ -f requirements.txt ]; then pip install -r requirements.txt; fi

      - name: Run Ad Poster
        env:
          BOT_TOKEN: \${{ secrets.TELEGRAM_BOT_TOKEN }}
          CHANNEL_ID: \${{ secrets.TELEGRAM_CHANNEL_ID }}
        run: |
          python post_ads.py

      - name: Commit and push state changes
        run: |
          git config --global user.name 'github-actions[bot]'
          git config --global user.email 'github-actions[bot]@users.noreply.github.com'
          git add state.json
          if ! git diff --cached --quiet; then
            git commit -m "Update state.json with latest ad post times [skip ci]"
            git push
          else
            echo "No changes to state.json to commit."
          fi`,
    },
    "requirements.txt": {
      language: "text",
      description: "List of minimal Python requirements for the scheduler execution environment.",
      code: `requests>=2.28.0`,
    }
  };

  // Fetch configs from local express server API
  const fetchConfig = async () => {
    try {
      setLoading(true);
      const res = await fetch("/api/config");
      const data = await res.json();
      if (data.config) {
        setAds(data.config);
      }
      if (data.state) {
        setStateData(data.state);
      }
    } catch (e) {
      console.error("Failed to load server config:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchConfig();
  }, []);

  // Update config on the server
  const saveConfigToServer = async (updatedAds: Ad[]) => {
    try {
      const response = await fetch("/api/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(updatedAds),
      });
      const data = await response.json();
      if (data.config) {
        setAds(data.config);
      }
    } catch (e) {
      console.error("Failed to save config to server:", e);
      alert("Failed to save changes to server file.");
    }
  };

  // Save active channels list to the server
  const saveActiveChannelsToServer = async (updatedChannels: (string | number)[]) => {
    try {
      const response = await fetch("/api/active-channels", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ channels: updatedChannels }),
      });
      const data = await response.json();
      if (data.state) {
        setStateData(data.state);
      }
    } catch (e) {
      console.error("Failed to save active channels:", e);
    }
  };

  const handleAddChannel = () => {
    if (!newChannelInput.trim()) return;
    const currentChannels = stateData.active_channels || [];
    const normalizedInput = newChannelInput.trim();
    if (currentChannels.includes(normalizedInput)) {
      alert("Channel is already in the list!");
      return;
    }
    const updated = [...currentChannels, normalizedInput];
    saveActiveChannelsToServer(updated);
    setNewChannelInput("");
  };

  const handleRemoveChannel = (channelToRemove: string | number) => {
    if (confirm(`Remove channel ${channelToRemove} from the active list?`)) {
      const currentChannels = stateData.active_channels || [];
      const updated = currentChannels.filter(c => c !== channelToRemove);
      saveActiveChannelsToServer(updated);
    }
  };

  // Check Bot Token validity
  const handleTestConnection = async () => {
    setIsTestingBot(true);
    setBotTestResult(null);
    try {
      const response = await fetch(`https://api.telegram.org/bot${botToken}/getMe`);
      const data = await response.json();
      if (data.ok) {
        setBotTestResult({
          success: true,
          botName: `@${data.result.username} (${data.result.first_name})`
        });
      } else {
        setBotTestResult({
          success: false,
          error: data.description || "Invalid bot token format or rejected by Telegram."
        });
      }
    } catch (e: any) {
      setBotTestResult({
        success: false,
        error: e.message || "Failed to contact Telegram API. Check network connectivity."
      });
    } finally {
      setIsTestingBot(false);
    }
  };

  // Scan updates from Telegram Bot API
  const handleScanMedia = async () => {
    setIsScanning(true);
    setScanError(null);
    setScanSuccess(false);
    try {
      const response = await fetch(`/api/telegram-updates?token=${encodeURIComponent(botToken)}`);
      const data = await response.json();
      if (data.ok) {
        setScannedMedia(data.updates);
        setScanSuccess(true);
        if (data.updates.length === 0) {
          setScanError("Successfully connected, but no media messages (photos/GIFs) were found in your bot's recent 100 updates. Send a file to your bot first!");
        }
      } else {
        setScanError(data.error || "Failed to scan Telegram updates.");
      }
    } catch (e: any) {
      setScanError(e.message || "An unexpected error occurred during scan.");
    } finally {
      setIsScanning(false);
    }
  };

  // Trigger test-post for a specific ad
  const handleTestPostAd = async (ad: Ad) => {
    // Set loading state for this ad
    setAdTestStatus(prev => ({
      ...prev,
      [ad.id]: { loading: true }
    }));

    try {
      const response = await fetch("/api/test-post", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          token: botToken,
          channel: channelId,
          ad: ad
        })
      });

      const data = await response.json();
      if (response.ok && data.ok) {
        setAdTestStatus(prev => ({
          ...prev,
          [ad.id]: { loading: false, success: true }
        }));
        // Auto clear success indicator after 4 seconds
        setTimeout(() => {
          setAdTestStatus(prev => {
            const copy = { ...prev };
            delete copy[ad.id];
            return copy;
          });
        }, 4000);
      } else {
        setAdTestStatus(prev => ({
          ...prev,
          [ad.id]: { loading: false, success: false, error: data.error || "Telegram posting failed." }
        }));
      }
    } catch (e: any) {
      setAdTestStatus(prev => ({
        ...prev,
        [ad.id]: { loading: false, success: false, error: e.message || "Failed to send request." }
      }));
    }
  };

  // Trigger full scheduling step
  const handleRunScheduler = async () => {
    setIsRunningScheduler(true);
    setSchedulerSuccess(false);
    setSchedulerLogs(["Initiating local scheduler engine simulation...", "Connecting to Telegram..."]);
    
    try {
      const response = await fetch("/api/run-scheduler-step", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          token: botToken,
          channel: channelId
        })
      });

      const data = await response.json();
      if (data.success) {
        setSchedulerLogs(data.logs);
        setStateData(data.state);
        setSchedulerSuccess(true);
      } else {
        setSchedulerLogs(prev => [...prev, `❌ Error: ${data.error || "Failed to execute scheduler sequence"}`]);
      }
    } catch (e: any) {
      setSchedulerLogs(prev => [...prev, `❌ Network Exception: ${e.message || "Failed to contact local daemon"}`]);
    } finally {
      setIsRunningScheduler(false);
    }
  };

  // Open modal for editing or adding a new ad
  const openAdModal = (ad: Ad | null = null) => {
    if (ad) {
      setEditingAd(ad);
      setFormId(ad.id);
      setFormMediaType(ad.media_type);
      setFormFileId(ad.file_id);
      setFormCaption(ad.caption);
      setFormButtonText(ad.button_text || "");
      setFormButtonUrl(ad.button_url || "");
      setFormInterval(ad.interval_minutes);
    } else {
      setEditingAd(null);
      setFormId(`ad_${Date.now().toString().slice(-6)}`);
      setFormMediaType("photo");
      setFormFileId("");
      setFormCaption("");
      setFormButtonText("");
      setFormButtonUrl("");
      setFormInterval(60);
    }
    setFormError("");
    setIsModalOpen(true);
  };

  // Prepulate form with scanned media item
  const handleUseScannedMedia = (media: ScannedMedia) => {
    setEditingAd(null);
    setFormId(`ad_${Date.now().toString().slice(-6)}`);
    setFormMediaType(media.media_type);
    setFormFileId(media.file_id);
    setFormCaption(media.caption || "");
    setFormButtonText("Join Channel 🚀");
    setFormButtonUrl(channelId.startsWith("@") ? `https://t.me/${channelId.substring(1)}` : "https://t.me/FeaturesticLeaks");
    setFormInterval(120);
    setFormError("");
    setActiveTab("dashboard");
    setIsModalOpen(true);
  };

  // Save changes from Ad Form modal
  const handleSaveAd = () => {
    if (!formId.trim()) {
      setFormError("Ad ID is required.");
      return;
    }
    if (!formFileId.trim()) {
      setFormError("Telegram File ID is required. Use the Bot Updates Scanner to fetch one if needed!");
      return;
    }
    if (formInterval <= 0) {
      setFormError("Interval minutes must be greater than 0.");
      return;
    }
    if (formButtonText.trim() && !formButtonUrl.trim()) {
      setFormError("You specified button text but no URL. Please enter a destination URL.");
      return;
    }
    if (formButtonUrl.trim() && !formButtonUrl.startsWith("http://") && !formButtonUrl.startsWith("https://")) {
      setFormError("Inline button URL must start with http:// or https://");
      return;
    }

    // Check uniqueness if creating new
    if (!editingAd && ads.some(a => a.id === formId)) {
      setFormError(`An ad with the ID "${formId}" already exists. Please choose a unique ID.`);
      return;
    }

    const newAd: Ad = {
      id: formId.trim(),
      media_type: formMediaType,
      file_id: formFileId.trim(),
      caption: formCaption,
      interval_minutes: Number(formInterval),
      ...(formButtonText.trim() && { button_text: formButtonText.trim() }),
      ...(formButtonUrl.trim() && { button_url: formButtonUrl.trim() })
    };

    let updatedAds: Ad[];
    if (editingAd) {
      // Replace existing
      updatedAds = ads.map(a => a.id === editingAd.id ? newAd : a);
    } else {
      // Add new
      updatedAds = [...ads, newAd];
    }

    setAds(updatedAds);
    saveConfigToServer(updatedAds);
    setIsModalOpen(false);
  };

  // Delete an ad
  const handleDeleteAd = (adId: string) => {
    if (confirm(`Are you sure you want to delete ad '${adId}'?`)) {
      const updated = ads.filter(a => a.id !== adId);
      setAds(updated);
      saveConfigToServer(updated);

      // Clean up testing status
      setAdTestStatus(prev => {
        const copy = { ...prev };
        delete copy[adId];
        return copy;
      });
    }
  };

  // Copy helper
  const handleCopyToClipboard = (text: string, identifier: string) => {
    navigator.clipboard.writeText(text);
    setCopiedFile(identifier);
    setTimeout(() => {
      setCopiedFile(null);
    }, 2000);
  };

  // Format Unix timestamp relative time
  const formatTimeAgo = (timestampSeconds: number) => {
    if (!timestampSeconds) return "Never";
    const diff = (Date.now() / 1000) - timestampSeconds;
    if (diff < 60) return "Just now";
    const mins = Math.floor(diff / 60);
    if (mins < 60) return `${mins}m ago`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}h ${mins % 60}m ago`;
    return new Date(timestampSeconds * 1000).toLocaleString();
  };

  return (
    <div id="root-container" className="min-h-screen bg-[#0d1117] text-gray-200 font-sans selection:bg-teal-500 selection:text-black">
      {/* Top Header Navigation */}
      <header id="navbar" className="border-b border-gray-800 bg-[#161b22]/90 backdrop-blur sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="bg-teal-500/10 p-2 rounded-lg border border-teal-500/20 text-teal-400">
              <Bot className="w-6 h-6 animate-pulse" />
            </div>
            <div>
              <h1 className="text-lg font-semibold text-white tracking-tight flex items-center gap-2">
                Telegram Ad Posting Bot <span className="text-xs bg-teal-500/20 border border-teal-500/30 text-teal-400 font-normal px-2 py-0.5 rounded-full">Server Control Panel</span>
              </h1>
              <p className="text-xs text-gray-400">Automated scheduling via GitHub Actions</p>
            </div>
          </div>
          
          <nav className="flex space-x-1">
            <button
              onClick={() => setActiveTab("dashboard")}
              className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === "dashboard"
                  ? "bg-teal-500/15 text-teal-400 border border-teal-500/25"
                  : "text-gray-400 hover:text-white hover:bg-gray-800"
              }`}
            >
              Dashboard
            </button>
            <button
              onClick={() => setActiveTab("scanner")}
              className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-1.5 ${
                activeTab === "scanner"
                  ? "bg-teal-500/15 text-teal-400 border border-teal-500/25"
                  : "text-gray-400 hover:text-white hover:bg-gray-800"
              }`}
            >
              <Sparkles className="w-4 h-4" /> Media Scanner
            </button>
            <button
              onClick={() => setActiveTab("files")}
              className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === "files"
                  ? "bg-teal-500/15 text-teal-400 border border-teal-500/25"
                  : "text-gray-400 hover:text-white hover:bg-gray-800"
              }`}
            >
              File Explorer
            </button>
            <button
              onClick={() => setActiveTab("instructions")}
              className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === "instructions"
                  ? "bg-teal-500/15 text-teal-400 border border-teal-500/25"
                  : "text-gray-400 hover:text-white hover:bg-gray-800"
              }`}
            >
              Setup Guide
            </button>
          </nav>
        </div>
      </header>

      {/* Main Container */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        
        {/* Telegram Configuration Banner */}
        <section className="bg-gray-900 border border-gray-800 rounded-xl p-5 mb-8 shadow-xl">
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
            <div className="flex-1 w-full grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-gray-400 mb-1.5 uppercase tracking-wider">
                  Bot Token (TELEGRAM_BOT_TOKEN)
                </label>
                <div className="relative">
                  <Bot className="absolute left-3 top-2.5 w-5 h-5 text-gray-500" />
                  <input
                    type="password"
                    value={botToken}
                    onChange={(e) => {
                      setBotToken(e.target.value);
                      setBotTestResult(null);
                    }}
                    className="w-full pl-10 pr-3 py-2 bg-black border border-gray-800 rounded-lg text-sm font-mono text-white focus:outline-none focus:border-teal-500 transition-colors"
                    placeholder="Enter Telegram Bot Token"
                  />
                </div>
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-400 mb-1.5 uppercase tracking-wider">
                  Target Channel (TELEGRAM_CHANNEL_ID)
                </label>
                <div className="relative">
                  <span className="absolute left-3 top-2 text-gray-500 font-semibold select-none">ID</span>
                  <input
                    type="text"
                    value={channelId}
                    onChange={(e) => {
                      setChannelId(e.target.value);
                    }}
                    className="w-full pl-10 pr-3 py-2 bg-black border border-gray-800 rounded-lg text-sm font-mono text-white focus:outline-none focus:border-teal-500 transition-colors"
                    placeholder="e.g. @FeaturesticLeaks"
                  />
                </div>
              </div>
            </div>

            <div className="flex flex-col sm:flex-row gap-3 w-full md:w-auto self-end md:self-center">
              <button
                onClick={handleTestConnection}
                disabled={isTestingBot || !botToken}
                className="w-full sm:w-auto px-5 py-2.5 bg-gray-800 hover:bg-gray-750 text-white font-medium rounded-lg text-sm flex items-center justify-center gap-2 border border-gray-700 hover:border-gray-600 transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isTestingBot ? <RefreshCw className="w-4 h-4 animate-spin text-teal-400" /> : <Send className="w-4 h-4 text-gray-400" />}
                Test Bot
              </button>
            </div>
          </div>

          {/* Test connection output alert */}
          <AnimatePresence>
            {botTestResult && (
              <motion.div
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                className={`mt-4 p-3 rounded-lg text-sm flex items-center justify-between border ${
                  botTestResult.success 
                    ? "bg-teal-500/10 border-teal-500/20 text-teal-300" 
                    : "bg-rose-500/10 border-rose-500/20 text-rose-300"
                }`}
              >
                <div className="flex items-center gap-2.5">
                  {botTestResult.success ? (
                    <Check className="w-5 h-5 text-teal-400 shrink-0" />
                  ) : (
                    <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0" />
                  )}
                  <span>
                    {botTestResult.success ? (
                      <><strong>Connected successfully!</strong> Bot details: {botTestResult.botName}</>
                    ) : (
                      <><strong>Connection failed:</strong> {botTestResult.error}</>
                    )}
                  </span>
                </div>
                <button 
                  onClick={() => setBotTestResult(null)} 
                  className="text-gray-400 hover:text-white px-2 py-1 text-xs uppercase"
                >
                  Dismiss
                </button>
              </motion.div>
            )}
          </AnimatePresence>
        </section>


        {/* TAB 1: DASHBOARD */}
        {activeTab === "dashboard" && (
          <div className="space-y-8">
            
            {/* Header section of Dashboard */}
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <div>
                <h2 className="text-xl font-semibold text-white">Scheduled Ad Campaigns</h2>
                <p className="text-sm text-gray-400">Manage independent post times and inline CTA keyboard parameters.</p>
              </div>
              <div className="flex flex-wrap gap-3 w-full sm:w-auto">
                <button
                  onClick={handleRunScheduler}
                  disabled={isRunningScheduler}
                  className="px-4 py-2.5 bg-gradient-to-r from-teal-500/10 to-emerald-500/10 hover:from-teal-500/20 hover:to-emerald-500/20 text-teal-400 font-medium rounded-lg text-sm border border-teal-500/20 flex items-center justify-center gap-2 transition-all cursor-pointer disabled:opacity-50"
                >
                  <RefreshCw className={`w-4 h-4 ${isRunningScheduler ? "animate-spin" : ""}`} />
                  Run Scheduler Step
                </button>
                <button
                  onClick={() => openAdModal(null)}
                  className="px-4 py-2.5 bg-teal-500 hover:bg-teal-400 text-black font-semibold rounded-lg text-sm flex items-center justify-center gap-2 shadow-lg hover:shadow-teal-500/10 transition-all cursor-pointer"
                >
                  <Plus className="w-4 h-4" /> Add New Ad
                </button>
              </div>
            </div>

            {/* Scheduler Logs Panel */}
            <AnimatePresence>
              {schedulerLogs.length > 0 && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  className="bg-black border border-gray-800 rounded-xl overflow-hidden shadow-2xl"
                >
                  <div className="bg-gray-900 px-4 py-2.5 border-b border-gray-800 flex items-center justify-between">
                    <span className="text-xs font-semibold text-gray-400 flex items-center gap-2 font-mono">
                      <Terminal className="w-4 h-4 text-teal-400" />
                      LOCAL_RUN_DAEMON_OUTPUT
                    </span>
                    <button
                      onClick={() => setSchedulerLogs([])}
                      className="text-gray-500 hover:text-gray-300 text-xs font-mono"
                    >
                      CLEAR
                    </button>
                  </div>
                  <div className="p-4 font-mono text-xs text-emerald-400 space-y-1.5 max-h-60 overflow-y-auto">
                    {schedulerLogs.map((log, i) => (
                      <div key={i} className="leading-relaxed">
                        <span className="text-gray-600 select-none mr-2">[$]</span>
                        {log}
                      </div>
                    ))}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Active Channels Management */}
            <div className="bg-[#161b22] border border-gray-800 rounded-xl p-5 shadow-lg">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
                <div>
                  <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                    <Bot className="w-4 h-4 text-teal-400" />
                    Bot Administered Channels
                  </h3>
                  <p className="text-xs text-gray-400 mt-0.5">
                    The bot will automatically broadcast ads to all listed channels.
                  </p>
                </div>
                
                {/* Manual Add Input */}
                <div className="flex items-center gap-2 max-w-sm w-full sm:w-auto">
                  <input
                    type="text"
                    value={newChannelInput}
                    onChange={(e) => setNewChannelInput(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleAddChannel()}
                    placeholder="e.g. @MyNewChannel or -10012345"
                    className="flex-1 sm:w-48 px-2.5 py-1.5 bg-black border border-gray-800 rounded-lg text-xs font-mono text-white placeholder-gray-500 focus:outline-none focus:border-teal-500 transition-colors"
                  />
                  <button
                    onClick={handleAddChannel}
                    className="px-3 py-1.5 bg-teal-500 hover:bg-teal-400 text-black font-semibold rounded-lg text-xs flex items-center justify-center gap-1 shrink-0 cursor-pointer transition-colors"
                  >
                    <Plus className="w-3.5 h-3.5" /> Add
                  </button>
                </div>
              </div>

              {/* Channels List */}
              <div className="flex flex-wrap gap-2">
                {/* Primary Channel */}
                <div className="bg-teal-500/10 border border-teal-500/25 text-teal-300 px-3 py-1.5 rounded-full text-xs font-mono flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-teal-400 animate-ping" />
                  <span>{channelId} (Primary)</span>
                </div>

                {/* Other Dynamically Registered Channels */}
                {stateData.active_channels && stateData.active_channels.map((chan) => {
                  // Skip displaying primary channel if it's already in active_channels to avoid duplication
                  if (String(chan) === String(channelId)) return null;

                  return (
                    <div
                      key={chan}
                      className="bg-gray-800/60 border border-gray-700 hover:border-gray-600 text-gray-300 px-3 py-1.5 rounded-full text-xs font-mono flex items-center gap-2 group transition-colors"
                    >
                      <span>{chan}</span>
                      <button
                        onClick={() => handleRemoveChannel(chan)}
                        className="text-gray-500 hover:text-rose-400 font-bold transition-colors text-xs"
                        title="Remove Channel"
                      >
                        ✕
                      </button>
                    </div>
                  );
                })}

                {/* Help message if no other channels are active */}
                {(!stateData.active_channels || stateData.active_channels.filter(c => String(c) !== String(channelId)).length === 0) && (
                  <div className="text-xs text-gray-500 italic flex items-center gap-1.5 mt-1">
                    <Info className="w-3.5 h-3.5" />
                    <span>No other active channels linked yet. Simply add your bot as an admin to any other channel, and it will register automatically.</span>
                  </div>
                )}
              </div>
            </div>

            {/* Main Ads Grid */}
            {loading ? (
              <div className="flex flex-col items-center justify-center py-20 bg-gray-900/40 rounded-2xl border border-gray-800">
                <RefreshCw className="w-8 h-8 text-teal-400 animate-spin mb-3" />
                <p className="text-sm text-gray-400">Loading schedules and campaign configs...</p>
              </div>
            ) : ads.length === 0 ? (
              <div className="text-center py-16 bg-gray-900/30 rounded-2xl border border-dashed border-gray-800 max-w-2xl mx-auto px-4">
                <div className="bg-gray-800/50 p-4 rounded-full inline-block mb-4 text-gray-500">
                  <ImageIcon className="w-8 h-8" />
                </div>
                <h3 className="text-base font-semibold text-white mb-1">No Ads Configured</h3>
                <p className="text-sm text-gray-400 mb-6">Create your first ad campaign detailing intervals, media file_ids, and call-to-action buttons.</p>
                <button
                  onClick={() => openAdModal(null)}
                  className="px-5 py-2.5 bg-teal-500 hover:bg-teal-400 text-black font-semibold rounded-lg text-sm inline-flex items-center gap-2 cursor-pointer transition-all"
                >
                  <Plus className="w-4 h-4" /> Setup First Ad
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {ads.map((ad) => {
                  const lastPostedTime = stateData[ad.id];
                  const interval = ad.interval_minutes;
                  const elapsedSeconds = lastPostedTime ? (Date.now() / 1000 - lastPostedTime) : Infinity;
                  const elapsedMinutes = elapsedSeconds / 60;
                  const minutesLeft = Math.max(0, interval - elapsedMinutes);
                  const progressPercentage = Math.min(100, (elapsedMinutes / interval) * 100);

                  return (
                    <motion.div
                      layout
                      key={ad.id}
                      className="bg-[#161b22] border border-gray-800 rounded-xl overflow-hidden shadow-md flex flex-col justify-between"
                    >
                      {/* Top Ad Identification Bar */}
                      <div className="p-4 border-b border-gray-850 bg-gray-900/40 flex items-center justify-between gap-4">
                        <div className="flex items-center gap-2.5 min-w-0">
                          <span className={`p-1.5 rounded-lg shrink-0 ${
                            ad.media_type === "animation" 
                              ? "bg-indigo-500/10 text-indigo-400 border border-indigo-500/20" 
                              : "bg-teal-500/10 text-teal-400 border border-teal-500/20"
                          }`}>
                            {ad.media_type === "animation" ? <Video className="w-4 h-4" /> : <ImageIcon className="w-4 h-4" />}
                          </span>
                          <div className="min-w-0">
                            <h3 className="text-sm font-semibold text-white truncate font-mono">{ad.id}</h3>
                            <p className="text-xs text-gray-400 flex items-center gap-1">
                              <Clock className="w-3.5 h-3.5 text-gray-500" />
                              Runs every {ad.interval_minutes} minutes
                            </p>
                          </div>
                        </div>

                        <div className="flex items-center gap-1.5">
                          <button
                            onClick={() => openAdModal(ad)}
                            className="p-1.5 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg transition-colors cursor-pointer"
                            title="Edit Campaign Parameters"
                          >
                            <Edit className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => handleDeleteAd(ad.id)}
                            className="p-1.5 bg-gray-800/60 hover:bg-rose-500/25 text-rose-400 rounded-lg transition-colors cursor-pointer"
                            title="Delete Campaign"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </div>

                      {/* Middle Ad Content Details */}
                      <div className="p-5 flex-1 space-y-4">
                        {/* file_id preview box */}
                        <div className="bg-black/40 border border-gray-850 rounded-lg p-2.5 font-mono text-xs text-gray-400 flex items-center justify-between gap-3">
                          <span className="truncate">File ID: <span className="text-gray-300">{ad.file_id}</span></span>
                          <button
                            onClick={() => handleCopyToClipboard(ad.file_id, ad.id + "_fileid")}
                            className="text-teal-400 hover:text-white p-1 hover:bg-gray-800 rounded transition-colors"
                          >
                            {copiedFile === (ad.id + "_fileid") ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                          </button>
                        </div>

                        {/* Caption preview */}
                        <div>
                          <div className="text-xs text-gray-500 font-semibold mb-1 uppercase tracking-wider">Caption Preview (HTML Formatting Supported)</div>
                          <div className="bg-black/60 rounded-lg p-3 text-sm text-gray-300 font-sans border border-gray-850 whitespace-pre-wrap max-h-32 overflow-y-auto">
                            {ad.caption || <span className="text-gray-600 italic">No caption specified</span>}
                          </div>
                        </div>

                        {/* CTA button representation */}
                        {ad.button_text && ad.button_url && (
                          <div>
                            <div className="text-xs text-gray-500 font-semibold mb-1 uppercase tracking-wider">Inline Keyboard Layout</div>
                            <a
                              href={ad.button_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="w-full inline-flex items-center justify-center gap-1.5 bg-sky-500/10 hover:bg-sky-500/15 border border-sky-500/20 text-sky-400 text-xs font-semibold py-2 px-3 rounded-lg transition-colors"
                            >
                              {ad.button_text}
                              <ExternalLink className="w-3 h-3" />
                            </a>
                          </div>
                        )}
                      </div>

                      {/* Bottom Scheduler Progression Status */}
                      <div className="px-5 py-4 bg-gray-900/20 border-t border-gray-850">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-xs text-gray-400 font-mono">
                            Last Posted: <strong className="text-gray-300">{formatTimeAgo(lastPostedTime)}</strong>
                          </span>
                          <span className="text-xs text-teal-400 font-semibold">
                            {minutesLeft > 0 ? `${minutesLeft.toFixed(0)}m remaining` : "Eligible now"}
                          </span>
                        </div>

                        {/* Progress slider bar */}
                        <div className="w-full bg-gray-800 rounded-full h-1.5 overflow-hidden mb-4">
                          <div
                            className={`h-full rounded-full transition-all duration-500 ${
                              minutesLeft === 0 ? "bg-emerald-500" : "bg-teal-500"
                            }`}
                            style={{ width: `${progressPercentage}%` }}
                          />
                        </div>

                        {/* Action buttons */}
                        <div className="flex gap-2">
                          <button
                            onClick={() => handleTestPostAd(ad)}
                            disabled={adTestStatus[ad.id]?.loading}
                            className="flex-1 px-3 py-2 bg-teal-500/10 hover:bg-teal-500/15 border border-teal-500/20 text-teal-400 font-medium rounded-lg text-xs flex items-center justify-center gap-1.5 cursor-pointer disabled:opacity-50 transition-colors"
                          >
                            {adTestStatus[ad.id]?.loading ? (
                              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                            ) : (
                              <Send className="w-3.5 h-3.5" />
                            )}
                            Test Send Now
                          </button>
                        </div>

                        {/* Local ad post testing outputs */}
                        <AnimatePresence>
                          {adTestStatus[ad.id] && adTestStatus[ad.id].success !== undefined && (
                            <motion.div
                              initial={{ opacity: 0, height: 0 }}
                              animate={{ opacity: 1, height: "auto" }}
                              exit={{ opacity: 0, height: 0 }}
                              className={`mt-2 p-2 rounded text-xs border ${
                                adTestStatus[ad.id].success
                                  ? "bg-teal-500/10 border-teal-500/20 text-teal-300"
                                  : "bg-rose-500/10 border-rose-500/20 text-rose-300"
                              }`}
                            >
                              {adTestStatus[ad.id].success ? (
                                <span>✔ Posted successfully to {channelId}!</span>
                              ) : (
                                <span className="block truncate">❌ Error: {adTestStatus[ad.id].error}</span>
                              )}
                            </motion.div>
                          )}
                        </AnimatePresence>
                      </div>
                    </motion.div>
                  );
                })}
              </div>
            )}
          </div>
        )}


        {/* TAB 2: TELEGRAM BOT SCANNER */}
        {activeTab === "scanner" && (
          <div className="space-y-6">
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 shadow-xl">
              <h2 className="text-xl font-semibold text-white mb-1 flex items-center gap-2">
                <Sparkles className="text-teal-400 w-5 h-5" />
                Telegram Media file_id Scanner
              </h2>
              <p className="text-sm text-gray-400 mb-6">
                Avoid manual scripts! Scan messages directly sent to your bot to extract high-resolution image/GIF file_ids instantly.
              </p>

              <div className="bg-[#161b22] border border-gray-850 rounded-xl p-5 mb-6">
                <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
                  <Info className="w-4 h-4 text-sky-400" /> Instructions to Retrieve file_ids:
                </h3>
                <ul className="space-y-2.5 text-xs text-gray-300 pl-1 list-none">
                  <li className="flex items-start gap-2">
                    <span className="bg-teal-500/15 text-teal-400 font-semibold px-1.5 py-0.5 rounded shrink-0">1</span>
                    <span>Open Telegram, search for your bot username, and tap <strong>Start</strong>.</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="bg-teal-500/15 text-teal-400 font-semibold px-1.5 py-0.5 rounded shrink-0">2</span>
                    <span>Directly upload/send any <strong>Photo</strong> or <strong>GIF</strong> message to the bot.</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="bg-teal-500/15 text-teal-400 font-semibold px-1.5 py-0.5 rounded shrink-0">3</span>
                    <span>Click the <strong>Scan Bot Updates</strong> button below to parse updates and capture IDs.</span>
                  </li>
                </ul>
              </div>

              <div className="flex flex-col sm:flex-row gap-3">
                <button
                  onClick={handleScanMedia}
                  disabled={isScanning || !botToken}
                  className="px-5 py-3 bg-teal-500 hover:bg-teal-400 text-black font-semibold rounded-lg text-sm flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50 transition-all shadow-lg hover:shadow-teal-500/10"
                >
                  <RefreshCw className={`w-4 h-4 ${isScanning ? "animate-spin" : ""}`} />
                  Scan Bot Updates
                </button>
                {scannedMedia.length > 0 && (
                  <button
                    onClick={() => setScannedMedia([])}
                    className="px-4 py-3 bg-gray-800 hover:bg-gray-750 text-gray-300 rounded-lg text-sm border border-gray-700 hover:border-gray-600 transition-all cursor-pointer"
                  >
                    Clear Scanner Results
                  </button>
                )}
              </div>
            </div>

            {/* Error alerts */}
            <AnimatePresence>
              {scanError && (
                <motion.div
                  initial={{ opacity: 0, y: -8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -8 }}
                  className="bg-yellow-500/10 border border-yellow-500/20 text-yellow-300 p-4 rounded-xl text-sm"
                >
                  <div className="flex items-start gap-3">
                    <AlertTriangle className="w-5 h-5 text-yellow-400 shrink-0 mt-0.5" />
                    <div>
                      <h4 className="font-semibold mb-1">Scanner Report:</h4>
                      <p className="text-gray-300 leading-relaxed">{scanError}</p>
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Scanned Results List */}
            {scannedMedia.length > 0 && (
              <div className="space-y-4">
                <h3 className="text-base font-semibold text-white px-1">Detected Media ({scannedMedia.length} item{scannedMedia.length > 1 ? "s" : ""})</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {scannedMedia.map((media) => (
                    <div key={media.id} className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-4 flex flex-col justify-between shadow-md">
                      <div className="space-y-3">
                        {/* Sender info */}
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <span className="text-xs text-gray-500 font-mono block">{media.date}</span>
                            <span className="text-sm font-semibold text-white block">From: {media.senderName}</span>
                            <span className="text-xs text-teal-400 block font-mono">{media.username}</span>
                          </div>
                          <span className={`px-2.5 py-1 text-xs font-semibold rounded-full uppercase ${
                            media.media_type === "animation" 
                              ? "bg-indigo-500/15 text-indigo-400 border border-indigo-500/25" 
                              : "bg-teal-500/15 text-teal-400 border border-teal-500/25"
                          }`}>
                            {media.media_type}
                          </span>
                        </div>

                        {/* Technical details */}
                        <div className="bg-black/40 border border-gray-850 p-3 rounded-lg space-y-2">
                          <div className="text-xs text-gray-500 font-semibold uppercase tracking-wider">Extracted file_id:</div>
                          <div className="font-mono text-xs text-teal-300 break-all select-all select-none">
                            {media.file_id}
                          </div>
                          <div className="text-[10px] text-gray-500 font-mono">
                            Details: {media.details}
                          </div>
                        </div>

                        {/* Optional captured caption */}
                        {media.caption && (
                          <div className="text-xs bg-black/20 p-2.5 rounded border border-gray-850">
                            <span className="text-[10px] text-gray-500 font-semibold block uppercase mb-1">Attached Message Caption:</span>
                            <span className="text-gray-300 font-mono">{media.caption}</span>
                          </div>
                        )}
                      </div>

                      {/* Action buttons */}
                      <div className="flex gap-2 pt-2 border-t border-gray-850">
                        <button
                          onClick={() => handleCopyToClipboard(media.file_id, media.id)}
                          className="flex-1 px-3 py-2 bg-gray-800 hover:bg-gray-750 text-white font-medium rounded-lg text-xs flex items-center justify-center gap-1.5 cursor-pointer border border-gray-700 hover:border-gray-600 transition-all"
                        >
                          {copiedFile === media.id ? <Check className="w-4 h-4 text-teal-400" /> : <Copy className="w-4 h-4" />}
                          {copiedFile === media.id ? "Copied ID!" : "Copy File ID"}
                        </button>
                        <button
                          onClick={() => handleUseScannedMedia(media)}
                          className="flex-1 px-3 py-2 bg-teal-500 hover:bg-teal-400 text-black font-semibold rounded-lg text-xs flex items-center justify-center gap-1.5 cursor-pointer transition-all"
                        >
                          <Plus className="w-4 h-4" />
                          Use in Ad Config
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}


        {/* TAB 3: CODE FILES VIEW */}
        {activeTab === "files" && (
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
            
            {/* Left sidebar tab lists */}
            <div className="space-y-2">
              <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3 px-1">Source Repository Files</h3>
              {Object.keys(staticFiles).map((filename) => (
                <button
                  key={filename}
                  onClick={() => setCodeViewerTab(filename)}
                  className={`w-full text-left px-3.5 py-3 rounded-lg text-sm flex items-center justify-between transition-all border ${
                    codeViewerTab === filename
                      ? "bg-teal-500/10 text-teal-400 border-teal-500/20 font-medium"
                      : "text-gray-300 hover:text-white bg-gray-900 border-transparent hover:border-gray-800"
                  }`}
                >
                  <span className="flex items-center gap-2">
                    <FileCode className="w-4 h-4 shrink-0" />
                    {filename}
                  </span>
                  <ChevronRight className="w-4 h-4 opacity-50" />
                </button>
              ))}
            </div>

            {/* Right side file visual viewport */}
            <div className="lg:col-span-3 bg-black border border-gray-800 rounded-xl overflow-hidden shadow-2xl flex flex-col">
              
              {/* Top status bar of viewport */}
              <div className="bg-gray-900 px-5 py-3 border-b border-gray-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                  <span className="text-sm font-semibold text-white font-mono">{codeViewerTab}</span>
                  <p className="text-xs text-gray-400 mt-0.5">{staticFiles[codeViewerTab].description}</p>
                </div>
                <button
                  onClick={() => handleCopyToClipboard(staticFiles[codeViewerTab].code, codeViewerTab)}
                  className="px-3.5 py-1.5 bg-gray-800 hover:bg-gray-750 text-white rounded-lg text-xs font-medium flex items-center justify-center gap-1.5 border border-gray-700 transition-colors"
                >
                  {copiedFile === codeViewerTab ? <Check className="w-3.5 h-3.5 text-teal-400" /> : <Copy className="w-3.5 h-3.5" />}
                  {copiedFile === codeViewerTab ? "Copied!" : "Copy Code"}
                </button>
              </div>

              {/* Viewport code content */}
              <pre className="p-5 overflow-auto text-xs font-mono text-gray-300 bg-black max-h-[550px] leading-relaxed select-text">
                <code>
                  {staticFiles[codeViewerTab].code}
                </code>
              </pre>
            </div>
          </div>
        )}


        {/* TAB 4: SETUP GUIDE & TELEGRAM BOT INSTRUCTIONS */}
        {activeTab === "instructions" && (
          <div className="bg-[#161b22] border border-gray-800 rounded-xl overflow-hidden shadow-xl">
            <div className="bg-gray-900 px-6 py-5 border-b border-gray-800">
              <h2 className="text-lg font-semibold text-white">Full Installation & Setup Guide</h2>
              <p className="text-xs text-gray-400 mt-1">Follow these 5 simple steps to get your ad posting bot running forever for free via GitHub Actions.</p>
            </div>

            <div className="p-6 md:p-8 space-y-8 divide-y divide-gray-850">
              
              {/* Step 1 */}
              <div className="flex gap-4 md:gap-6 items-start pb-6">
                <div className="bg-teal-500/10 text-teal-400 text-sm font-bold w-10 h-10 rounded-full border border-teal-500/25 flex items-center justify-center shrink-0">
                  1
                </div>
                <div className="space-y-2">
                  <h3 className="text-base font-semibold text-white">Create your Bot via BotFather</h3>
                  <p className="text-sm text-gray-300 leading-relaxed">
                    Search for <strong>@BotFather</strong> on Telegram and send the <code>/newbot</code> command. 
                    Follow the prompts to name your bot and choose a username. Copy the long HTTP API token provided — this is your <strong>BOT_TOKEN</strong>.
                  </p>
                </div>
              </div>

              {/* Step 2 */}
              <div className="flex gap-4 md:gap-6 items-start pt-6 pb-6">
                <div className="bg-teal-500/10 text-teal-400 text-sm font-bold w-10 h-10 rounded-full border border-teal-500/25 flex items-center justify-center shrink-0">
                  2
                </div>
                <div className="space-y-2">
                  <h3 className="text-base font-semibold text-white">Promote Bot to Channel Admin</h3>
                  <p className="text-sm text-gray-300 leading-relaxed">
                    Go to your target Telegram Channel (e.g. <code>@FeaturesticLeaks</code>), open <strong>Channel Info</strong>, click <strong>Administrators</strong> &gt; <strong>Add Administrator</strong>, and search for your Bot's username. Ensure it has permissions to <strong>Post Messages</strong>.
                  </p>
                </div>
              </div>

              {/* Step 3 */}
              <div className="flex gap-4 md:gap-6 items-start pt-6 pb-6">
                <div className="bg-teal-500/10 text-teal-400 text-sm font-bold w-10 h-10 rounded-full border border-teal-500/25 flex items-center justify-center shrink-0">
                  3
                </div>
                <div className="space-y-2">
                  <h3 className="text-base font-semibold text-white">Acquire Telegram Media file_ids</h3>
                  <p className="text-sm text-gray-300 leading-relaxed">
                    Open Telegram and message your bot directly by sending the <strong>Photos</strong> or <strong>GIFs/Animations</strong> you want to use for ads.
                    Go back to our <span className="text-teal-400 font-semibold cursor-pointer" onClick={() => setActiveTab("scanner")}>Media Scanner</span> tab, input your Bot Token, and click <strong>Scan Bot Updates</strong> to fetch the file IDs instantly.
                  </p>
                </div>
              </div>

              {/* Step 4 */}
              <div className="flex gap-4 md:gap-6 items-start pt-6 pb-6">
                <div className="bg-teal-500/10 text-teal-400 text-sm font-bold w-10 h-10 rounded-full border border-teal-500/25 flex items-center justify-center shrink-0">
                  4
                </div>
                <div className="space-y-2">
                  <h3 className="text-base font-semibold text-white">Create GitHub Repository Secrets</h3>
                  <p className="text-sm text-gray-300 leading-relaxed">
                    Once you push or upload these files to your GitHub repository, navigate to the repo's <strong>Settings</strong> &gt; <strong>Secrets and variables</strong> &gt; <strong>Actions</strong> &gt; <strong>New repository secret</strong> and define:
                  </p>
                  <ul className="list-disc pl-5 text-xs text-gray-400 space-y-1.5 pt-1">
                    <li><strong>TELEGRAM_BOT_TOKEN</strong>: Paste your bot token here.</li>
                    <li><strong>TELEGRAM_CHANNEL_ID</strong>: Enter your target channel username starting with <code>@</code> (e.g. <code>@FeaturesticLeaks</code>) or numeric ID.</li>
                  </ul>
                </div>
              </div>

              {/* Step 5 */}
              <div className="flex gap-4 md:gap-6 items-start pt-6">
                <div className="bg-teal-500/10 text-teal-400 text-sm font-bold w-10 h-10 rounded-full border border-teal-500/25 flex items-center justify-center shrink-0">
                  5
                </div>
                <div className="space-y-2">
                  <h3 className="text-base font-semibold text-white">Continuous Runs & Manual Execution</h3>
                  <p className="text-sm text-gray-300 leading-relaxed">
                    The GitHub actions pipeline is configured to automatically trigger every <strong>10 minutes</strong> via GitHub cron. It will boot the scheduler, check intervals, post qualifying ads, and commit changes back to keep tracking active.
                    You can also trigger it manually at any time by visiting the repository's <strong>Actions</strong> tab, selecting <strong>Telegram Ad Poster</strong>, and clicking <strong>Run workflow</strong>.
                  </p>
                </div>
              </div>

            </div>
          </div>
        )}

      </main>

      {/* FOOTER */}
      <footer className="border-t border-gray-800 bg-[#0d1117] py-8 text-center text-xs text-gray-500 mt-16">
        <div className="max-w-7xl mx-auto px-4">
          <p>© 2026 Telegram Ad Posting Bot. Engineered with professional React, Express and GitHub Actions workflows.</p>
        </div>
      </footer>

      {/* AD CAMPAIGN ADD / EDIT MODAL */}
      <AnimatePresence>
        {isModalOpen && (
          <div className="fixed inset-0 z-50 overflow-y-auto bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="bg-[#161b22] border border-gray-800 rounded-xl w-full max-w-lg shadow-2xl overflow-hidden"
            >
              {/* Modal Header */}
              <div className="bg-gray-900 px-6 py-4 border-b border-gray-800 flex items-center justify-between">
                <h3 className="text-base font-semibold text-white">
                  {editingAd ? "Modify Ad Campaign Parameters" : "Setup New Ad Campaign"}
                </h3>
                <button
                  onClick={() => setIsModalOpen(false)}
                  className="text-gray-400 hover:text-white font-semibold text-sm"
                >
                  ✕
                </button>
              </div>

              {/* Modal Body / Form */}
              <div className="p-6 space-y-4 max-h-[75vh] overflow-y-auto text-sm">
                
                {formError && (
                  <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs font-semibold flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 text-rose-400" />
                    {formError}
                  </div>
                )}

                <div className="grid grid-cols-2 gap-4">
                  {/* ID field */}
                  <div>
                    <label className="block text-xs font-semibold text-gray-400 mb-1.5 uppercase">Ad Campaign ID</label>
                    <input
                      type="text"
                      disabled={!!editingAd}
                      value={formId}
                      onChange={(e) => setFormId(e.target.value.replace(/\s+/g, "_"))}
                      className="w-full px-3 py-2 bg-black border border-gray-800 rounded-lg text-xs font-mono text-white focus:outline-none focus:border-teal-500 transition-colors disabled:opacity-50"
                      placeholder="e.g. weekend_sale"
                    />
                  </div>

                  {/* Interval */}
                  <div>
                    <label className="block text-xs font-semibold text-gray-400 mb-1.5 uppercase">Interval (Minutes)</label>
                    <input
                      type="number"
                      value={formInterval}
                      onChange={(e) => setFormInterval(Math.max(1, parseInt(e.target.value) || 0))}
                      className="w-full px-3 py-2 bg-black border border-gray-800 rounded-lg text-xs font-mono text-white focus:outline-none focus:border-teal-500 transition-colors"
                      placeholder="60"
                    />
                  </div>
                </div>

                {/* Media type Selection */}
                <div>
                  <label className="block text-xs font-semibold text-gray-400 mb-1.5 uppercase">Media File Type</label>
                  <div className="grid grid-cols-2 gap-3">
                    <button
                      type="button"
                      onClick={() => setFormMediaType("photo")}
                      className={`py-2 px-3 rounded-lg text-xs font-semibold border flex items-center justify-center gap-2 transition-all cursor-pointer ${
                        formMediaType === "photo"
                          ? "bg-teal-500/10 text-teal-400 border-teal-500/30"
                          : "bg-black border-gray-800 text-gray-400 hover:text-white"
                      }`}
                    >
                      <ImageIcon className="w-4 h-4" /> Static Image (photo)
                    </button>
                    <button
                      type="button"
                      onClick={() => setFormMediaType("animation")}
                      className={`py-2 px-3 rounded-lg text-xs font-semibold border flex items-center justify-center gap-2 transition-all cursor-pointer ${
                        formMediaType === "animation"
                          ? "bg-indigo-500/10 text-indigo-400 border-indigo-500/30"
                          : "bg-black border-gray-800 text-gray-400 hover:text-white"
                      }`}
                    >
                      <Video className="w-4 h-4" /> Animated GIF (animation)
                    </button>
                  </div>
                </div>

                {/* Telegram File ID */}
                <div>
                  <label className="block text-xs font-semibold text-gray-400 mb-1.5 uppercase">Telegram file_id</label>
                  <input
                    type="text"
                    value={formFileId}
                    onChange={(e) => setFormFileId(e.target.value.trim())}
                    className="w-full px-3 py-2 bg-black border border-gray-800 rounded-lg text-xs font-mono text-white focus:outline-none focus:border-teal-500 transition-colors"
                    placeholder="Enter Telegram file_id (e.g. AgACAgIAAxkBAA...)"
                  />
                  <p className="text-[10px] text-gray-500 mt-1">
                    Tip: You can fetch file_ids directly by uploading files to your bot and scanning in our <strong>Media Scanner</strong> tab!
                  </p>
                </div>

                {/* Caption Form */}
                <div>
                  <label className="block text-xs font-semibold text-gray-400 mb-1.5 uppercase">Ad Caption Description (HTML)</label>
                  <textarea
                    value={formCaption}
                    onChange={(e) => setFormCaption(e.target.value)}
                    rows={4}
                    className="w-full px-3 py-2 bg-black border border-gray-800 rounded-lg text-xs text-white focus:outline-none focus:border-teal-500 transition-colors font-sans whitespace-pre-wrap"
                    placeholder="<b>Bold Head</b>&#10;&#10;Use <i>HTML</i> tag notation like &lt;b&gt;, &lt;i&gt;, or &lt;code&gt; for stylized Telegram text."
                  />
                </div>

                {/* CTA Button text & URL */}
                <div className="bg-black/40 border border-gray-850 p-4 rounded-xl space-y-3">
                  <span className="text-xs font-semibold text-gray-300 block uppercase tracking-wider">
                    Call-to-Action Inline Button (Optional)
                  </span>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="block text-[10px] text-gray-400 mb-1 uppercase">Button Text</label>
                      <input
                        type="text"
                        value={formButtonText}
                        onChange={(e) => setFormButtonText(e.target.value)}
                        className="w-full px-3 py-1.5 bg-black border border-gray-800 rounded-lg text-xs text-white focus:outline-none focus:border-teal-500 transition-colors"
                        placeholder="e.g. Join Channel 🚀"
                      />
                    </div>
                    <div>
                      <label className="block text-[10px] text-gray-400 mb-1 uppercase">Button Destination URL</label>
                      <input
                        type="text"
                        value={formButtonUrl}
                        onChange={(e) => setFormButtonUrl(e.target.value.trim())}
                        className="w-full px-3 py-1.5 bg-black border border-gray-800 rounded-lg text-xs font-mono text-white focus:outline-none focus:border-teal-500 transition-colors"
                        placeholder="https://t.me/..."
                      />
                    </div>
                  </div>
                </div>

              </div>

              {/* Modal Footer */}
              <div className="bg-gray-900 px-6 py-4 border-t border-gray-800 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 bg-gray-800 hover:bg-gray-750 text-white rounded-lg text-xs font-semibold transition-all cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleSaveAd}
                  className="px-4 py-2 bg-teal-500 hover:bg-teal-400 text-black font-semibold rounded-lg text-xs transition-all cursor-pointer"
                >
                  Save Campaign
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
