import tweepy
import google.generativeai as genai
import time
import os
import subprocess
import json
from datetime import datetime

# --- ここから設定 ---

# Twitter API v2 Keys (返信用アカウントのもの)
TWITTER_API_KEY = ""
TWITTER_API_SECRET = ""
TWITTER_ACCESS_TOKEN = ""
TWITTER_ACCESS_TOKEN_SECRET = ""

# Google Gemini API Key
GEMINI_API_KEY = ""

# ★★★ 投稿用アカウントのユーザー名（@は不要） ★★★
# Geminiにキャラクター設定を伝えるために使います
TARGET_USERNAME_TO_CHECK = "YOUR_TARGET_USERNAME" 

# スクリーンショットを保存するファイル名
SCREENSHOT_FILE = "scrcpy_window.png"

# 二重返信を防ぐために、返信した相手のユーザー名とリプライ内容を記録するファイル
REPLIED_LOG_FILE = "replied_log.txt"

# --- 設定ここまで ---


# --- APIクライアントとモデルの初期化 ---
try:
    # Gemini
    genai.configure(api_key=GEMINI_API_KEY)
    vision_model = genai.GenerativeModel('gemini-2.0-flash')
    text_model = genai.GenerativeModel('gemini-2.0-flash')
    print("Gemini APIの初期化に成功しました。")

    # Twitter
    twitter_client = tweepy.Client(
        consumer_key=TWITTER_API_KEY,
        consumer_secret=TWITTER_API_SECRET,
        access_token=TWITTER_ACCESS_TOKEN,
        access_token_secret=TWITTER_ACCESS_TOKEN_SECRET
    )
    auth_user = twitter_client.get_me()
    print(f"Twitter APIの認証に成功しました。返信元アカウント: @{auth_user.data.username}")
except Exception as e:
    print(f"APIの初期化中にエラーが発生しました: {e}")
    exit()


def capture_scrcpy_window():
    """scrcpyのウィンドウをターゲットにしてスクリーンショットを撮影する"""
    print("Capturing scrcpy window...")
    try:
        # 'scrot'コマンドでフォーカスされているウィンドウを撮影し、ファイルに保存
        # -u (または --focused) オプションを使います
        # 実行前にscrcpyのウィンドウをクリックしてフォーカスしておく必要があります
# ★★★ ここを書き換える ★★★
        # 'gnome-screenshot' を使ってフォーカスされているウィンドウを撮影
        # -w: ウィンドウモード, -f: ファイル名を指定
        subprocess.run(["gnome-screenshot", "-w", "-f", SCREENSHOT_FILE], check=True)
        print(f"Screenshot saved as {SCREENSHOT_FILE}")
        return True
    except FileNotFoundError:
        # エラーメッセージもgnome-screenshot用に変えておくと親切
        print("Error: 'gnome-screenshot' command not found. It should be installed by default on Ubuntu.")
        return False
    except subprocess.CalledProcessError as e:
        print(f"Failed to capture screenshot. Make sure a window is focused. Error: {e}")
        return False

def analyze_screenshot():
    """スクリーンショット画像をGeminiで分析し、リプライ情報を抽出する"""
    if not os.path.exists(SCREENSHOT_FILE):
        print("Screenshot file not found.")
        return None

    print("Analyzing image with Gemini Vision...")
    try:
        from PIL import Image # Pillowライブラリをインポート
        img = Image.open(SCREENSHOT_FILE)
        
        prompt = """
        このTwitterアプリの通知画面のスクリーンショットから、新しい未読のリプライ（メンション）をすべて抽出してください。
        以下のJSON形式で、リプライを送信したユーザーの「@」で始まるユーザー名と、リプライの全文をリストとして返してください。
        「いいね」やリツイート、フォローの通知は無視してください。また、@YOUR_TARGET_USERNAMEというidと「example」という名前のユーザーは返信先のユーザーのidではないのでこれも無視すること。リプライのみを対象とします。
        もし有効なリプライがなければ、空のリスト `[]` を返してください。

        [
          { "username": "@user_example_1", "text": "これがリプライのテキストです。" },
          { "username": "@another_user_2", "text": "素敵なツイートですね！" }
        ]
        """
        
        response = vision_model.generate_content([prompt, img])
        
        # Geminiからの返答はマークダウンで囲まれていることがあるので、それを取り除く
        clean_response = response.text.strip().replace("```json", "").replace("```", "").strip()
        print(f"Analysis result (raw): {clean_response}")
        return clean_response
    except Exception as e:
        print(f"Failed to analyze image with Gemini: {e}")
        return None

