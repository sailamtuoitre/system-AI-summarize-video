import sys
import traceback as tb

try:
    from fastapi.testclient import TestClient
    from apps.api.main import app

    print("TestClient created successfully")

    client = TestClient(app)
    
    print("Opening file...")
    with open(r'C:\Users\leduc\OneDrive\Desktop\tool crawl\shorts_NHKht6p9X1Q.mp4', 'rb') as f:
        print("Posting to /upload...")
        response = client.post('/upload', files={'file': ('test.mp4', f, 'video/mp4')})
        print(f'Status: {response.status_code}')
        print(f'Response: {response.text}')

except Exception as e:
    print(f'Exception: {e}')
    tb.print_exc()
