import requests
import urllib.parse
import base64
import sys
from flask import Flask, request, Response
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# الصفحة الرئيسية للتأكد من عمل السيرفر
@app.route('/')
def home():
    return "<h1>Aboud TV Proxy is Running 🚀</h1>", 200

# دالة فك التشفير للروابط الواردة من التطبيق
def decode_b64(val):
    if not val: return None
    try:
        val = val.replace(' ', '+')
        val += '=' * (-len(val) % 4)
        return base64.b64decode(val).decode('utf-8')
    except:
        return val

# دالة تحضير الترويسات (Headers) الذكية
def get_headers(ua, ref):
    headers = {'User-Agent': ua if ua else 'Mozilla/5.0'}
    if ref:
        if not ref.startswith('http'):
            ref = 'https://' + ref
        headers['Referer'] = ref
        try:
            parsed_ref = urllib.parse.urlparse(ref)
            headers['Origin'] = f"{parsed_ref.scheme}://{parsed_ref.netloc}"
        except:
            pass
    return headers

# مسار مشغل الـ DRM الذكي
@app.route('/drm')
def play_drm():
    stream_url = decode_b64(request.args.get('bx_url'))
    drm_key = decode_b64(request.args.get('bx_key'))
    
    html = f"""
    <!DOCTYPE html>
    <html lang="ar">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>Aboud TV - DRM Player</title>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/shaka-player/4.7.1/shaka-player.ui.min.js"></script>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/shaka-player/4.7.1/controls.min.css">
        <style>
            body {{ margin: 0; background-color: #000; overflow: hidden; height: 100vh; display: flex; justify-content: center; align-items: center; font-family: sans-serif; }}
            video {{ width: 100%; height: 100%; outline: none; }}
            .loading {{ position: absolute; color: #4facfe; font-size: 18px; font-weight: bold; z-index: 10; text-align: center; }}
        </style>
    </head>
    <body>
        <div id="loading" class="loading">جاري فك التشفير والتشغيل... 🚀</div>
        <div data-shaka-player-container style="width: 100%; height: 100%; z-index: 20;">
            <video autoplay data-shaka-player id="video"></video>
        </div>
        <script>
            const manifestUri = '{stream_url}';
            const drmInfo = '{drm_key or ''}';
            async function initPlayer() {{
                const video = document.getElementById('video');
                const player = new shaka.Player(video);
                const ui = new shaka.ui.Overlay(player, document.querySelector('[data-shaka-player-container]'), video);
                if (drmInfo) {{
                    if (drmInfo.includes('keyid=') && drmInfo.includes('key=')) {{
                        try {{
                            const urlParams = new URLSearchParams(drmInfo.substring(drmInfo.indexOf('?')));
                            const clearKeys = {{ [urlParams.get('keyid')]: urlParams.get('key') }};
                            player.configure({{ drm: {{ clearKeys: clearKeys }} }});
                        }} catch(e) {{ console.log("Key extraction error"); }}
                    }} else if (drmInfo.includes(':') && !drmInfo.startsWith('http')) {{
                        const parts = drmInfo.split(':');
                        player.configure({{ drm: {{ clearKeys: {{ [parts[0]]: parts[1] }} }} }});
                    }} else if (drmInfo.startsWith('http')) {{
                        player.configure({{ drm: {{ servers: {{ 'com.widevine.alpha': drmInfo }} }} }});
                    }}
                }}
                try {{ await player.load(manifestUri); document.getElementById('loading').style.display = 'none'; video.requestFullscreen(); }}
                catch (e) {{ document.getElementById('loading').innerHTML = '❌ خطأ: ' + e.code; }}
            }}
            document.addEventListener('shaka-ui-loaded', initPlayer);
        </script>
    </body>
    </html>
    """
    return html

# مسار البروكسي الرئيسي (M3U8)
@app.route('/stream.m3u8')
def proxy_m3u8():
    stream_url = decode_b64(request.args.get('bx_url')) or request.args.get('url')
    user_agent = decode_b64(request.args.get('bx_ua')) or request.args.get('ua')
    referer = decode_b64(request.args.get('bx_ref')) or request.args.get('ref')

    print(f"[+] Request: {stream_url}", file=sys.stderr, flush=True)

    if not stream_url: return "URL missing", 400
    headers = get_headers(user_agent, referer)

    try:
        proxied_res = requests.get(stream_url, headers=headers, timeout=10, verify=False)
        proxied_res.raise_for_status()
        
        base_url = stream_url.rsplit('/', 1)[0] + '/'
        lines = proxied_res.text.splitlines()
        new_playlist = []

        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                if "URI=" in line:
                    parts = line.split('URI="')
                    sub_url = parts[1].split('"')[0]
                    full_sub = urllib.parse.urljoin(base_url, sub_url)
                    bx_u = urllib.parse.quote(base64.b64encode(full_sub.encode()).decode())
                    bx_a = urllib.parse.quote(base64.b64encode((user_agent or '').encode()).decode())
                    bx_r = urllib.parse.quote(base64.b64encode((referer or '').encode()).decode())
                    new_uri = f"/stream.m3u8?bx_url={bx_u}&bx_ua={bx_a}&bx_ref={bx_r}"
                    line = parts[0] + 'URI="' + new_uri + '"' + parts[1].split('"')[1]
                new_playlist.append(line)
            else:
                full_url = urllib.parse.urljoin(base_url, line)
                bx_u = urllib.parse.quote(base64.b64encode(full_url.encode()).decode())
                bx_a = urllib.parse.quote(base64.b64encode((user_agent or '').encode()).decode())
                bx_r = urllib.parse.quote(base64.b64encode((referer or '').encode()).decode())
                if ".m3u8" in line.lower() or "playlist" in line.lower() or "chunklist" in line.lower():
                    proxy_link = f"/stream.m3u8?bx_url={bx_u}&bx_ua={bx_a}&bx_ref={bx_r}"
                else:
                    proxy_link = f"/ts?bx_url={bx_u}&bx_ua={bx_a}&bx_ref={bx_r}"
                new_playlist.append(proxy_link)
        return Response("\n".join(new_playlist), mimetype='application/vnd.apple.mpegurl')
    except Exception as e:
        return f"Error: {str(e)}", 500

# مسار قطع الفيديو (TS)
@app.route('/ts')
def proxy_ts():
    ts_url = decode_b64(request.args.get('bx_url')) or request.args.get('url')
    ua = decode_b64(request.args.get('bx_ua')) or request.args.get('ua')
    ref = decode_b64(request.args.get('bx_ref')) or request.args.get('ref')
    headers = get_headers(ua, ref)
    def generate():
        try:
            with requests.get(ts_url, headers=headers, stream=True, timeout=15, verify=False) as r:
                for chunk in r.iter_content(chunk_size=8192): yield chunk
        except: pass
    return Response(generate(), content_type='video/mp2t')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
