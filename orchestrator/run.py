import os, datetime, sys
from notion_client import Client
from notion_client.errors import APIResponseError

JST = datetime.timezone(datetime.timedelta(hours=9))
now_str = datetime.datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S")

def short(s): 
    return (s[:8] + "…") if s else "None"

print("=== auto-sns orchestrator (debug) ===")
print(f"[JST] {now_str}")

token = os.environ.get("NOTION_TOKEN")
db_id = os.environ.get("NOTION_DB_ID_CONTENT")

print(f"NOTION_TOKEN (prefix): {short(token)}")     # 先頭だけ
print(f"NOTION_DB_ID_CONTENT: {db_id}")

# 1) まず環境変数の有無チェック
if not token:
    print("NG: NOTION_TOKEN が空（Secrets未設定 or env渡し漏れ）", file=sys.stderr)
    sys.exit(1)
if not db_id or len(db_id) != 32:
    print("NG: NOTION_DB_ID_CONTENT がおかしい（32文字か、?v= 以降混入してないか）", file=sys.stderr)
    sys.exit(1)

# 2) Notionクライアント生成 & APIバージョン表示
notion = Client(auth=token)
print("Notion client OK")

# 3) DBにアクセスできるか → ここが失敗すると接続/権限ミス
try:
    meta = notion.databases.retrieve(db_id)
    print("DB retrieve OK: title =", meta.get("title", [{}])[0].get("plain_text", ""))
except APIResponseError as e:
    print(f"DB retrieve ERROR: status={e.status}, code={e.code}, msg={e.message}", file=sys.stderr)
    print("想定原因:")
    print("- 401: トークンが間違い or IntegrationがDBに未接続（Add connections未実施）")
    print("- 403: トークンは正しいが、そのDBに権限がない（Add connectionsの漏れ）")
    sys.exit(1)

# 4) 1行だけ作成テスト（titleプロパティがある前提）
try:
    resp = notion.pages.create(
        parent={"database_id": db_id},
        properties={ "title": {"title": [{"text": {"content": f"Smoke {now_str}"}}]} }
    )
    print("Notion write OK:", resp["id"])
except APIResponseError as e:
    print(f"Page create ERROR: status={e.status}, code={e.code}, msg={e.message}", file=sys.stderr)
    print("想定原因: titleプロパティ名の相違／DBがページでデータベースではない等")
    sys.exit(1)
