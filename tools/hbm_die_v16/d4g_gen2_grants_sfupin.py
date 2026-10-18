#!/usr/bin/env python3
"""H-D4G GEN2 10-18 (SFU-K9PIN / HANDOFF 0gj): bind the SFU core stand-in pins to the k9 kit pin plan.
Adds to every sfucore_<q> grant slot synth_pin_bind = {faces: kit floorplan.json 'pins' face per port (master-local),
windows: io_word / compiler_control / fault packed on the N face core-local x 1040.4-1576.8 (the kit's region)}.
tools/hbm_die_v15/die_case_v16.py builds the SYNTH abstract from it; the orientation (SW R0 / SE MY / NW MX / NE R180)
is applied by place_inst, so one abstract matches the hardened block in all 4 quadrants.  Idempotent.
    d4g_gen2_grants_sfupin.py [--grants G] [--kit-floorplan F | --kit-ref origin/claude/sfuk9-1018]"""
import argparse, json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ap = argparse.ArgumentParser()
ap.add_argument('--grants', default=str(ROOT / 'results/arch/hbm_die_d4g/grants_d4g.json'))
ap.add_argument('--kit-floorplan', default=None)
ap.add_argument('--kit-ref', default='origin/claude/sfuk9-1018')
a = ap.parse_args()
KP = 'physical/ref_tile/hbm_sfucore_k9/floorplan.json'
if a.kit_floorplan:
    fp = json.loads(Path(a.kit_floorplan).read_text())
else:
    fp = json.loads(subprocess.check_output(['git', '-C', str(ROOT), 'show', f'{a.kit_ref}:{KP}']))
sha = subprocess.run(['git', '-C', str(ROOT), 'rev-parse', '--short=9', a.kit_ref], capture_output=True, text=True).stdout.strip()
faces = {p: f for f, L in fp['pins'].items() for p in L}
sys.path.insert(0, str(ROOT / 'tools'))
import die_port_bind as DPB  # noqa: E402
idx, _ = DPB.rtl_index([str(ROOT / 'rtl/hbm_accel/generic/peers')], [], {}, [])
rtl = set(idx['ot_hgi_sfu_core_split3'].order)
if set(faces) != rtl:
    raise SystemExit(f'kit face map != RTL ports: kit-only {sorted(set(faces) - rtl)} rtl-only {sorted(rtl - set(faces))}')
WIN = [dict(ports=['io_word', 'compiler_control', 'fault'], face='N', local_um=[1040.4, 1576.8])]
for w in WIN:
    assert all(faces[p] == w['face'] for p in w['ports'])
g = json.loads(Path(a.grants).read_text())
n = 0
for s in g['slots']:
    if s['name'].startswith('sfucore_'):
        s['synth_pin_bind'] = dict(source=f'SFU-K9PIN kit hbm_sfucore_k9 claude/sfuk9-1018 {sha or "bfa778f2e"} floorplan.json pins',
                                   faces=dict(sorted(faces.items())), windows=WIN)
        n += 1
assert n == 4, n
Path(a.grants).write_text(json.dumps(g, indent=1) + '\n')
print('synth_pin_bind on', n, 'sfucore slots;', len(faces), 'ports;', sum(1 for f in faces.values() if f == 'N'), 'on N')
