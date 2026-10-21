"""S81-ROMOPT-A (10-20): regenerate the frame ROM via-map + cfg7 images of one frame and layer class with the compiler
defaults in the environment (xs_flags), fully legalised; record phases, legaliser faults, ROM fill (<= 8192 a pair),
cfg7 rows (<= 4096) and the sha256 of every image.  usage (cwd = root): python3 imagesa.py OUT LAYER FRAME"""
import hashlib, json, sys
from pathlib import Path
R = Path.cwd(); sys.path.insert(0, str(R / 'tools/s81_dv/layer_prog'))
import xs_place as X
import xs_flags as XO
import xs_topo as TP
import dv_layer_compile as C
O, L, FR = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
FX = f'/srv/opentallas-scratch/claude/s81-calpipe/fixtures/{L}'; DR = '/srv/opentallas-scratch/claude/toksim-s81b-fwoa/dieref'
die = C.Die(C.die_tree(None, DR))
ops = X.XS_OPS[L] + X.BF_OPS[L]
rec, field = X.compile_frame(die, FR, FX, ops)
d = O / L / FR; d.mkdir(parents=True, exist_ok=True)
names, tmp = X.write_images(field, rec['pairs'], rec['q_pairs'], rec['bf_pairs'], FR, d)
img = {n: hashlib.sha256((d / n).read_bytes()).hexdigest() for n in sorted(set(names))}
byop = {}
for p in rec['phases']:
    byop.setdefault(p['op'], []).append(p['rows'])
faults = sum(p['faults'] for p in rec['phases'] if p.get('calendar') != 'not_legalised')
man = dict(layer=L, frame=FR, master=rec['master'], lk=rec['lk'], slice=rec['slice'], env=XO.describe(), topo=TP.describe(),
           nphases=rec['nphases'], cfg7_rows=4 * rec['nphases'], cfg7_ok=4 * rec['nphases'] <= 4096, faults=faults,
           fill_max=max(rec['fill']), fill=rec['fill'], depth=rec['depth'], fill_ok=max(rec['fill']) <= rec['depth'],
           pairs=rec['pairs'], phases_by_op={k: len(v) for k, v in byop.items()}, rows_by_op={k: sum(v) for k, v in byop.items()},
           images=img, image_set_sha256=hashlib.sha256(json.dumps(img, sort_keys=True).encode()).hexdigest())
(d / 'manifest.json').write_text(json.dumps(man, indent=1) + '\n')
print('IMAGESA', L, FR, 'phases', rec['nphases'], 'faults', faults, 'fill', man['fill_max'], '/', rec['depth'], 'images', len(img),
      'set', man['image_set_sha256'][:16], json.dumps(man['phases_by_op']), flush=True)
sys.exit(0 if faults == 0 and man['fill_ok'] and man['cfg7_ok'] else 1)
