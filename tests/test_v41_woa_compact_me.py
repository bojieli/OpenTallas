import json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def test_compact_ME_matches_cycles_and_real_outputs():
 x=json.loads((ROOT/'results/rtl/v41_woa_compact_me.json').read_text())
 assert x['arms']['expanded']['exact_rows']==x['arms']['compact']['exact_rows']==32
 assert x['arms']['expanded']['cycles']==x['arms']['compact']['cycles']==4235
 assert x['contract']['extra_cycles']==0
 for f,h in x['source_sha256'].items():assert hashlib.sha256((ROOT/f).read_bytes()).hexdigest()==h
