import os, datetime
from notion_client import Client

JST = datetime.timezone(datetime.timedelta(hours=9))
now_str = datetime.datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S")

print("=== auto-sns orchestrator ===")
print(f"[JST] {now_str}")

token = os.environ.get("NOTION_TOKEN")
db_id = os.environ.get("NOTION_DB_ID_CONTENT")

# 親切チェック（トークンは先頭のみ表示、漏えい防止）
def short(s): 
    return (s[:8] + "…") if s else "None"

if not token or not token.startswith("secret_"):
    raise RuntimeError(f"NOTION_TOKEN が無効です（現在: {short(token)}）。"
                       " GitHub → Settings → Secrets で 'NOTION_TOKEN' をセットし、"
                       "workflow の env で渡しているか確認してください。")
if not db_id:
    raise RuntimeError("NOTION_DB_ID_CONTENT が未設定です。DBのURLからIDをコピーしてください。")

notion = Client(auth=token)

# DBアクセス確認（失敗時はIDか権限の問題）
try:
    notion.databases.retrieve(db_id)
    print("Notion DB retrieve: OK")
except Exception as e:
    raise RuntimeError("Notion DBにアクセスできません。"
                       "① DBの『…』→ Add connections でこのIntegrationを招待"
                       "② DB IDが正しいか（URLの英数字）を確認") from e

# テストで1行作成
resp = notion.pages.create(
    parent={"database_id": db_id},
    properties={
        "title": {"title": [{"text": {"content": f"Smoke {now_str}"}}]},
        # season/status が無いDBでも通るようにガード
    }
)
print("Notion write OK:", resp["id"])
