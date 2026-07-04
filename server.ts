import express from "express";
import path from "path";
import fs from "fs";
import { fileURLToPath } from "url";
import { createServer as createViteServer } from "vite";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function startServer() {
  const app = express();
  const PORT = 3000;

  // Middleware
  app.use(express.json());

  const CONFIG_FILE = path.join(process.cwd(), "ads_config.json");
  const STATE_FILE = path.join(process.cwd(), "state.json");

  // Helper to load files safely
  const loadJsonFile = (filePath: string, defaultValue: any) => {
    if (!fs.existsSync(filePath)) {
      return defaultValue;
    }
    try {
      const data = fs.readFileSync(filePath, "utf-8");
      return JSON.parse(data);
    } catch (e) {
      console.error(`Error reading ${filePath}:`, e);
      return defaultValue;
    }
  };

  // Helper to save files safely
  const saveJsonFile = (filePath: string, data: any) => {
    try {
      fs.writeFileSync(filePath, JSON.stringify(data, null, 2), "utf-8");
      return true;
    } catch (e) {
      console.error(`Error writing ${filePath}:`, e);
      return false;
    }
  };

  // Helper to force bold and blockquote formatting
  const formatCaptionAsQuoteAndBold = (caption: string): string => {
    if (!caption) return "";
    let clean = caption.trim();
    
    // Strip outer <b> and </b>
    while (clean.startsWith("<b>") && clean.endsWith("</b>")) {
      clean = clean.substring(3, clean.length - 4).trim();
    }
    while (clean.startsWith("<strong>") && clean.endsWith("</strong>")) {
      clean = clean.substring(8, clean.length - 9).trim();
    }
    
    // Remove spoiler and blockquote tags
    clean = clean.replace(/<\/?tg-spoiler>/g, "");
    clean = clean.replace(/<span\s+class=["']tg-spoiler["']>/g, "");
    clean = clean.replace(/<\/?blockquote>/g, "");
    clean = clean.replace(/<\/span>/g, "");
    
    return `<blockquote><b>${clean.trim()}</b></blockquote>`;
  };

  // ==========================================
  // API ENDPOINTS
  // ==========================================

  // 1. Get configurations and state
  app.get("/api/config", (req, res) => {
    const config = loadJsonFile(CONFIG_FILE, []);
    const state = loadJsonFile(STATE_FILE, {});
    res.json({ config, state });
  });

  // 2. Save/Update configurations (ads list)
  app.post("/api/config", (req, res) => {
    const newConfig = req.body;
    if (!Array.isArray(newConfig)) {
      return res.status(400).json({ error: "Invalid configuration. Must be an array of ads." });
    }
    const success = saveJsonFile(CONFIG_FILE, newConfig);
    if (success) {
      res.json({ message: "Configuration saved successfully", config: newConfig });
    } else {
      res.status(500).json({ error: "Failed to write configuration file." });
    }
  });

  // 2b. Save/Update active channels list in state.json
  app.post("/api/active-channels", (req, res) => {
    const { channels } = req.body;
    if (!Array.isArray(channels)) {
      return res.status(400).json({ error: "Channels must be an array." });
    }
    
    const state = loadJsonFile(STATE_FILE, {});
    state.active_channels = channels;
    const success = saveJsonFile(STATE_FILE, state);
    
    if (success) {
      res.json({ message: "Active channels updated successfully", state });
    } else {
      res.status(500).json({ error: "Failed to write state file." });
    }
  });

  // 3. Scan for recent Telegram Updates
  app.get("/api/telegram-updates", async (req, res) => {
    const token = req.query.token as string;
    if (!token) {
      return res.status(400).json({ error: "Bot token is required as a query parameter." });
    }

    try {
      const telegramUrl = `https://api.telegram.org/bot${token}/getUpdates?limit=100&allowed_updates=["message"]`;
      const response = await fetch(telegramUrl);
      const data: any = await response.json();

      if (!data.ok) {
        return res.status(400).json({ error: data.description || "Telegram API returned an error." });
      }

      const updates = data.result || [];
      const mediaList: any[] = [];

      // Scan for media files in updates, going backwards (latest first)
      for (const update of [...updates].reverse()) {
        const message = update.message;
        if (!message) continue;

        const sender = message.from || {};
        const senderName = `${sender.first_name || ""} ${sender.last_name || ""}`.trim() || "Anonymous";
        const username = sender.username ? `@${sender.username}` : "No username";
        const date = new Date(message.date * 1000).toLocaleString();
        const msgId = message.message_id;

        if (message.photo && message.photo.length > 0) {
          const largestPhoto = message.photo[message.photo.length - 1];
          mediaList.push({
            id: `msg_${msgId}_photo`,
            media_type: "photo",
            file_id: largestPhoto.file_id,
            caption: message.caption || "",
            senderName,
            username,
            date,
            msgId,
            details: `${largestPhoto.width}x${largestPhoto.height} pixels`,
          });
        } else if (message.animation) {
          mediaList.push({
            id: `msg_${msgId}_animation`,
            media_type: "animation",
            file_id: message.animation.file_id,
            caption: message.caption || "",
            senderName,
            username,
            date,
            msgId,
            details: message.animation.file_name || "GIF animation",
          });
        } else if (message.document) {
          const doc = message.document;
          const mime = doc.mime_type || "";
          if (mime.startsWith("image/gif") || mime.startsWith("video/")) {
            mediaList.push({
              id: `msg_${msgId}_doc_gif`,
              media_type: "animation",
              file_id: doc.file_id,
              caption: message.caption || "",
              senderName,
              username,
              date,
              msgId,
              details: `${doc.file_name || "GIF"} (${mime})`,
            });
          }
        }
      }

      res.json({ ok: true, updates: mediaList });
    } catch (e: any) {
      console.error("Error fetching Telegram updates:", e);
      res.status(500).json({ error: e.message || "Failed to scan Telegram updates." });
    }
  });

  // 4. Test post an ad immediately
  app.post("/api/test-post", async (req, res) => {
    const { token, channel, ad } = req.body;

    if (!token || !channel || !ad) {
      return res.status(400).json({ error: "Missing required fields: token, channel, or ad." });
    }

    const { file_id, media_type, caption, button_text, button_url } = ad;
    if (!file_id) {
      return res.status(400).json({ error: "Ad is missing file_id." });
    }

    try {
      const reply_markup = button_text && button_url ? {
        inline_keyboard: [[{ text: button_text, url: button_url }]]
      } : null;

      const formattedCaption = formatCaptionAsQuoteAndBold(caption || "");
      
      // Load all active channels where the bot is admin
      const state = loadJsonFile(STATE_FILE, {});
      let activeChannels = state.active_channels || [];
      if (!Array.isArray(activeChannels)) {
        activeChannels = [];
      }
      
      // Ensure the user-inputted primary channel is also included in the broadcast
      const channelsToPost = [...activeChannels];
      const primaryStr = String(channel);
      const primaryNum = Number(channel);
      const hasPrimary = channelsToPost.some(c => String(c) === primaryStr || (typeof c === "number" && c === primaryNum));
      if (!hasPrimary) {
        channelsToPost.unshift(channel);
      }

      const results = [];
      let successCount = 0;
      let lastError = "";

      for (const chan of channelsToPost) {
        let url = `https://api.telegram.org/bot${token}/sendPhoto`;
        let payload: any = {
          chat_id: chan,
          photo: file_id,
          caption: formattedCaption,
          parse_mode: "HTML",
        };

        if (media_type === "animation") {
          url = `https://api.telegram.org/bot${token}/sendAnimation`;
          payload = {
            chat_id: chan,
            animation: file_id,
            caption: formattedCaption,
            parse_mode: "HTML",
          };
        }

        if (reply_markup) {
          payload.reply_markup = JSON.stringify(reply_markup);
        }

        try {
          const response = await fetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
          });

          const data: any = await response.json();
          if (data.ok) {
            successCount++;
            results.push({ channel: chan, success: true });
          } else {
            results.push({ channel: chan, success: false, error: data.description });
            lastError = data.description;
          }
        } catch (chanErr: any) {
          results.push({ channel: chan, success: false, error: chanErr.message });
          lastError = chanErr.message;
        }
      }

      if (successCount > 0) {
        res.json({ 
          ok: true, 
          message: `Ad posted successfully to ${successCount}/${channelsToPost.length} channel(s)!`, 
          results 
        });
      } else {
        res.status(400).json({ error: lastError || "Telegram rejected the post request for all channels.", results });
      }
    } catch (e: any) {
      console.error("Error test posting ad:", e);
      res.status(500).json({ error: e.message || "Failed to submit test post to Telegram." });
    }
  });

  // 5. Run scheduler step manually
  app.post("/api/run-scheduler-step", async (req, res) => {
    const { token, channel } = req.body;
    if (!token || !channel) {
      return res.status(400).json({ error: "Token and Channel are required." });
    }

    const config = loadJsonFile(CONFIG_FILE, []);
    const state = loadJsonFile(STATE_FILE, {});
    const currentTime = Date.now() / 1000; // in seconds
    const logs: string[] = [];
    let stateUpdated = false;

    // Load active channels
    let activeChannels = state.active_channels || [];
    if (!Array.isArray(activeChannels)) {
      activeChannels = [];
    }
    
    // Ensure primary channel is in the active list
    const channelsToPost = [...activeChannels];
    const primaryStr = String(channel);
    const primaryNum = Number(channel);
    const hasPrimary = channelsToPost.some(c => String(c) === primaryStr || (typeof c === "number" && c === primaryNum));
    if (!hasPrimary) {
      channelsToPost.unshift(channel);
    }

    // Ensure channel_states dictionary exists
    if (!state.channel_states || typeof state.channel_states !== "object") {
      state.channel_states = {};
    }

    logs.push(`Scheduler step triggered at ${new Date().toLocaleString()}`);
    logs.push(`Loaded ${config.length} configured ads. Checking for ${channelsToPost.length} channel(s)...`);

    for (const chan of channelsToPost) {
      const chanStr = String(chan);
      if (!state.channel_states[chanStr] || typeof state.channel_states[chanStr] !== "object") {
        state.channel_states[chanStr] = {};
      }
      const chanState = state.channel_states[chanStr];

      logs.push(`--- Checking Channel: ${chanStr} ---`);

      for (const ad of config) {
        const adId = ad.id;
        const intervalMinutes = ad.interval_minutes || 120;
        
        // Fallback to general timestamp if channel-specific state isn't populated yet
        const lastPosted = chanState[adId] || state[adId] || 0;
        const elapsedMinutes = (currentTime - lastPosted) / 60.0;

        logs.push(`Ad '${adId}': Elapsed: ${elapsedMinutes.toFixed(1)} mins, Required Interval: ${intervalMinutes} mins`);

        if (elapsedMinutes >= intervalMinutes) {
          logs.push(`Ad '${adId}' is eligible for ${chanStr}. Posting...`);
          try {
            const reply_markup = ad.button_text && ad.button_url ? {
              inline_keyboard: [[{ text: ad.button_text, url: ad.button_url }]]
            } : null;

            const formattedCaption = formatCaptionAsQuoteAndBold(ad.caption || "");
            let url = `https://api.telegram.org/bot${token}/sendPhoto`;
            let payload: any = {
              chat_id: chan,
              photo: ad.file_id,
              caption: formattedCaption,
              parse_mode: "HTML",
            };

            if (ad.media_type === "animation") {
              url = `https://api.telegram.org/bot${token}/sendAnimation`;
              payload = {
                chat_id: chan,
                animation: ad.file_id,
                caption: formattedCaption,
                parse_mode: "HTML",
              };
            }

            if (reply_markup) {
              payload.reply_markup = JSON.stringify(reply_markup);
            }

            const response = await fetch(url, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify(payload),
            });

            const data: any = await response.json();
            if (data.ok) {
              chanState[adId] = currentTime;
              state[adId] = currentTime; // update fallback as well
              stateUpdated = true;
              logs.push(`✅ Ad '${adId}' posted successfully to ${chanStr}!`);
            } else {
              logs.push(`❌ Ad '${adId}' failed for ${chanStr}: ${data.description}`);
            }
          } catch (e: any) {
            logs.push(`❌ Exception during Ad '${adId}' for ${chanStr}: ${e.message}`);
          }
        } else {
          const remaining = intervalMinutes - elapsedMinutes;
          logs.push(`Skipping ad '${adId}' on ${chanStr} (${remaining.toFixed(1)} mins left)`);
        }
      }
    }

    if (stateUpdated) {
      saveJsonFile(STATE_FILE, state);
      logs.push(`Saved updated scheduler timestamps to state.json`);
    } else {
      logs.push(`No ads were posted, state.json was not modified.`);
    }

    res.json({ success: true, logs, state });
  });

  // ==========================================
  // VITE & STATIC FILE SERVING
  // ==========================================

  if (process.env.NODE_ENV !== "production") {
    // Development Mode
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    // Production Mode
    const distPath = path.join(process.cwd(), "dist");
    app.use(express.static(distPath));
    app.get("*", (req, res) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`Server running on http://localhost:${PORT}`);
  });
}

startServer();
