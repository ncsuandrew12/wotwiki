import json
import os
import pathlib

cfg_dir = os.getenv("WOTWIKI_BOT_CFG_DIR", pathlib.Path.home() / ".wotwiki-bot")
cfg_json = {
    "secrets": "secrets.json"
}
cfg_path = os.getenv("WOTWIKI_BOT_DISCORD_CFG_PATH", "wotwiki.json")
if not cfg_path.startswith("/"):
    cfg_path = os.path.join(cfg_dir, cfg_path)
with open(cfg_path, "r") as f:
    cfg_json = json.load(f)
secrets_json = {}
if "secrets" in cfg_json:
    secrets_path = cfg_json["secrets"]
    if not secrets_path.startswith("/"):
        secrets_path = os.path.join(cfg_dir, secrets_path)
    with open(secrets_path, "r") as f:
        secrets_json = json.load(f)