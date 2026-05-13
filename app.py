import requests
import urllib.parse
import base64
import sys
from flask import Flask, request, Response
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

def decode_b64(val):
    if not val: return None
    try:
        val = val.replace(' ', '+')
        val += '=' * (-len(val) % 4)
        return base64.b64decode(val).decode('utf-8')
    except:
        return val

def get_headers(ua, ref):
    headers = {'User-Agent': ua if ua else 'Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36'}
    if ref:
        headers['Referer'] = ref
    return headers

@app.route('/')
def home():
    return "<h1>Aboud TV Proxy is Online 🚀</h1>", 200

# مسار البروكسي للقنوات العادية فقط
@app.route('/stream.m3u8')
def proxy_m3u8():
    stream_url = decode_b64(request.args.get('bx_url'))
    ua = decode_b64(request.args.get('bx_ua'))
    ref = decode_b64(request.args.get('bx_ref'))
    
    if not stream_url: return "URL missing", 400
    headers = get_headers(ua, ref)
    try:
        r = requests.get(stream_url, headers=headers, timeout=10, verify=False)
        r.raise_for_status()
        base_url = stream_url.rsplit('/', 1)[0] + '/'
        lines = r.text.splitlines()
        new_playlist = []
        for line in lines:
            if not line.strip() or line.startswith("#"):
                new_playlist.append(line)
            else:
                full_url = urllib.parse.urljoin(base_url, line)
                bx_u = urllib.parse.quote(base64.b64encode(full_url.encode()).decode())
                # تمرير الترويسات للقطعة التالية
                bx_a = request.args.get('bx_ua')
                bx_r = request.args.get('bx_ref')
                if ".m3u8" in line.lower():
                    proxy_link = f"/stream.m3u8?bx_url={bx_u}&bx_ua={bx_a}&bx_ref={bx_r}"
                else:
                    proxy_link = f"/ts?bx_url={bx_u}&bx_ua={bx_a}&bx_ref={bx_r}"
                new_playlist.append(proxy_link)
        return Response("\n".join(new_playlist), mimetype='application/vnd.apple.mpegurl')
    except Exception as e: return f"Error: {str(e)}", 500

@app.route('/ts')
def proxy_ts():
    ts_url = decode_b64(request.args.get('bx_url'))
    ua = decode_b64(request.args.get('bx_ua'))
    ref = decode_b64(request.args.get('bx_ref'))
    headers = get_headers(ua, ref)
    try:
        r = requests.get(ts_url, headers=headers, stream=True, timeout=15, verify=False)
        return Response(r.iter_content(chunk_size=8192), content_type='video/mp2t')
    except: return "TS Error", 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
