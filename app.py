import requests
import urllib.parse
import base64
from flask import Flask, request, Response
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

DEFAULT_UA = (
    "Mozilla/5.0 (Linux; Android 13; SM-S918B) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Mobile Safari/537.36"
)

# =========================================================
# Base64 Decode
# =========================================================
def decode_b64(val):
    if not val:
        return None

    try:
        val = val.replace(' ', '+')
        val += '=' * (-len(val) % 4)
        return base64.b64decode(val).decode('utf-8')
    except:
        return val

# =========================================================
# Headers
# =========================================================
def get_headers(ua=None, ref=None):

    headers = {
        'User-Agent': ua if ua else DEFAULT_UA,
        'Accept': '*/*',
        'Connection': 'keep-alive'
    }

    if ref:
        headers['Referer'] = ref

        try:
            parsed_ref = urllib.parse.urlparse(ref)
            headers['Origin'] = f"{parsed_ref.scheme}://{parsed_ref.netloc}"
        except:
            pass

    # دعم Range لتجنب التقطيع
    if 'Range' in request.headers:
        headers['Range'] = request.headers['Range']

    return headers

# =========================================================
# Home
# =========================================================
@app.route('/')
def home():
    return "<h1>Aboud TV Proxy Online 🚀</h1>", 200

# =========================================================
# SHAKA PROXY
# =========================================================
@app.route('/shaka_proxy', methods=['GET', 'OPTIONS'])
def shaka_proxy():

    # دعم OPTIONS
    if request.method == 'OPTIONS':
        return ('', 204, {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, OPTIONS',
            'Access-Control-Allow-Headers': '*',
            'Access-Control-Expose-Headers': '*'
        })

    target_url = decode_b64(request.args.get('bx_url'))
    ua = decode_b64(request.args.get('bx_ua'))
    ref = decode_b64(request.args.get('bx_ref'))

    if not target_url:
        return "Missing URL", 400

    headers = get_headers(ua, ref)

    try:

        r = requests.get(
            target_url,
            headers=headers,
            stream=True,
            timeout=20,
            allow_redirects=True
        )

        # =====================================================
        # تحديد نوع الملف الصحيح
        # =====================================================

        content_type = r.headers.get('Content-Type', '')

        url_lower = target_url.lower()

        if '.mpd' in url_lower:
            content_type = 'application/dash+xml'

        elif '.m3u8' in url_lower:
            content_type = 'application/vnd.apple.mpegurl'

        elif '.ts' in url_lower:
            content_type = 'video/mp2t'

        elif '.m4s' in url_lower:
            content_type = 'video/iso.segment'

        # =====================================================
        # Headers
        # =====================================================

        resp_headers = {}

        allowed_headers = [
            'Content-Length',
            'Content-Range',
            'Accept-Ranges',
            'Cache-Control',
            'Expires',
            'Date',
            'ETag'
        ]

        for key, value in r.headers.items():

            if key.lower() in [
                'transfer-encoding',
                'content-encoding',
                'connection'
            ]:
                continue

            if key in allowed_headers:
                resp_headers[key] = value

        # CORS
        resp_headers['Access-Control-Allow-Origin'] = '*'
        resp_headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        resp_headers['Access-Control-Allow-Headers'] = '*'
        resp_headers['Access-Control-Expose-Headers'] = '*'

        # =====================================================
        # Stream Generator
        # =====================================================

        def generate():
            for chunk in r.iter_content(chunk_size=1024 * 64):
                if chunk:
                    yield chunk

        return Response(
            generate(),
            status=r.status_code,
            headers=resp_headers,
            content_type=content_type
        )

    except Exception as e:
        return f"Proxy Error: {str(e)}", 500

# =========================================================
# M3U8 PROXY
# =========================================================
@app.route('/stream.m3u8')
def proxy_m3u8():

    stream_url = decode_b64(request.args.get('bx_url'))
    ua = decode_b64(request.args.get('bx_ua'))
    ref = decode_b64(request.args.get('bx_ref'))

    if not stream_url:
        return "URL missing", 400

    headers = get_headers(ua, ref)

    try:

        r = requests.get(
            stream_url,
            headers=headers,
            timeout=15,
            allow_redirects=True
        )

        r.raise_for_status()

        base_url = stream_url.rsplit('/', 1)[0] + '/'

        lines = r.text.splitlines()

        new_playlist = []

        for line in lines:

            line = line.strip()

            if not line or line.startswith("#"):
                new_playlist.append(line)
                continue

            full_url = urllib.parse.urljoin(base_url, line)

            bx_u = urllib.parse.quote(
                base64.b64encode(full_url.encode()).decode()
            )

            bx_a = ''
            bx_r = ''

            if ua:
                bx_a = urllib.parse.quote(
                    base64.b64encode(ua.encode()).decode()
                )

            if ref:
                bx_r = urllib.parse.quote(
                    base64.b64encode(ref.encode()).decode()
                )

            # إعادة تمرير الروابط عبر البروكسي
            if (
                ".m3u8" in line.lower()
                or "playlist" in line.lower()
                or "chunklist" in line.lower()
            ):

                proxy_link = (
                    f"/stream.m3u8?"
                    f"bx_url={bx_u}&bx_ua={bx_a}&bx_ref={bx_r}"
                )

            else:

                proxy_link = (
                    f"/ts?"
                    f"bx_url={bx_u}&bx_ua={bx_a}&bx_ref={bx_r}"
                )

            new_playlist.append(proxy_link)

        return Response(
            "\n".join(new_playlist),
            content_type='application/vnd.apple.mpegurl'
        )

    except Exception as e:
        return f"M3U8 Error: {str(e)}", 500

# =========================================================
# TS PROXY
# =========================================================
@app.route('/ts')
def proxy_ts():

    ts_url = decode_b64(request.args.get('bx_url'))
    ua = decode_b64(request.args.get('bx_ua'))
    ref = decode_b64(request.args.get('bx_ref'))

    if not ts_url:
        return "TS URL missing", 400

    headers = get_headers(ua, ref)

    try:

        r = requests.get(
            ts_url,
            headers=headers,
            stream=True,
            timeout=20,
            allow_redirects=True
        )

        resp_headers = {
            'Access-Control-Allow-Origin': '*',
            'Accept-Ranges': 'bytes'
        }

        return Response(
            r.iter_content(chunk_size=1024 * 64),
            status=r.status_code,
            headers=resp_headers,
            content_type='video/mp2t'
        )

    except Exception as e:
        return f"TS Error: {str(e)}", 500

# =========================================================
# Run
# =========================================================
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
