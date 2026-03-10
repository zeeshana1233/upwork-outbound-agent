"""
Uploads the local WhatsApp Baileys session folder to the Windows server via SFTP.
Run with: .venv/bin/python copy_wa_session.py
"""
import paramiko
import getpass
import os

HOST = "38.242.198.21"
USER = "root"
LOCAL_SESSION = os.path.join(os.path.dirname(__file__), "whatsapp_bridge", "session")
REMOTE_DIR = "C:/upwork-outbound-agent/whatsapp_bridge/session"

password = getpass.getpass(f"SSH password for {USER}@{HOST}: ")

print("Connecting...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=22, username=USER, password=password, timeout=15)
sftp = ssh.open_sftp()

# Create remote session dir if it doesn't exist
try:
    sftp.stat(REMOTE_DIR)
    print("Remote session dir already exists.")
except FileNotFoundError:
    _, stdout, _ = ssh.exec_command(
        f'powershell -Command "New-Item -ItemType Directory -Force -Path \'{REMOTE_DIR}\'"'
    )
    stdout.channel.recv_exit_status()
    print(f"Created remote dir: {REMOTE_DIR}")

files = [f for f in os.listdir(LOCAL_SESSION) if os.path.isfile(os.path.join(LOCAL_SESSION, f))]
print(f"Uploading {len(files)} session files...")

for i, fname in enumerate(files, 1):
    local_path = os.path.join(LOCAL_SESSION, fname)
    remote_path = REMOTE_DIR + "/" + fname
    sftp.put(local_path, remote_path)
    print(f"  [{i}/{len(files)}] {fname}")

sftp.close()
ssh.close()
print("\nAll done! WA session copied to server.")
print("Now start the bridge on the server: node C:\\upwork-outbound-agent\\whatsapp_bridge\\server.js")
