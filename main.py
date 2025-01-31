import requests
from flask import Flask, render_template, redirect, url_for, request
from urllib.parse import unquote
from bs4 import BeautifulSoup
from flask.views import MethodView
import logging

app = Flask(__name__, static_folder='static')

# ログの設定
logging.basicConfig(level=logging.DEBUG)

# 共通の設定
TARGET_TITLE = "ネコ"
INITIAL_CLICKS = 6
WIKI_API_URL = "https://ja.wikipedia.org/w/api.php"

# 除外するリンクのプレフィックスリスト
EXCLUDED_PREFIXES = [
    '/wiki/Special:',
    '/wiki/Help:',
    '/wiki/Category:',
    '/wiki/File:',
    '/wiki/Template:',
    '/wiki/Template_talk:',
    '/wiki/Portal:',
    '/wiki/Book:',
    '/wiki/Draft:',
    '/wiki/Education_Program:',
    '/wiki/TimedText:',
    '/wiki/Wikipedia:',
    '/wiki/MediaWiki:',
    '/wiki/Module:',
    '/wiki/Gadget:',
    '/wiki/Topic:'
]

def get_random_page():
    """
    ランダムなページタイトルを返すユーティリティ関数
    """
    params = {
        'action': 'query',
        'list': 'random',
        'rnlimit': 1,
        'rnnamespace': 0,
        'format': 'json'
    }
    try:
        response = requests.get(WIKI_API_URL, params=params)
        data = response.json()
        random_title = data['query']['random'][0]['title']
        return random_title
    except Exception as e:
        app.logger.error(f"get_random_page Error: {e}")
        # 失敗時はデフォルトでネコを返す
        return "ネコ"

class OpeningView(MethodView):
    def get(self):
        error = request.args.get('error', '')
        return render_template('opening.html', error=error)

class StartGameView(MethodView):
    def get(self):
        # difficulty をクエリストリングから取得
        difficulty = request.args.get('difficulty', 'easy')
        app.logger.debug(f"StartGameView: difficulty = {difficulty}")

        if difficulty == 'easy':
            # Easyならターゲットはネコ、スタートはランダム
            target_title = "ネコ"
            start_page = get_random_page()
        else:
            # Hardならターゲットもランダム、スタートもランダム
            target_title = get_random_page()
            start_page = get_random_page()

        # /game にリダイレクト
        # ターゲットを mytarget パラメータに乗せて、difficulty も一緒に渡す
        return redirect(url_for('game', page=start_page, clicks=INITIAL_CLICKS,
                                mytarget=target_title, difficulty=difficulty))

class ResetView(MethodView):
    def get(self):
        # 現在の difficulty をクエリから取得。無ければ easy
        difficulty = request.args.get('difficulty', 'easy')
        app.logger.debug(f"ResetView: difficulty={difficulty}")

        # 難易度によってターゲットとスタートページを決める
        if difficulty == 'hard':
            target_title = get_random_page()
            start_page = get_random_page()
        else:
            target_title = "ネコ"
            start_page = get_random_page()

        app.logger.debug(f"ResetView: start='{start_page}', target='{target_title}'")

        # クリック数をリセットして、/game に飛ばす
        return redirect(url_for('game', page=start_page, clicks=INITIAL_CLICKS,
                                mytarget=target_title, difficulty=difficulty))

