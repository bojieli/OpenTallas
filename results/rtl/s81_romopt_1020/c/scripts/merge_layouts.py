"""S81-ROMOPT-C: merge kslot_search outputs into tools/s81_dv/layer_prog/kslot_layouts.json (first found wins)."""
import json, sys
from pathlib import Path
out = Path(sys.argv[1]); db = json.loads(out.read_text()) if out.exists() else dict(schema='opentallas.s81_dv.kslot_layouts.v1', layouts={}, provenance={})
for f in sys.argv[2:]:
    if not Path(f).exists():
        continue
    d = json.loads(Path(f).read_text())
    for k, v in d['layouts'].items():
        if k not in db['layouts']:
            db['layouts'][k] = v; db['provenance'][k] = dict(d['provenance'][k], source=Path(f).name)
out.write_text(json.dumps(db, indent=1, sort_keys=True) + '\n')
print('MERGED', sorted(db['layouts']))
