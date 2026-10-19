from pathlib import Path
import hashlib,json
p=json.loads(Path('SELECTED_SOURCE_MANIFEST.json').read_text())
for name,r in p['files'].items():
 x=hashlib.file_digest(open(name,'rb'),'sha256').hexdigest();assert x==r['sha256'],(name,x,r['sha256'])
print('SOURCE_MANIFEST_PASS',len(p['files']),'front',p['source_front_sha256'],'tip',p['private_tip'])
