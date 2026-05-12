from flask import Flask, request, Response
import requests
import urllib.parse

app = Flask(__name__)

@app.route('/play')
def proxy_stream():
    stream_url = request.args.get('url')
    user_agent = request.args.get('ua')
    referer = request.args.get('ref')

    if not stream_url:
        return "Missing URL parameter", 400

    headers = {}
    if user_agent:
        headers['User-Agent'] = user_agent
    if referer:
        headers['Referer'] = referer

    try:
        response = requests.get(stream_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        playlist_content = response.text
        base_url = stream_url.rsplit('/', 1)[0] + '/'

        modified_playlist = []
        for line in playlist_content.splitlines():
            line = line.strip()
            if line == '' or line.startswith('#'):
                modified_playlist.append(line)
            elif line.startswith('http'):
                modified_playlist.append(line)
            else:
                absolute_url = urllib.parse.urljoin(base_url, line)
                modified_playlist.append(absolute_url)

        return Response('\n'.join(modified_playlist), mimetype='application/vnd.apple.mpegurl')

    except requests.exceptions.RequestException as e:
        return f"Error fetching stream: {str(e)}", 502
    except Exception as e:
        return f"Internal Server Error: {str(e)}", 500

if __name__ == '__main__':
    app.run()
