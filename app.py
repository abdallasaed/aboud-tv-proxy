import requests
import urllib.parse
from flask import Flask, request, Response
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/stream.m3u8')
def proxy_m3u8():
    stream_url = request.args.get('url')
    user_agent = request.args.get('ua')
    referer = request.args.get('ref')

    if not stream_url: return "URL missing", 400

    headers = {'User-Agent': user_agent if user_agent else 'Mozilla/5.0'}
    if referer: headers['Referer'] = referer

    try:
        # جلب القائمة
        proxied_res = requests.get(stream_url, headers=headers, timeout=10, verify=False)
        base_url = stream_url.rsplit('/', 1)[0] + '/'
        
        lines = proxied_res.text.splitlines()
        new_playlist = []

        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                # تعديل الروابط داخل التاغات (مثل جودات الفيديو)
                if "URI=" in line:
                    parts = line.split('URI="')
                    sub_url = parts[1].split('"')[0]
                    full_sub = urllib.parse.urljoin(base_url, sub_url)
                    new_uri = f"stream.m3u8?url={urllib.parse.quote(full_sub)}&ua={urllib.parse.quote(user_agent or '')}&ref={urllib.parse.quote(referer or '')}"
                    line = parts[0] + 'URI="' + new_uri + '"' + parts[1].split('"')[1]
                new_playlist.append(line)
            else:
                # تحويل كل الروابط (حتى الـ .ts) لتمر عبر سيرفرك
                full_url = urllib.parse.urljoin(base_url, line)
                proxy_link = f"ts?url={urllib.parse.quote(full_url)}&ua={urllib.parse.quote(user_agent or '')}&ref={urllib.parse.quote(referer or '')}"
                new_playlist.append(proxy_link)

        return Response("\n".join(new_playlist), mimetype='application/vnd.apple.mpegurl')
    except Exception as e:
        return str(e), 500

@app.route('/ts')
def proxy_ts():
    # هذا الجزء هو المسؤول عن تمرير قطع الفيديو (البث الفعلي)
    ts_url = request.args.get('url')
    ua = request.args.get('ua')
    ref = request.args.get('ref')
    
    headers = {'User-Agent': ua if ua else 'Mozilla/5.0'}
    if ref: headers['Referer'] = ref

    def generate():
        with requests.get(ts_url, headers=headers, stream=True, timeout=15, verify=False) as r:
            for chunk in r.iter_content(chunk_size=8192):
                yield chunk
    
    return Response(generate(), content_type='video/mp2t')

if __name__ == "__main__":
    app.run()
