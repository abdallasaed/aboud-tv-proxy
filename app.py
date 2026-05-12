import requests
import urllib.parse
from flask import Flask, request, Response

app = Flask(__name__)

@app.route('/play')
def proxy_stream():
    stream_url = request.args.get('url')
    user_agent = request.args.get('ua')
    referer = request.args.get('ref')

    if not stream_url:
        return "Missing URL parameter", 400

    # تجهيز الترويسات
    headers = {}
    if user_agent:
        headers['User-Agent'] = user_agent
    if referer:
        headers['Referer'] = referer

    try:
        # طلب ملف البث
        response = requests.get(stream_url, headers=headers, timeout=15)
        response.raise_for_status()
        
        content = response.text
        base_url = stream_url.rsplit('/', 1)[0] + '/'

        # إعادة بناء الروابط داخل الملف
        lines = content.splitlines()
        modified_content = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.startswith('#'):
                modified_content.append(line)
            else:
                # تحويل الروابط النسبية إلى روابط كاملة
                full_url = urllib.parse.urljoin(base_url, line)
                modified_content.append(full_url)

        # الحل الجذري لمشكلة المشغل: إرسال نوع المحتوى الصحيح
        output = "\n".join(modified_content)
        return Response(output, mimetype='application/x-mpegURL')

    except Exception as e:
        return f"Error: {str(e)}", 500

if __name__ == "__main__":
    app.run()
