import os, datetime
from dotenv import load_dotenv

load_dotenv()

JST = datetime.timezone(datetime.timedelta(hours=9))
now = datetime.datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S")

print("=== auto-sns orchestrator ===")
print(f"[JST] {now}")
print("step1: スモークテストOK（Actionsが動いてログが出ていれば成功）")
