import requests
from flask import Flask, request, Response
from flask_cors import CORS

app = Flask(__name__)
CORS(app) # السماح بتبادل الموارد بين النطاقات المختلفة

@app.route('/play')
def proxy_stream():
    stream_url = request.args.get('url')
    user_agent = request.args.get('ua')
    referer = request.args.get('ref')

    if not stream_url:
        return "URL is missing", 400

    headers = {}
    if user_agent:
        headers['User-Agent'] = user_agent
    if referer:
        headers['Referer'] = referer

    try:
        # جلب البيانات الخام من السيرفر الأصلي
        response = requests.get(stream_url, headers=headers, timeout=15, verify=False)
        
        # إرسال المحتوى كما هو دون تعديل أسطر (لتجنب إتلاف الملف)
        # مع تحديد Header نوع الملف بشكل دقيق جداً للمشغل المدمج
        return Response(
            response.content,
            status=response.status_code,
            content_type='application/vnd.apple.mpegurl',
            headers={
                'Access-Control-Allow-Origin': '*',
                'Content-Disposition': 'inline; filename="playlist.m3u8"'
            }
        )

    except Exception as e:
        return f"Error: {str(e)}", 500

if __name__ == "__main__":
    app.run()
