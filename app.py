import requests
import urllib.parse
from flask import Flask, request, Response
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/play')
def proxy_stream():
    stream_url = request.args.get('url')
    user_agent = request.args.get('ua')
    referer = request.args.get('ref')

    if not stream_url:
        return "URL missing", 400

    # تجهيز الترويسات
    headers = {
        'User-Agent': user_agent if user_agent else 'Mozilla/5.0',
    }
    if referer:
        headers['Referer'] = referer

    try:
        # جلب ملف الـ m3u8 من السيرفر الأصلي
        response = requests.get(stream_url, headers=headers, timeout=15, verify=False)
        response.raise_for_status()
        
        # استخراج الرابط الأساسي (Base URL) لبناء الروابط الكاملة
        # مثلاً لو الرابط http://site.com/live/1.m3u8 يكون الأساس http://site.com/live/
        parsed_url = urllib.parse.urlparse(stream_url)
        base_path = parsed_url.scheme + "://" + parsed_url.netloc + parsed_url.path.rsplit('/', 1)[0] + "/"

        lines = response.text.splitlines()
        new_playlist = []

        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.startswith("#"):
                # الحفاظ على التاغات كما هي
                new_playlist.append(line)
            else:
                # تحويل أي رابط نسبي إلى رابط كامل يشير للسيرفر الأصلي مباشرة
                if line.startswith("http"):
                    new_playlist.append(line)
                else:
                    full_segment_url = urllib.parse.urljoin(base_path, line)
                    new_playlist.append(full_segment_url)

        # إرجاع الملف الجديد للمشغل المدمج
        output = "\n".join(new_playlist)
        return Response(
            output,
            mimetype='application/vnd.apple.mpegurl',
            headers={
                'Content-Type': 'application/vnd.apple.mpegurl',
                'Access-Control-Allow-Origin': '*'
            }
        )

    except Exception as e:
        return f"Error: {str(e)}", 500

if __name__ == "__main__":
    app.run()
