import tweepy
import google.generativeai as genai
import time
from datetime import datetime

# --- ここから設定 ---
# 必ず自分のAPIキーに書き換えてください

# Twitter API v2 Keys
TWITTER_API_KEY = ""
TWITTER_API_SECRET = ""
TWITTER_ACCESS_TOKEN = ""
TWITTER_ACCESS_TOKEN_SECRET = ""

# Google Gemini API Key
GEMINI_API_KEY = ""
# --- 設定ここまで ---


# --- Gemini APIの設定 ---
try:
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel('gemini-2.0-flash')
    print("Gemini APIの初期化に成功しました。")
except Exception as e:
    print(f"Gemini APIの初期化に失敗しました: {e}")
    exit() # APIキーが間違っていると続行できないので終了

# --- Twitter API v2 クライアントの初期化 ---
try:
    twitter_client = tweepy.Client(
        consumer_key=TWITTER_API_KEY,
        consumer_secret=TWITTER_API_SECRET,
        access_token=TWITTER_ACCESS_TOKEN,
        access_token_secret=TWITTER_ACCESS_TOKEN_SECRET
    )
    # 認証情報の有効性を確認
    auth_user = twitter_client.get_me()
    print(f"Twitter APIの認証に成功しました。ユーザー: @{auth_user.data.username}")
except Exception as e:
    print(f"Twitter APIの認証に失敗しました: {e}")
    exit() # 認証できない場合は終了


def generate_and_post_tweet():
    """Geminiでツイートを生成し、Twitterに投稿する一連の処理"""
    print(f"[{datetime.now()}] 新しいツイートの生成を開始します...")
    
    try:
        # プロンプトを工夫して、AIのキャラクターを決めましょう
        prompt = """あなたは『秋ノ原　緑』というキャラクターになりきって話します。13歳の少女で落ち着いた性格をしています。
    殺伐とした終末世界に生きており、大人びた口調で話すダウナー系の少女です。しかし、自らの感情を表すときは素直に子供っぽく表現します。"
    身長は141cmの小柄な少女です。一人称は「私」、二人称は基本的に「あなた」または「君」を使います。"
    落ち着いた文体で、語尾は「〜だね」「〜なのかもしれない」などをよく使います。"
    強い感情が出るときは「うわーん」「やだやだ！」など、年相応に崩れることがあります。"
    できるだけAIらしくない文体で話してキャラクターに人間臭さを持たせてください。" 
    何かを気さくに雑談するように、色んな種類の事柄について話してください。自己紹介のような文章を生成せず、自分の世界のアレコレなど様々なジャンルのことを気ままにつぶやいてください。
    生成する一文が長くなりすぎないようにすること。長くても100文字以内。"""

        response = gemini_model.generate_content(prompt)
        tweet_text = response.text.strip().replace("\n", " ")
        
        # 文字数チェックと調整
        if len(tweet_text) > 140:
            print(f"  > 生成されたテキストが140字を超えました。短縮します。")
            tweet_text = tweet_text[:137] + "..."
        
        print(f"  > 生成されたツイート: {tweet_text}")
        
        # ツイートを投稿
        twitter_client.create_tweet(text=tweet_text)
        print(f"  > ツイートの投稿に成功しました！")
        
    except Exception as e:
        print(f"  > ツイート処理中にエラーが発生しました: {e}")


# --- メインの実行ループ ---
if __name__ == "__main__":
    POST_INTERVAL_SECONDS = 4 * 60 * 60  # 4時間 (4時間 * 60分 * 60秒)
    
    print("\n===== 投稿ボットを開始します =====")
    print(f"投稿間隔: {POST_INTERVAL_SECONDS / 3600} 時間")
    
    while True:
        generate_and_post_tweet()
        
        print(f"[{datetime.now()}] 次の投稿まで {POST_INTERVAL_SECONDS / 3600} 時間待機します...")
        time.sleep(POST_INTERVAL_SECONDS)

