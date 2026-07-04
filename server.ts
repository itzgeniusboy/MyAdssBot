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

      let url = `https://api.telegram.org/bot${token}/sendPhoto`;
      let payload: any = {
        chat_id: channel,
        photo: file_id,
        caption: caption || "",
        parse_mode: "HTML",
      };

      if (media_type === "animation") {
        url = `https://api.telegram.org/bot${token}/sendAnimation`;
        payload = {
          chat_id: channel,
          animation: file_id,
          caption: caption || "",
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
        res.json({ ok: true, message: "Ad posted successfully for testing!", telegram_response: data.result });
      } else {
        res.status(400).json({ error: data.description || "Telegram rejected the post request." });
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

    logs.push(`Scheduler step triggered at ${new Date().toLocaleString()}`);
    logs.push(`Loaded ${config.length} configured ads.`);

    for (const ad of config) {
      const adId = ad.id;
      const intervalMinutes = ad.interval_minutes || 120;
      const lastPosted = state[adId] || 0;
      const elapsedMinutes = (currentTime - lastPosted) / 60.0;

      logs.push(`Ad '${adId}': Elapsed: ${elapsedMinutes.toFixed(1)} mins, Required Interval: ${intervalMinutes} mins`);

      if (elapsedMinutes >= intervalMinutes) {
        logs.push(`Ad '${adId}' is eligible. Posting...`);
        try {
          const reply_markup = ad.button_text && ad.button_url ? {
            inline_keyboard: [[{ text: ad.button_text, url: ad.button_url }]]
          } : null;

          let url = `https://api.telegram.org/bot${token}/sendPhoto`;
          let payload: any = {
            chat_id: channel,
            photo: ad.file_id,
            caption: ad.caption || "",
            parse_mode: "HTML",
          };

          if (ad.media_type === "animation") {
            url = `https://api.telegram.org/bot${token}/sendAnimation`;
            payload = {
              chat_id: channel,
              animation: ad.file_id,
              caption: ad.caption || "",
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
            state[adId] = currentTime;
            stateUpdated = true;
            logs.push(`✅ Ad '${adId}' posted successfully!`);
          } else {
            logs.push(`❌ Ad '${adId}' failed: ${data.description}`);
          }
        } catch (e: any) {
          logs.push(`❌ Exception during Ad '${adId}': ${e.message}`);
        }
      } else {
        const remaining = intervalMinutes - elapsedMinutes;
        logs.push(`Skipping ad '${adId}' (${remaining.toFixed(1)} mins left)`);
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
