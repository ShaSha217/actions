import os, datetime, json, subprocess, tempfile, pathlib, uuid
from notion_client import Client

JST = datetime.timezone(datetime.timedelta(hours=9))
now = datetime.datetime.now(JST)
now_str = now.strftime("%Y-%m-%d %H:%M:%S")

def log(*a): print("[auto-sns]", *a)

# === ENV ===
NOTION_TOKEN = os.environ["NOTION_TOKEN"]
DB_ID = os.environ["NOTION_DB_ID_CONTENT"]
PUBLISH_DRY = os.environ.get("PUBLISH_DRY_RUN","true").lower()=="true"

# === Notion helpers ===
notion = Client(auth=NOTION_TOKEN)

def find_status_prop(db_id: str):
    """DBのプロパティから、DRAFTオプションを持つ 'status' 型 or 'select' 型のプロパティを探す"""
    meta = notion.databases.retrieve(db_id)
    for name, info in meta["properties"].items():
        ptype = info.get("type")
        if ptype not in ("status", "select"):
            continue
        opts = info.get(ptype, {}).get("options", [])
        opt_names = {o.get("name") for o in opts}
        if "DRAFT" in opt_names:
            return name, ptype
    # 見つからなければ None
    return None, None

def get_one_draft():
    prop_name, prop_type = find_status_prop(DB_ID)
    if not prop_name:
        # フォールバック：フィルターなしで1行返す（初期構築用）
        return notion.databases.query(database_id=DB_ID, page_size=1).get("results", [None])[0]

    # status型なら {"status": {...}}、select型なら {"select": {...}}
    cond_key = "status" if prop_type == "status" else "select"
    q = notion.databases.query(
        database_id=DB_ID,
        filter={"property": prop_name, cond_key: {"equals": "DRAFT"}},
        page_size=1
    )
    results = q.get("results", [])
    return results[0] if results else None


def set_status(page_id, status_value):
    prop_name, prop_type = find_status_prop(DB_ID)
    if not prop_name:
        # プロパティが無ければ何もしない（初期構築フォールバック）
        return
    key = "status" if prop_type == "status" else "select"
    notion.pages.update(page_id, properties={prop_name: {key: {"name": status_value}}})

def set_props(page_id, props):
    notion.pages.update(page_id, properties=props)

def prop_text(txt): return {"rich_text":[{"type":"text","text":{"content":txt}}]}

# === Content generation (秋・紅葉テンプレ) ===
HOOKS = [
  "東京から1時間で行ける紅葉名所！",
  "夜の紅葉が一番映える庭園は？",
  "日帰りで楽しむ秋の絶景ドライブ！"
]
CAPTION_TMPL = (
  "秋の紅葉スポットガイド🍁\n"
  "・ベスト時間: {best_time}\n"
  "・アクセス: {access}\n"
  "・ひとこと: {tip}\n\n"
  "保存して秋の予定に！"
)
HASH_JP = "#紅葉 #秋旅行 #日本旅行 #映えスポット #週末おでかけ"
HASH_EN = "#JapanAutumn #FallInJapan #TravelJapan"

def generate_from_row(row):
    props = row["properties"]
    spot = props.get("spot",{}).get("rich_text",[{"plain_text":""}])[0]["plain_text"] if props.get("spot") else ""
    area = props.get("area",{}).get("rich_text",[{"plain_text":""}])[0]["plain_text"] if props.get("area") else ""
    best_time = props.get("best_time",{}).get("rich_text",[{"plain_text":"午前中"}])[0]["plain_text"] if props.get("best_time") else "午前中"

    hook = HOOKS[hash(spot)%len(HOOKS)] if spot else HOOKS[0]
    title = f"{area}・{spot}｜秋の紅葉スポット" if spot else "秋の紅葉スポット"
    caption = CAPTION_TMPL.format(best_time=best_time, access=f"{area}から電車/車で便利", tip="混雑回避は朝イチ")
    hashtags = f"{HASH_JP} {HASH_EN}"

    script_lines = [
      f"HOOK: {hook}",
      f"VALUE: 見頃は{best_time}。撮影は0-3秒のフックを意識！",
      "POINT: 池や橋など“映り込み”がある場所は写真映え◎",
      "CTA: 保存して秋の予定に！"
    ]
    script = "\n".join(script_lines)
    return title, caption, hashtags, script

# === Dummy video (FFmpeg) ===
def make_dummy_video(title:str) -> str:
    # 9:16 (1080x1920), 6秒のカラースレートにテキストを載せる
    out = pathlib.Path(tempfile.gettempdir())/f"{uuid.uuid4().hex}.mp4"
    # drawtext は runner にフォントがなくてもデフォで動くケースが多い（Ubuntuのsans互換）
    cmd = [
        "ffmpeg","-y",
        "-f","lavfi","-i","color=c=#101010:s=1080x1920:d=6,format=yuv420p",
        "-vf", f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='{title}':x=(w-tw)/2:y=(h/2-50):fontsize=64:fontcolor=white",
        "-pix_fmt","yuv420p","-r","30", str(out)
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return str(out)

# === Publisher stubs ===
def publish_instagram(video_path:str, caption:str):
    if PUBLISH_DRY:
        log("IG DRY-RUN: would post", video_path)
        return {"id":"dry_ig"}
    # 実線化時：/me/media → /me/media_publish を叩く
    raise NotImplementedError("IG real publish not yet wired")

def publish_youtube(video_path:str, title:str, description:str):
    if PUBLISH_DRY:
        log("YT DRY-RUN: would post", video_path, title)
        return {"id":"dry_yt"}
    # 実線化時：OAuthでvideos.insert
    raise NotImplementedError("YT real publish not yet wired")

# === Main ===
def main():
    log("JST", now_str)
    row = get_one_draft()
    if not row:
        log("No DRAFT rows. Nothing to do.")
        return
    page_id = row["id"]
    set_status(page_id,"QC")  # 取りかかりフラグ

    title, caption, hashtags, script = generate_from_row(row)
    set_props(page_id, {
        "script_jp": prop_text(script),
        "hashtags_jp": prop_text(hashtags),
        "title": {"title":[{"text":{"content": title}}]}
    })

    vid = make_dummy_video(title)
    log("video generated:", vid)

    # ドライラン投稿（本番化は環境変数で切替）
    ig = publish_instagram(vid, f"{caption}\n\n{hashtags}")
    yt = publish_youtube(vid, title, f"{caption}\n\n{hashtags}")
    log("publish results:", ig, yt)

    set_status(page_id,"SCHEDULED" if PUBLISH_DRY else "DONE")
    log("DONE (status updated)")

if __name__=="__main__":
    main()
