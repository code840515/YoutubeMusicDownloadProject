# 引入必要的函式庫
import os
import shutil
import re
from flask import Flask, request, jsonify, render_template
from yt_dlp import YoutubeDL
from pydub import AudioSegment
from pydub.effects import speedup

app = Flask(__name__)

# 設定下載路徑
DOWNLOAD_PATH = os.path.join(os.getcwd(), 'downloaded_music')

@app.route('/')
def index():
    """
    渲染主頁面。
    """
    return render_template('index.html')

@app.route('/download_to_server', methods=['POST'])
def download_to_server():
    """
    處理單一下載任務，將檔案直接儲存到伺服器。
    """
    data = request.json

    # 確保有傳送單一任務資料
    if not data or 'url' not in data or 'filename' not in data:
        return jsonify({'error': '無效的下載任務資料'}), 400

    url = data.get('url')
    filename = data.get('filename')
    speed = data.get('speed', 1.0)

    # 確保下載資料夾存在
    if not os.path.exists(DOWNLOAD_PATH):
        os.makedirs(DOWNLOAD_PATH)

    try:
        # 下載選項設定，僅下載最佳音訊
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            }],
        }

        # 從 URL 中移除播放清單參數，確保只下載單一影片
        url = re.sub(r"&list=.*", "", url)
        url = re.sub(r"&start_radio=.*", "", url)

        print(f'正在下載: {filename} (連結: {url})')

        # 創建一個暫存目錄來下載單一檔案
        temp_dir = 'temp_download'
        os.makedirs(temp_dir, exist_ok=True)
        ydl_opts['outtmpl'] = os.path.join(temp_dir, f'{filename}.%(ext)s')

        # 使用 yt-dlp 進行下載
        try:
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
        except Exception as e:
            print(f'下載 {filename} 失敗: {e}')
            return jsonify({'error': f'下載 {filename} 失敗: {e}'}), 500

        # 尋找下載的音訊檔案
        downloaded_files = [f for f in os.listdir(temp_dir) if f.startswith(filename) and f.endswith('.mp3')]
        if not downloaded_files:
            print(f'下載 {filename} 失敗，找不到音訊檔案。')
            return jsonify({'error': f'下載 {filename} 失敗，找不到音訊檔案。'}), 500

        temp_filepath = os.path.join(temp_dir, downloaded_files[0])
        final_filepath = os.path.join(DOWNLOAD_PATH, f'{filename}.mp3')

        # 如果需要調整速度
        if float(speed) != 1.0:
            print(f'正在調整音訊速度為 {speed}x...')
            try:
                audio = AudioSegment.from_mp3(temp_filepath)
                fast_audio = speedup(audio, playback_speed=speed)
                fast_audio.export(final_filepath, format='mp3')
                print(f'音訊已調整並儲存為: {final_filepath}')
            except Exception as e:
                print(f'音訊處理 {filename} 失敗: {e}')
                # 如果處理失敗，還是將原始檔案移過去
                shutil.move(temp_filepath, final_filepath)
                print(f'音訊處理失敗，已儲存原始檔案至: {final_filepath}')
        else:
            # 不需要調整速度，直接移動檔案
            shutil.move(temp_filepath, final_filepath)
            print(f'已儲存檔案至: {final_filepath}')

        # 清理暫存目錄
        shutil.rmtree(temp_dir)

        return jsonify({'status': 'success', 'message': f'歌曲 "{filename}" 下載並處理完成。'}), 200

    except Exception as e:
        print(f'處理下載請求時發生錯誤: {e}')
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # 在 5000 埠上執行應用程式
    app.run(port=5000, debug=True)
