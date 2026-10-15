import sys,json,hashlib
from pathlib import Path
b=Path(sys.argv[1]);p=json.loads((b/'prepared.json').read_text());bad=[k for k,v in p['frozen'].items() if hashlib.sha256((b/'work'/k).read_bytes()).hexdigest()!=v]
(b/'upstream_check.json').write_text(json.dumps(dict(changed=bad,frozen_count=len(p['frozen'])),indent=2)+'\n')
assert not bad,bad
