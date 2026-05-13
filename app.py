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
@app.route('/drm')
def play_drm():
    stream_url = decode_b64(request.args.get('bx_url'))
    drm_key = decode_b64(request.args.get('bx_key'))
    
    html = f"""
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>Aboud TV - Pro DRM Player</title>
        <!-- استدعاء مكتبات المشغل -->
        <script src="https://cdnjs.cloudflare.com/ajax/libs/shaka-player/4.7.1/shaka-player.ui.min.js"></script>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/shaka-player/4.7.1/controls.min.css">
        <style>
            /* تخصيص ألوان المشغل ليتطابق مع هيبة تطبيقك */
            :root {{
                --shaka-color-primary: #4facfe; 
                --shaka-color-text: #ffffff;
            }}
            body {{ margin: 0; background-color: #000; overflow: hidden; height: 100vh; font-family: 'Segoe UI', sans-serif; }}
            video {{ width: 100%; height: 100%; outline: none; }}
            
            /* شاشة التحميل السينمائية */
            .loading-container {{ position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); z-index: 10; text-align: center; color: white; }}
            .spinner {{ width: 50px; height: 50px; border: 5px solid rgba(79, 172, 254, 0.3); border-top-color: #4facfe; border-radius: 50%; animation: spin 1s linear infinite; margin: 0 auto 15px auto; }}
            @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
            
            /* زر الرجوع للخلف */
            .back-btn {{ position: absolute; top: 20px; left: 20px; z-index: 30; background: rgba(255,255,255,0.1); color: white; border: 1px solid rgba(255,255,255,0.2); border-radius: 50%; width: 45px; height: 45px; font-size: 20px; cursor: pointer; display: flex; justify-content: center; align-items: center; backdrop-filter: blur(10px); transition: 0.3s; }}
            .back-btn:active {{ transform: scale(0.9); background: rgba(255,255,255,0.3); }}
            
            .shaka-video-container {{ width: 100%; height: 100%; }}
        </style>
    </head>
    <body>
        <!-- زر العودة لتطبيقك -->
        <button class="back-btn" onclick="history.back()">🔙</button>
        
        <!-- شاشة التحميل -->
        <div id="loading" class="loading-container">
            <div class="spinner" id="spinner"></div>
            <div id="loading-text" style="font-size: 16px; font-weight: bold; text-shadow: 0 2px 4px rgba(0,0,0,0.5);">جاري فك التشفير السينمائي... 🚀</div>
        </div>

        <div data-shaka-player-container>
            <video autoplay data-shaka-player id="video"></video>
        </div>

        <script>
            const manifestUri = '{stream_url}';
            const drmInfo = '{drm_key or ''}';

            async function initPlayer() {{
                const video = document.getElementById('video');
                const player = new shaka.Player(video);
                const ui = new shaka.ui.Overlay(player, document.querySelector('[data-shaka-player-container]'), video);

                // إعدادات الواجهة الاحترافية
                ui.configure({{
                    controlPanelElements: ['play_pause', 'time_and_duration', 'spacer', 'mute', 'volume', 'fullscreen', 'overflow_menu'],
                    addSeekBar: true
                }});

                if (drmInfo) {{
                    if (drmInfo.includes('keyid=') && drmInfo.includes('key=')) {{
                        try {{
                            const urlParams = new URLSearchParams(drmInfo.substring(drmInfo.indexOf('?')));
                            const clearKeys = {{ [urlParams.get('keyid')]: urlParams.get('key') }};
                            player.configure({{ drm: {{ clearKeys: clearKeys }} }});
                        }} catch(e) {{}}
                    }} else if (drmInfo.includes(':') && !drmInfo.startsWith('http')) {{
                        const parts = drmInfo.split(':');
                        player.configure({{ drm: {{ clearKeys: {{ [parts[0]]: parts[1] }} }} }});
                    }} else if (drmInfo.startsWith('http')) {{
                        player.configure({{ drm: {{ servers: {{ 'com.widevine.alpha': drmInfo }} }} }});
                    }}
                }}

                player.addEventListener('error', onErrorEvent);

                try {{
                    await player.load(manifestUri);
                    document.getElementById('loading').style.display = 'none';
                }}
                catch (e) {{
                    onError(e);
                }}
            }}

            function onErrorEvent(event) {{ onError(event.detail); }}
            function onError(error) {{
                document.getElementById('spinner').style.display = 'none';
                // إظهار الخطأ بدقة لنعرف المشكلة
                document.getElementById('loading-text').innerHTML = '❌ عذراً، فشل فك التشفير<br><br><span style="font-size:14px; color:#ff4d4d; background: rgba(0,0,0,0.5); padding: 5px 10px; border-radius: 5px;">Error Code: ' + error.code + '</span>';
                console.error('Error code', error.code, 'object', error);
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
