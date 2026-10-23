import sys,json,tempfile,hashlib
from pathlib import Path
sys.path.insert(0,'src/tools/s81_dv/layer_prog/svc')
import so_bench as S
fx=Path('/srv/opentallas-scratch/claude/codex-tok-s81-layers/fixtures/L0')
checked=S.verify_reference_sources(fx)
with tempfile.TemporaryDirectory() as t:
 meta=json.loads((fx/'meta.json').read_text());meta['sources']['tools/hdc_golden_v41.py']='0'*64
 (Path(t)/'meta.json').write_text(json.dumps(meta))
 try:S.verify_reference_sources(t)
 except ValueError as e:negative=str(e)
 else:raise AssertionError('stale reference accepted')
for m in ('base','cs_swap','hm_shift'):
 for p in (Path('images_pinned')/m).glob('*.hex'):
  assert p.read_bytes()==(Path('images_guarded')/m/p.name).read_bytes(),str(p)
print(json.dumps(dict(status='PASS',reference_sources=checked,stale_reference_rejected=negative,all_runtime_rows_unchanged=True),indent=2))