def load_replied_log():
    """返信済みログをファイルから読み込む"""
    if not os.path.exists(REPLIED_LOG_FILE):
        return set()
    with open(REPLIED_LOG_FILE, "r") as f:
        # ユーザー名とテキストを結合したものをキーとして保存
        return set(line.strip() for line in f)

def save_to_replied_log(username, text):
    """返信済みログをファイルに追記する"""
    log_entry = f"{username}|{text}"
    with open(REPLIED_LOG_FILE, "a") as f:
        f.write(log_entry + "\n")

def process_and_reply():
    """一連の処理（撮影→分析→返信）を実行する"""
    # 1. scrcpyウィンドウを撮影
    if not capture_scrcpy_window():
        return

    # 2. 画像を分析してリプライ情報を抽出
    mentions_json = analyze_screenshot()
    if not mentions_json:
        return

    # 3. 抽出した情報をもとに返信
    try:
        mentions = json.loads(mentions_json)
        if not mentions:
            print("No new valid mentions found in the analysis.")
            return
            
        replied_log = load_replied_log()
            
        for mention in mentions:
            username = mention.get("username")
            original_text = mention.get("text")
            
            if not username or not original_text:
                continue
            
            # 二重返信チェック
            log_key = f"{username}|{original_text}"
            if log_key in replied_log:
                print(f"Skipping already replied mention from {username}")
                continue

            print(f"Generating reply for {username}...")
            reply_prompt = f""" あなたは『秋ノ原 緑』というキャラクターのAIです。
            秋ノ原 緑（@{TARGET_USERNAME_TO_CHECK}）へのリプライ「{original_text}」に対して、あなたが代わりに返信してください。13歳の少女で落ち着いた性格をしています。
            殺伐とした終末世界に生きており、大人びた口調で話すダウナー系の少女です。しかし、自らの感情を表すときは素直に子供っぽく表現します。"
            身長は141cmの小柄な少女です。一人称は「私」、二人称は基本的に「あなた」または「君」を使います。"
            落ち着いた文体で、語尾は「〜だね」「〜なのかもしれない」などをよく使います。"
            強い感情が出るときは「うわーん」「やだやだ！」など、年相応に崩れることがあります。"
            できるだけAIらしくない文体で話してキャラクターに人間臭さを持たせてください。" 
                  生成する一文が長くなりすぎないようにすること。長くても100文字以内。
            """
            
            response = text_model.generate_content(reply_prompt)
            # 生成したテキストの先頭に@ユーザー名を追加してメンションにする
            reply_text = f"{username} {response.text.strip()}"
            
            # 文字数チェック
            if len(reply_text) > 140:
                reply_text = reply_text[:137] + "..."

            print(f"Posting reply: {reply_text}")
            twitter_client.create_tweet(text=reply_text)
            
            # 返信済みとしてログに記録
            save_to_replied_log(username, original_text)
            
            time.sleep(15) # API制限と連続投稿を避ける

    except json.JSONDecodeError:
        print(f"Failed to parse JSON from Vision API. Response was: {mentions_json}")
    except Exception as e:
        print(f"An error occurred during reply processing: {e}")

# --- メインの実行ループ ---
if __name__ == "__main__":
    INTERVAL_SECONDS = 60 * 60  # 1時間

    print("\n===== scrcpy Reply Bot Started =====")
    print(f"Check interval: {INTERVAL_SECONDS / 3600} hours")
    
    while True:
        print(f"\n--- {datetime.now()} ---")
        # 実行前にscrcpyウィンドウにフォーカスを当てるための時間
        print("Please focus the scrcpy window within 5 seconds...")
        time.sleep(5)
        
        process_and_reply()
        
        print(f"Waiting for {INTERVAL_SECONDS / 60} minutes for the next cycle...")
        time.sleep(INTERVAL_SECONDS)
