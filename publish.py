import yaml
import datetime
import requests
import os

# タイムゾーンを日本時間に設定
JST = datetime.timezone(datetime.timedelta(hours=9))
now = datetime.datetime.now(JST)

# 設定ファイルの読み込み
with open('articles.yaml', 'r') as f:
    articles = yaml.safe_load(f)

# 投稿対象の記事を抽出
targets = []
for a in articles:
    # すでに公開済みのものはスキップ
    if a.get('status') == 'published':
        continue
    
    # 文字列の時間を比較可能なdatetimeオブジェクトに変換
    publish_time = datetime.datetime.strptime(a['publish_at'], "%Y-%m-%d %H:%M").replace(tzinfo=JST)
    
    # 指定時刻を過ぎていたら候補に入れる
    if now >= publish_time:
        targets.append(a)

if not targets:
    print("投稿対象の記事はありません。")
    exit()

# 優先度(priority)が高い順（数値が小さい順、あるいは大きい順）にソート
# 例：priority 1 を最優先にする場合
targets.sort(key=lambda x: x.get('priority', 99))

# Qiita API用の設定
QIITA_TOKEN = os.environ['QIITA_TOKEN']
headers = {
    "Authorization": f"Bearer {QIITA_TOKEN}",
    "Content-Type": "application/json"
}

# 投稿処理
for article in targets:
    url = f"https://qiita.com/api/v2/items/{article['id']}"
    
    # 1. 現在の記事の情報をGETで取得する
    get_res = requests.get(url, headers=headers)
    if get_res.status_code != 200:
        print(f"失敗: 記事情報が取得できませんでした (ID: {article['id']}) - {get_res.text}")
        continue
        
    current_data = get_res.json()
    
    # 2. 公開に必要なパラメータを組み立てる
    # (既存のタイトルや本文、タグを引き継ぎつつ、privateをfalseにする)
    update_payload = {
        "title": current_data["title"],
        "body": current_data["body"],
        "tags": current_data["tags"],
        "private": False
    }
    
    # 3. PATCHで公開状態に更新する
    res = requests.patch(url, headers=headers, json=update_payload)
    
    if res.status_code == 200:
        print(f"成功: {article['title']} (ID: {article['id']}) を公開しました。")
        article['status'] = 'published' # ステータスを更新
        article['published_actual_at'] = now.strftime("%Y-%m-%d %H:%M:%S")
    else:
        print(f"失敗: {article['title']} (ID: {article['id']}) - {res.text}")

# 状態を保存してyamlを上書き（この後GitHub Actions側でGit Pushする）
with open('articles.yaml', 'w') as f:
    yaml.safe_dump(articles, f, allow_unicode=True)
