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

// ─── Config ──────────────────────────────────────────────────
const PORT         = process.env.WA_BRIDGE_PORT || 3001;
const SESSION_DIR  = path.join(__dirname, "session");
const logger       = pino({ level: "silent" }); // suppress Baileys verbose logs

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
