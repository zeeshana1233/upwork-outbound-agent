/**
 * MERIDIAN WhatsApp Bridge
 * Thin Express server wrapping Baileys (@whiskeysockets/baileys).
 *
 * First run: prints a QR code — scan with WhatsApp on your phone.
 * Session is saved to ./session/ and survives restarts.
 *
 * API:
 *   POST /send
 *   Body: { "group_jid": "120363...", "message": "Hello!" }
 *
 *   GET /status
 *   Returns: { "connected": true|false, "groups": [...] }
 *
 * Incoming command (WhatsApp group message):
 *   "agree <job_number>"  →  triggers proposal draft generation
 *   e.g. "agree 7"        →  generates draft for Job #7
 *
 * Setup:
 *   npm install
 *   node server.js
 */

const {
  default: makeWASocket,
  useMultiFileAuthState,
  DisconnectReason,
  fetchLatestBaileysVersion,
  makeInMemoryStore,
} = require("@whiskeysockets/baileys");

const express   = require("express");
const qrcode    = require("qrcode-terminal");
const pino      = require("pino");
const path      = require("path");
const fs        = require("fs");
const http      = require("http");

// ─── Config ──────────────────────────────────────────────────
const PORT              = process.env.WA_BRIDGE_PORT || 3001;
const SESSION_DIR       = path.join(__dirname, "session");
const DRAFT_SERVER_PORT = process.env.DRAFT_SERVER_PORT || 8765;  // Python draft endpoint
const WA_GROUP_JID      = process.env.WA_GROUP_JID || "";         // only listen to this group
const logger            = pino({ level: "silent" }); // suppress Baileys verbose logs

// ─── State ───────────────────────────────────────────────────
let sock        = null;
let isConnected = false;
let knownGroups = [];

// ─── Express app ─────────────────────────────────────────────
const app = express();
app.use(express.json());

/** POST /send — send a message to a WhatsApp group */
app.post("/send", async (req, res) => {
  const { group_jid, message } = req.body || {};

  if (!group_jid || !message) {
    return res.status(400).json({ error: "group_jid and message are required" });
  }
  if (!isConnected || !sock) {
    return res.status(503).json({ error: "WhatsApp not connected yet" });
  }

  try {
    await sock.sendMessage(group_jid, { text: message });
    console.log(`[WA Bridge] Sent to ${group_jid}: ${message.slice(0, 60)}...`);
    return res.json({ ok: true });
  } catch (err) {
    console.error("[WA Bridge] Send error:", err.message);
    return res.status(500).json({ error: err.message });
  }
});

/** GET /status — check connection status + available group JIDs */
app.get("/status", (req, res) => {
  res.json({ connected: isConnected, groups: knownGroups });
});

app.listen(PORT, () => {
  console.log(`[WA Bridge] HTTP server listening on port ${PORT}`);
});

// ─── Outgoing command: call Python draft server ───────────────
/**
 * triggerDraftGeneration(jobNumber)
 * POSTs to the Python bot's draft HTTP server to kick off proposal generation.
 */
function triggerDraftGeneration(jobNumber) {
  const body = JSON.stringify({ job_number: jobNumber });
  const options = {
    hostname: "127.0.0.1",
    port:     DRAFT_SERVER_PORT,
    path:     "/draft",
    method:   "POST",
    headers:  {
      "Content-Type":   "application/json",
      "Content-Length": Buffer.byteLength(body),
    },
  };

  const req = http.request(options, (res) => {
    let data = "";
    res.on("data", (chunk) => { data += chunk; });
    res.on("end",  () => {
      console.log(`[WA Bridge] Draft server responded ${res.statusCode}: ${data.slice(0, 80)}`);
    });
  });

  req.on("error", (e) => {
    console.error(`[WA Bridge] Could not reach draft server (is the Python bot running?): ${e.message}`);
  });

  req.write(body);
  req.end();
}

// ─── Incoming message handler ─────────────────────────────────
/**
 * Handle incoming WA messages and look for the "agree <N>" command.
 * Only acts on messages from the configured WA_GROUP_JID.
 */
