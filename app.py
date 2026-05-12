import requests
import urllib.parse
from flask import Flask, request, Response
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# تغيير اسم المسار لينتهي بـ m3u8 ليقبله المشغل فوراً
@app.route('/stream.m3u8')
def proxy_stream():
    stream_url = request.args.get('url')
    user_agent = request.args.get('ua')
    referer = request.args.get('ref')

    if not stream_url:
        return "URL missing", 400

    headers = {}
    if user_agent:
        headers['User-Agent'] = user_agent
    if referer:
        headers['Referer'] = referer

    try:
        response = requests.get(stream_url, headers=headers, timeout=15, verify=False)
        response.raise_for_status()

        parsed_url = urllib.parse.urlparse(stream_url)
        base_path = parsed_url.scheme + "://" + parsed_url.netloc + parsed_url.path.rsplit('/', 1)[0] + "/"

        lines = response.text.splitlines()
        new_playlist = []

        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.startswith("#"):
                new_playlist.append(line)
            else:
                # إذا كان الرابط يخص قائمة فرعية (m3u8 أخرى)، نجبره على المرور عبر سيرفرنا مرة أخرى
                if ".m3u8" in line:
                    if not line.startswith("http"):
                        line = urllib.parse.urljoin(base_path, line)
                    
                    proxy_url = f"/stream.m3u8?url={urllib.parse.quote(line)}"
                    if user_agent: proxy_url += f"&ua={urllib.parse.quote(user_agent)}"
                    if referer: proxy_url += f"&ref={urllib.parse.quote(referer)}"
                    new_playlist.append(proxy_url)
                else:
                    # إذا كان ملف فيديو (ts)، نحوله لرابط كامل مباشر
                    if not line.startswith("http"):
                        line = urllib.parse.urljoin(base_path, line)
                    new_playlist.append(line)

        output = "\n".join(new_playlist)
        return Response(output, mimetype='application/vnd.apple.mpegurl')

    except Exception as e:
        return f"Error: {str(e)}", 500

if __name__ == "__main__":
    app.run()
