import json,hashlib,os
from pathlib import Path
k=Path('/work');c=os.environ['OT_CORNER'].lower();d=json.load(open(k/f'expected_postcts_{c}.libraries.json'))
assert hashlib.sha256((k/'config.mk').read_bytes()).hexdigest()==d['config_sha256'],'native library config differs'
for row in d['libraries']:
 p=Path(row['path']);assert hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256'],str(p)
print('QUERY exact recorded native library/config digests matched; no policy/clock/SDC/RC changes')
