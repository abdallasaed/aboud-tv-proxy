import requests
import urllib.parse
import base64
import re
from flask import Flask, request, Response, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    return "<h1>Aboud TV Proxy (HLS + DASH + DRM) 🚀</h1>", 200

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
        if not ref.startswith('http'):
            ref = 'https://' + ref
        headers['Referer'] = ref
        try:
            parsed_ref = urllib.parse.urlparse(ref)
            headers['Origin'] = f"{parsed_ref.scheme}://{parsed_ref.netloc}"
        except:
            pass
    return headers

# ---------------- HLS ----------------
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
    except Exception as e:
        return f"Error: {str(e)}", 500

@app.route('/ts')
def proxy_ts():
    ts_url = decode_b64(request.args.get('bx_url')) or request.args.get('url')
    ua = decode_b64(request.args.get('bx_ua')) or request.args.get('ua')
    ref = decode_b64(request.args.get('bx_ref')) or request.args.get('ref')
    headers = get_headers(ua, ref)

    def generate():
        try:
            with requests.get(ts_url, headers=headers, stream=True, timeout=15, verify=False) as r:
                r.raise_for_status()
                for chunk in r.iter_content(chunk_size=8192): yield chunk
        except: pass
    
    # ضمان وجود الـ CORS لقطع الفيديو
    return Response(generate(), content_type='video/mp2t', headers={'Access-Control-Allow-Origin': '*'})

# ---------------- DASH (MPD) ----------------
@app.route('/manifest.mpd')
def proxy_mpd():
    mpd_url = decode_b64(request.args.get('bx_url')) or request.args.get('url')
    ua = decode_b64(request.args.get('bx_ua')) or request.args.get('ua')
    ref = decode_b64(request.args.get('bx_ref')) or request.args.get('ref')

    if not mpd_url: return "MPD URL missing", 400
    headers = get_headers(ua, ref)

    try:
        proxied_res = requests.get(mpd_url, headers=headers, timeout=10, verify=False)
        proxied_res.raise_for_status()
        content = proxied_res.text
        
        # 🔥 اللمسة السحرية: حقن المسار الأصلي عشان المشغل ما يضيع مسار القطع 🔥
        base_url = mpd_url.rsplit('/', 1)[0] + '/'
        if '<BaseURL>' not in content:
            content = re.sub(r'(<MPD[^>]*>)', rf'\1\n  <BaseURL>{base_url}</BaseURL>', content, count=1)
            
        return Response(content, mimetype='application/dash+xml', headers={'Access-Control-Allow-Origin': '*'})
    except Exception as e:
        return f"Error: {str(e)}", 500

@app.route('/segment')
def proxy_segment():
    seg_url = decode_b64(request.args.get('bx_url')) or request.args.get('url')
    ua = decode_b64(request.args.get('bx_ua')) or request.args.get('ua')
    ref = decode_b64(request.args.get('bx_ref')) or request.args.get('ref')
    headers = get_headers(ua, ref)

    def generate():
        try:
            with requests.get(seg_url, headers=headers, stream=True, timeout=15, verify=False) as r:
                r.raise_for_status()
                for chunk in r.iter_content(chunk_size=8192): yield chunk
        except: pass
        
    return Response(generate(), content_type='video/mp4', headers={'Access-Control-Allow-Origin': '*'})

# ---------------- ClearKey DRM ----------------
@app.route('/clearkey')
def clearkey_license():
    kid = request.args.get('kid')
    key = request.args.get('key')
    if not kid or not key: return "Missing kid/key", 400

    try:
        kid_b64 = base64.urlsafe_b64encode(bytes.fromhex(kid.replace('-',''))).decode().rstrip("=")
        key_b64 = base64.urlsafe_b64encode(bytes.fromhex(key.replace('-',''))).decode().rstrip("=")

        license_json = {
            "keys": [{"kty":"oct", "kid": kid_b64, "k": key_b64}],
            "type":"temporary"
        }
        return jsonify(license_json)
    except Exception as e:
        return f"Error: {str(e)}", 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
