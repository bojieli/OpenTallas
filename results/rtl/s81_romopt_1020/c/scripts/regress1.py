"""S81-ROMOPT-C: default (OT_XS_KSLOT unset = 1) must reproduce the RATE3 release compile byte-for-byte: frame.json phases
/ fill / pairs and every generated image sha256 of the RATE3 fseq3 vectors (ep9 s81-rate3/out/fseq3)."""
import json, os, sys, tempfile
from pathlib import Path
from types import SimpleNamespace
R = Path.cwd(); sys.path.insert(0, str(R / 'tools/s81_dv/layer_prog'))
assert 'OT_XS_KSLOT' not in os.environ
import xs_place as X, xs_topo as TP, dv_layer_compile as C
FX = '/srv/opentallas-scratch/claude/s81-calpipe/fixtures/L0'; DR = '/srv/opentallas-scratch/claude/toksim-s81b-fwoa/dieref'
REF = Path('/srv/opentallas-scratch/claude/s81-rate3/out/fseq3')
die = C.Die(C.die_tree(None, DR))
res = []
for fr, op in [('u_f_3L01', 'ffn.experts_gu'), ('u_f_3L01', 'ffn.down'), ('u_f_0L00', 'ffn.down')]:
    V = REF / fr / op.split('.')[-1]
    ref = json.loads((V / 'frame.json').read_text())
    rec, field = X.compile_frame(die, fr, FX, [op])
    mine = json.loads(json.dumps(dict(rec, env=ref['env'], topo=TP.describe(), phases=[{k: v for k, v in p.items() if k != 'plan'} for p in rec['phases']]), default=str))
    same = mine == ref
    imgs = []
    for ph in rec['phases']:
        if ph['op'] != op or not (V / f'p{ph["phase"]}' / 'meta.json').exists():
            continue
        d = Path(tempfile.mkdtemp())
        X.gen_one(SimpleNamespace(fixtures=FX, frame=fr, mutant=None, bf_measure=False), rec, field, ph, d)
        a, b = json.loads((d / 'meta.json').read_text()), json.loads((V / f'p{ph["phase"]}' / 'meta.json').read_text())
        imgs.append((ph['phase'], a['images'] == b['images'], a['plan'] == b['plan']))
    res.append(dict(frame=fr, op=op, frame_json_identical=same, phases=len(rec['phases']),
                    images_identical=all(x[1] for x in imgs), plans_identical=all(x[2] for x in imgs), checked_phases=len(imgs)))
    print('REGRESS_K1', res[-1], flush=True)
ok = all(r['frame_json_identical'] and r['images_identical'] and r['plans_identical'] for r in res)
Path(sys.argv[1]).write_text(json.dumps(dict(PASS=ok, cases=res), indent=1) + '\n')
print('REGRESS_K1_VERDICT', 'PASS' if ok else 'FAIL')
