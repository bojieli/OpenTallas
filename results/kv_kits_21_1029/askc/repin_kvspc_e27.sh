#!/bin/bash
# KV-KITS-21 (2026-10-29): qkd_kvs_pc kit on event27 pins (DIE-KV-27 ASK-C: 288 pc__land_es S->W + o_prev/o_next/i_prev W-face
# reorder; 4133 pins, same names).  BASE = KV-KITS-16 kit (already --cts-setup-only --two-mode-grt, regen_kvspc.sh); the original
# generator inputs are deleted, so this is the regen_flow.sh form with ONE plan change: io.tcl + pins.json are rewritten from
# event27/qkd_kvs_pc_pins_r27.json by the generator's own io_tcl() (CHECKED: on the base pins_r25 it reproduces the base kit
# io.tcl and pins.json byte-identically).  Also: main tool copies refreshed, OWNER 12.19 OT_HOLD_FF_MARGIN 10,
# freeze.json pins_file/pins_sha256/plan_sha256/pins_canon/kit_hash/source_commit + PROVENANCE.json rewritten.
# rtl/, constraint.sdc, pdn, face_flops*, island_ft*, kvr2_reserve.tcl: byte-identical to the base.
# usage (intel2, this branch): repin_kvspc_e27.sh BASE_KIT PLAN_DIR PLAN_JSON OUTDIR
set -euo pipefail
REPO=$(git rev-parse --show-toplevel)
K=${1:?BASE_KIT}; P=${2:?PLAN_DIR}; PJ=${3:?PLAN_JSON}; O=${4:?OUTDIR}
T=$(basename "$K"); N=$O/$T
mkdir -p "$O"; rm -rf "$N"; mkdir -p "$N"
rsync -a --exclude run --exclude signoff --exclude views --exclude lec --exclude __pycache__ \
  --exclude 'autopilot_chain_*' --exclude 'preflight_autopilot_*' --exclude preflight.json \
  --exclude 1_synth_odb.v --exclude 'synth_odb_v.*' --exclude 'face_guard*.json' --exclude 'face_guard*.log' \
  --exclude 'rtl_lint.json' --exclude rtl_lint.log --exclude rtl_lint.ys --exclude 'selrange.*' \
  --exclude dont_use_check.json --exclude adder_map_dontuse.json --exclude sdc_lint.log \
  --exclude lec_run.log --exclude run_place.log --exclude run_route.log --exclude run_finish.log --exclude signoff.log \
  --exclude pin_audit.json --exclude 'replica_check_odb.json' "$K/" "$N/"
for f in face_guard.py lec.py rtl_lint.py sdc_lint.py straps.py vclk_corner.tcl; do cp "$REPO/tools/die_plan/$f" "$N/$f"; done
cp "$REPO/physical/die_plan/qwen_kvsys/cores/harden/run_kit_kv.sh" "$N/run_kit_kv.sh"
python3 -I "$REPO/tools/die_plan/signoff.py" bundle "$N"
python3 - "$REPO" "$N" "$K" "$P" "$PJ" <<'PY'
import json, sys, hashlib
from pathlib import Path
repo, kd, base, pd, pj = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], Path(sys.argv[4]), Path(sys.argv[5])
sys.path[:0] = [str(repo / 'physical/die_plan/qwen_kvsys/cores/harden'), str(repo / 'tools/die_plan')]
import gen_core_kit_kv as GK
import lec as LEC
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
fz = json.loads((kd / 'freeze.json').read_text())
w, h = fz['outline_um']
plan = json.loads(pj.read_bytes())
pf = {hc['pins_file'] for t in plan['partition_types'].values() for hc in t.get('hard_cores', []) if hc['module'] == fz['module']}
NEW = 'event27/qkd_kvs_pc_pins_r27.json'
assert NEW in pf, pf
doc = json.loads((pd / NEW).read_text())
old = json.loads((Path(base) / 'pins.json').read_text())
cj = json.loads((kd / 'core.json').read_text())
pa = json.loads((kd / 'pins_added.json').read_text())
assert not pa['added']
names = set(cj['pin_class'])
pins = doc['pins']
assert {p['name'] for p in pins} == {r['bus'] + (f"[{r['bit']}]" if r['bit'] is not None else '') for r in old}, 'pin name set changed'
ft = [p for p in pins if p['name'].startswith('ft_ck')]
nonft = [p for p in pins if not p['name'].startswith('ft_ck')]
off = [q['name'] for q in pins if abs(((q['x'] if q['layer'] in ('M3','M5','M7') else q['y']) - GK.OFFS[q['layer']]) / GK.PITCH[q['layer']] - round(((q['x'] if q['layer'] in ('M3','M5','M7') else q['y']) - GK.OFFS[q['layer']]) / GK.PITCH[q['layer']])) > 0.05]
assert not off, off[:3]
clk = {n for n, c in cj['pin_class'].items() if c in ('clk', 'clk_unused')}
txt, rows = GK.io_tcl(nonft + ft, w, h, fz['type'], clk | {p['name'] for p in ft})
assert len(rows) == len(old)
(kd / 'io.tcl').write_text(txt)
(kd / 'pins.json').write_text(json.dumps(rows) + '\n')
moved = sum(1 for a, b in zip(sorted(old, key=lambda r: (r['bus'], r['bit'] if r['bit'] is not None else -1)),
                              sorted(rows, key=lambda r: (r['bus'], r['bit'] if r['bit'] is not None else -1))) if a != b)
cfg = (kd / 'config.mk').read_text().splitlines()
hits = [i for i, l in enumerate(cfg) if l.startswith('export OT_HOLD_FF_MARGIN = ')]
assert len(hits) == 1
knob = [cfg[hits[0]].split(' = ', 1)[1], '10']
cfg[hits[0]] = 'export OT_HOLD_FF_MARGIN = 10'
(kd / 'config.mk').write_text('\n'.join(cfg) + '\n')
prov = LEC._repo_provenance(repo)
try:
    import die_sta_related as DSR
    canon = DSR.canon_sha256(DSR.canon_pins(doc, [w, h]))
except (ImportError, AttributeError) as e:
    canon = None
fz.update(pins_file=NEW, pins_sha256=sha(pd / NEW), plan_sha256=sha(pj), pins_canon_sha256=canon, kit_hash=GK.kit_hash(kd),
          source_commit=prov.get('commit'),
          regen=dict(lane='KV-KITS-21', base_kit=base, base_kit_hash=fz.get('kit_hash'), base_source_commit=fz.get('source_commit'),
                     plan='DIE-KV-28 event27 FINAL plan_e27f (event27 ASK-C pins)', pins_moved=moved,
                     knobs={'OT_HOLD_FF_MARGIN': knob}, options=['--cts-setup-only', '--two-mode-grt'] ,
                     tools_refreshed=['face_guard.py', 'lec.py', 'rtl_lint.py', 'sdc_lint.py', 'straps.py', 'vclk_corner.tcl',
                                      'run_kit_kv.sh', 'signoff bundle']))
(kd / 'freeze.json').write_text(json.dumps(fz, indent=1) + '\n')
LEC.write_kit_provenance(kd, repo, provenance=prov)
print('REPIN', kd.name, 'kit_hash', fz['kit_hash'], 'pins_moved', moved, 'canon', canon and canon[:12], 'src', prov.get('commit'))
PY
