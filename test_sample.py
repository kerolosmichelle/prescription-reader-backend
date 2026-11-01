import requests
with open('../frontend/assets/sample-prescription.png', 'rb') as f:
    files = {'image': ('sample-prescription.png', f, 'image/png')}
    r = requests.post('http://127.0.0.1:5000/extract-text', files=files)
    print(r.status_code)
    data = r.json()
    print(data['success'])
    print('meds:', len(data.get('medicines',[])))
    for m in data.get('medicines',[]):
        print(m)
    print('raw:', data.get('raw_text')[:200])