class GameView(MethodView):
    def get(self):
        # difficultyに応じたターゲット切り替えのため、difficultyも受け取る
        difficulty = request.args.get('difficulty', 'easy')
        # デフォルトはネコ
        target_title = request.args.get('mytarget', TARGET_TITLE).strip()
        page_title = request.args.get('page', 'ネコ').strip()  # デフォルトは「ネコ」
        clicks_remaining = request.args.get('clicks', str(INITIAL_CLICKS))

        try:
            clicks_remaining = int(clicks_remaining)
        except ValueError:
            clicks_remaining = INITIAL_CLICKS

        app.logger.debug(
            f"GameView: page_title = '{page_title}', target_title = '{target_title}', clicks_remaining = {clicks_remaining}, difficulty={difficulty}")

        # ゲームクリア判定
        if page_title == target_title:
            app.logger.debug("GameView: Game Clear")
            return render_template('game_clear.html')

        # ゲームオーバー判定
        if clicks_remaining <= 0:
            app.logger.debug("GameView: Game Over")
            return redirect(url_for('game_over'))

        # ページ内容の取得
        params = {
            'action': 'parse',
            'page': page_title,
            'format': 'json',
            'prop': 'text',
            'redirects': 1
        }

        try:
            response = requests.get(WIKI_API_URL, params=params)
            data = response.json()

            if 'parse' not in data:
                raise KeyError("'parse' キーがレスポンスに存在しません。")

            parsed_html = data['parse']['text']['*']

            # リンク書き換え
            soup = BeautifulSoup(parsed_html, 'html.parser')
            for a in soup.find_all('a', href=True):
                link = a['href']
                if not link.startswith('/wiki/'):
                    continue

                if any(link.startswith(prefix) for prefix in EXCLUDED_PREFIXES):
                    continue

                title = link.replace('/wiki/', '')
                title = unquote(title).strip()

                if title == page_title:
                    continue

                new_clicks = clicks_remaining - 1

                if title == target_title:
                    # ターゲットページへのリンクはクリック数に関係なく飛べる
                    a['href'] = url_for('game', page=title, clicks=new_clicks,
                                        mytarget=target_title, difficulty=difficulty)
                elif new_clicks <= 0:
                    a['href'] = url_for('game_over')
                else:
                    a['href'] = url_for('game', page=title, clicks=new_clicks,
                                        mytarget=target_title, difficulty=difficulty)

            parsed_html = f'<div id="mw-content-text">{str(soup)}</div>'

        except KeyError as e:
            app.logger.error(f"GameView KeyError: {e}")
            parsed_html = f'<div id="mw-content-text"><p>エラーが発生しました: {str(e)}</p></div>'
        except Exception as e:
            app.logger.error(f"GameView Exception: {e}")
            parsed_html = f'<div id="mw-content-text"><p>エラーが発生しました: {str(e)}</p></div>'

        return render_template(
            'game.html',
            target_title=target_title,
            page_title=page_title,
            clicks_remaining=clicks_remaining,
            parsed_html=parsed_html,
            difficulty=difficulty
        )

class GameOverView(MethodView):
    def get(self):
        return render_template('game_over.html')

# ルート登録
app.add_url_rule('/', view_func=OpeningView.as_view('opening'))
app.add_url_rule('/start_game', view_func=StartGameView.as_view('start_game'))
app.add_url_rule('/reset', view_func=ResetView.as_view('reset'))
app.add_url_rule('/game', view_func=GameView.as_view('game'))
app.add_url_rule('/gameover', view_func=GameOverView.as_view('game_over'))

###########################
# Quick tests (basic)     #
###########################
# def run_tests():
#     print("Running tests...")
#     with app.test_client() as client:
#         # 1) Test the root (opening)
#         rv = client.get('/')
#         assert rv.status_code == 200, "Root / should return 200"
#         print("Test 1 passed: GET / => 200")
#
#         # 2) Test start_game (GET)
#         rv = client.get('/start_game')
#         assert rv.status_code in (200, 302), "start_game should redirect or succeed"
#         print("Test 2 passed: GET /start_game => OK (Redirect or 200)")
#
#         # 3) Test reset
#         rv = client.get('/reset')
#         assert rv.status_code in (200, 302), "reset should redirect"
#         print("Test 3 passed: GET /reset => OK (Redirect)")
#
#     print("All tests completed!")

if __name__ == '__main__':
    # run_tests()  # 必要があればテスト
    # debug=False, use_reloader=False で _multiprocessing エラーを回避
    app.run(debug=False, use_reloader=False)