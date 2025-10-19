import os, datetime
from dotenv import load_dotenv
from notion_client import Client

load_dotenv()
JST = datetime.timezone(datetime.timedelta(hours=9))
now_str = datetime.datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S")

print("=== auto-sns orchestrator ===")
print(f"[JST] {now_str}")

notion = Client(auth=os.environ.get("NOTION_TOKEN"))
db_id = os.environ.get("NOTION_DB_ID_CONTENT")

resp = notion.pages.create(
    parent={"database_id": db_id},
    properties={
        "title": {"title": [{"text": {"content": f"Smoke {now_str}"}}]},
        "season": {"select": {"name": "秋"}},
        "status": {"select": {"name": "DRAFT"}},
    }
)
print("Notion write OK:", resp["id"])
