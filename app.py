import requests
import urllib.parse
import base64
from flask import Flask, request, Response
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# دالة فك التشفير
def decode_b64(val):
    if not val: return None
    try:
        val += '=' * (-len(val) % 4) # إصلاح الفراغات
        return base64.b64decode(val).decode('utf-8')
    except:
        return val # إذا لم يكن مشفراً، يعيده كما هو

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

@app.route('/stream.m3u8')
def proxy_m3u8():
    # استقبال البيانات المشفرة أو العادية
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
                    new_uri = f"stream.m3u8?url={urllib.parse.quote(full_sub)}&ua={urllib.parse.quote(user_agent or '')}&ref={urllib.parse.quote(referer or '')}"
                    line = parts[0] + 'URI="' + new_uri + '"' + parts[1].split('"')[1]
                new_playlist.append(line)
            else:
                full_url = urllib.parse.urljoin(base_url, line)
                proxy_link = f"ts?url={urllib.parse.quote(full_url)}&ua={urllib.parse.quote(user_agent or '')}&ref={urllib.parse.quote(referer or '')}"
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
                for chunk in r.iter_content(chunk_size=8192):
                    yield chunk
        except Exception as e:
            pass
            
    return Response(generate(), content_type='video/mp2t')

if __name__ == "__main__":
    app.run()
