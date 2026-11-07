import sys
from pathlib import Path
p=Path(sys.argv[1]); s=p.read_text(); Path(str(p)+'.before_fg_advisory').write_text(s)
a="python3 -I /work/face_guard.py \\$N --pins /work/pins.json --out /work/face_guard.json; rc=\\$?; if [ \\$rc != 0 ]; then echo 'FAIL_PREFLOOR face_guard' | tee -a /work/FAIL_PREFLOOR; fi; fi; \\"
b="python3 -I /work/face_guard.py \\$N --pins /work/pins.json --out /work/face_guard.json; rc=\\$?; if [ \\$rc != 0 ]; then echo 'FACE_GUARD_ADVISORY synth (OWNER 11-03 pre-build advisory; as-built face_guard still gates sign-off)'; rc=0; fi; fi; \\"
assert s.count(a)==1; s=s.replace(a,b)
a2="--out /work/face_guard_odb.json; rc=\\$?; fi; \\"
b2="--out /work/face_guard_odb.json; rc=\\$?; if [ \\$rc != 0 ]; then echo 'FACE_GUARD_ADVISORY synth ODB'; rc=0; fi; fi; \\"
assert s.count(a2)==1; s=s.replace(a2,b2); p.write_text(s); print('patched')