function handleIncomingMessage(msg) {
  try {
    // Only process text messages from the monitored group
    const fromJid = msg.key.remoteJid || "";
    const isGroup = fromJid.endsWith("@g.us");
    if (!isGroup) return;

    // If WA_GROUP_JID is set, only listen to that specific group
    if (WA_GROUP_JID && fromJid !== WA_GROUP_JID) return;

    // Ignore messages sent by this bot itself
    if (msg.key.fromMe) return;

    const text = (
      msg.message?.conversation ||
      msg.message?.extendedTextMessage?.text ||
      ""
    ).trim().toLowerCase();

    // Match: "agree <number>"  e.g. "agree 7" or "agree7"
    const match = text.match(/^agree\s*(\d+)$/);
    if (!match) return;

    const jobNumber = parseInt(match[1], 10);
    if (isNaN(jobNumber) || jobNumber < 1) return;

    console.log(`[WA Bridge] Received 'agree ${jobNumber}' — triggering draft generation`);
    triggerDraftGeneration(jobNumber);

  } catch (e) {
    // Non-fatal — never crash the bridge over a bad message
    console.warn("[WA Bridge] handleIncomingMessage error:", e.message);
  }
}

// ─── Baileys socket ──────────────────────────────────────────
async function startWhatsApp() {
  if (!fs.existsSync(SESSION_DIR)) {
    fs.mkdirSync(SESSION_DIR, { recursive: true });
  }

  const { version } = await fetchLatestBaileysVersion();
  const { state, saveCreds } = await useMultiFileAuthState(SESSION_DIR);

  sock = makeWASocket({
    version,
    logger,
    printQRInTerminal: false, // we'll print it ourselves below
    auth: state,
    browser: ["MERIDIAN Bot", "Chrome", "1.0"],
    generateHighQualityLinkPreview: false,
    syncFullHistory: false,
  });

  // Save credentials whenever they update
  sock.ev.on("creds.update", saveCreds);

  // ── Listen for incoming messages ──────────────────────────
  sock.ev.on("messages.upsert", ({ messages, type }) => {
    if (type !== "notify") return;
    for (const msg of messages) {
      handleIncomingMessage(msg);
    }
  });

  // Handle connection lifecycle
  sock.ev.on("connection.update", async (update) => {
    const { connection, lastDisconnect, qr } = update;

    if (qr) {
      console.log("\n[WA Bridge] Scan the QR code below with WhatsApp:\n");
      qrcode.generate(qr, { small: true });
      console.log("\nOpen WhatsApp → Settings → Linked Devices → Link a Device\n");
    }

    if (connection === "open") {
      isConnected = true;
      console.log("[WA Bridge] ✅ WhatsApp connected!");
      console.log(`[WA Bridge] Listening for 'agree <N>' commands from group: ${WA_GROUP_JID || "(all groups)"}`);

      // List available groups so user can find their group JID
      try {
        const groups = await sock.groupFetchAllParticipating();
        knownGroups = Object.entries(groups).map(([jid, g]) => ({
          jid,
          name: g.subject,
        }));
        if (knownGroups.length > 0) {
          console.log("\n[WA Bridge] Available groups (set WA_GROUP_JID in .env):");
          knownGroups.forEach((g) =>
            console.log(`  JID: ${g.jid}   Name: "${g.name}"`)
          );
          console.log("");
        } else {
          console.log("[WA Bridge] No group chats found. Add the phone to a group first.");
        }
      } catch (e) {
        console.warn("[WA Bridge] Could not fetch groups:", e.message);
      }
    }

    if (connection === "close") {
      isConnected = false;
      const code    = lastDisconnect?.error?.output?.statusCode;
      const reason  = Object.keys(DisconnectReason).find(
        (k) => DisconnectReason[k] === code
      ) || code;

      if (code === DisconnectReason.loggedOut) {
        console.log("[WA Bridge] Logged out. Deleting session, please restart and scan QR again.");
        fs.rmSync(SESSION_DIR, { recursive: true, force: true });
        process.exit(1);
      } else {
        console.log(`[WA Bridge] Disconnected (${reason}). Reconnecting in 5s...`);
        setTimeout(startWhatsApp, 5000);
      }
    }
  });
}

startWhatsApp().catch((err) => {
  console.error("[WA Bridge] Fatal startup error:", err);
  process.exit(1);
});
