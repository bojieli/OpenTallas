import json
from pathlib import Path
from throughput_budget import build as B
root = Path(__file__).resolve().parent
live = json.loads((root / 'live_inputs.json').read_text())
base = json.loads((root / 'budget_new.json').read_text())
# JSON object keys encode the schedule's Python None variant as 'null'.
for part in (base['ds_hbm'], base['qwen_hbm']):
    for op in part['ops']:
        variants = op.get('variants', {})
        if 'null' in variants:
            variants[None] = variants.pop('null')
# Reuse exactly computed schedule results from the completed same-source build.
# Re-run all qualification/coverage logic with snapshots of existing local readers.
B.ds_budget = lambda: base['ds_hbm']
B.qwen_budget = lambda: base['qwen_hbm']
B.ROM_BLOCKS = live['rom_blocks']
B.bench_ii = lambda: live['bench_ii']
def prov(path):
    if not path:
        return None
    assert path in live['provenance'], path
    return live['provenance'][path]
B.prov = prov
raise SystemExit(B.main())
