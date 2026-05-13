import requests
import urllib.parse
import base64
import sys
from flask import Flask, request, Response
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    return "<h1>Aboud TV Proxy is Running 🚀</h1>", 200

def decode_b64(val):
    if not val: return None
    try:
        val = val.replace(' ', '+')
        val += '=' * (-len(val) % 4)
        return base64.b64decode(val).decode('utf-8')
    except:
        return val

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

# 🔥 المسار الخاص بسحب قطع الـ DRM (مع أوامر الطباعة لكشف الخلل) 🔥
@app.route('/shaka_proxy')
def shaka_proxy():
    target_url = decode_b64(request.args.get('bx_url'))
    ua = decode_b64(request.args.get('bx_ua'))
    ref = decode_b64(request.args.get('bx_ref'))
    
    print("\n" + "="*40, file=sys.stderr, flush=True)
    print(f"[DRM PROXY] TARGET: {target_url}", file=sys.stderr, flush=True)
    print(f"[DRM PROXY] REF: {ref} | UA: {ua}", file=sys.stderr, flush=True)
    
    if not target_url: return "Missing URL", 400
    headers = get_headers(ua, ref)
    
    if 'Range' in request.headers:
        headers['Range'] = request.headers['Range']
        
    try:
        r = requests.get(target_url, headers=headers, stream=True, timeout=15, verify=False)
        print(f"[DRM PROXY] HTTP STATUS: {r.status_code}", file=sys.stderr, flush=True)
        print("="*40 + "\n", file=sys.stderr, flush=True)
        
        resp_headers = {}
        if 'Content-Type' in r.headers: resp_headers['Content-Type'] = r.headers['Content-Type']
        if 'Content-Range' in r.headers: resp_headers['Content-Range'] = r.headers['Content-Range']
        if 'Accept-Ranges' in r.headers: resp_headers['Accept-Ranges'] = r.headers['Accept-Ranges']
        resp_headers['Access-Control-Allow-Origin'] = '*' 
        
        def generate():
            for chunk in r.iter_content(chunk_size=8192):
                yield chunk
                
        return Response(generate(), status=r.status_code, headers=resp_headers)
    except Exception as e:
        print(f"[DRM PROXY] FATAL ERROR: {str(e)}", file=sys.stderr, flush=True)
        return str(e), 500

@app.route('/drm')
def play_drm():
    stream_url = decode_b64(request.args.get('bx_url'))
    drm_key = decode_b64(request.args.get('bx_key'))
    raw_ua = request.args.get('bx_ua') or ''
    raw_ref = request.args.get('bx_ref') or ''
    
    print(f"\n[DRM PAGE OPENED] URL: {stream_url}", file=sys.stderr, flush=True)
    
    html = f"""
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>Aboud TV - Pro DRM Player</title>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/shaka-player/4.7.1/shaka-player.ui.min.js"></script>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/shaka-player/4.7.1/controls.min.css">
        <style>
            :root {{ --shaka-color-primary: #4facfe; --shaka-color-text: #ffffff; }}
            body {{ margin: 0; background-color: #000; overflow: hidden; height: 100vh; font-family: 'Segoe UI', sans-serif; }}
            video {{ width: 100%; height: 100%; outline: none; }}
            .loading-container {{ position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); z-index: 10; text-align: center; color: white; }}
            .spinner {{ width: 50px; height: 50px; border: 5px solid rgba(79, 172, 254, 0.3); border-top-color: #4facfe; border-radius: 50%; animation: spin 1s linear infinite; margin: 0 auto 15px auto; }}
            @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
            .back-btn {{ position: absolute; top: 20px; left: 20px; z-index: 30; background: rgba(255,255,255,0.1); color: white; border: 1px solid rgba(255,255,255,0.2); border-radius: 50%; width: 45px; height: 45px; font-size: 20px; cursor: pointer; display: flex; justify-content: center; align-items: center; backdrop-filter: blur(10px); transition: 0.3s; }}
            .back-btn:active {{ transform: scale(0.9); background: rgba(255,255,255,0.3); }}
            .shaka-video-container {{ width: 100%; height: 100%; }}
        </style>
    </head>
    <body>
        <button class="back-btn" onclick="history.back()">🔙</button>
        <div id="loading" class="loading-container">
            <div class="spinner" id="spinner"></div>
            <div id="loading-text" style="font-size: 16px; font-weight: bold;">جاري فك التشفير السينمائي... 🚀</div>
        </div>
        <div data-shaka-player-container>
            <video autoplay data-shaka-player id="video"></video>
        </div>
        <script>
            const manifestUri = '{stream_url}';
            const drmInfo = '{drm_key or ''}';
            const rawUa = '{raw_ua}';
            const rawRef = '{raw_ref}';

            async function initPlayer() {{
                const video = document.getElementById('video');
                const player = new shaka.Player(video);
                const ui = new shaka.ui.Overlay(player, document.querySelector('[data-shaka-player-container]'), video);

                ui.configure({{
                    controlPanelElements: ['play_pause', 'time_and_duration', 'spacer', 'mute', 'volume', 'fullscreen', 'overflow_menu'],
                    addSeekBar: true
                }});

                player.getNetworkingEngine().registerRequestFilter(function(type, request) {{
                    if (type == shaka.net.NetworkingEngine.RequestType.MANIFEST || type == shaka.net.NetworkingEngine.RequestType.SEGMENT) {{
                        const originalUri = request.uris[0];
                        const b64Encode = (str) => btoa(unescape(encodeURIComponent(str)));
                        request.uris[0] = '/shaka_proxy?bx_url=' + encodeURIComponent(b64Encode(originalUri)) + '&bx_ua=' + rawUa + '&bx_ref=' + rawRef;
                    }}
                }});

                player.getNetworkingEngine().registerResponseFilter(function(type, response) {{
                    if (type == shaka.net.NetworkingEngine.RequestType.MANIFEST) {{
                        response.uri = manifestUri; 
                    }}
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
                try {{ await player.load(manifestUri); document.getElementById('loading').style.display = 'none'; }}
                catch (e) {{ onError(e); }}
            }}
            function onErrorEvent(event) {{ onError(event.detail); }}
            function onError(error) {{
                document.getElementById('spinner').style.display = 'none';
                document.getElementById('loading-text').innerHTML = '❌ عذراً، فشل فك التشفير<br><br><span style="font-size:14px; color:#ff4d4d;">Error Code: ' + error.code + '</span>';
            }}
            document.addEventListener('shaka-ui-loaded', initPlayer);
        </script>
    </body>
    </html>
    """
    return html

@app.route('/stream.m3u8')
def proxy_m3u8():
    stream_url = decode_b64(request.args.get('bx_url')) or request.args.get('url')
    user_agent = decode_b64(request.args.get('bx_ua')) or request.args.get('ua')
    referer = decode_b64(request.args.get('bx_ref')) or request.args.get('ref')
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
    except Exception as e: return f"Error: {str(e)}", 500

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
