"""S81-ROMOPT-C (10-20): MEASURE the multi-slot element return cadence (OT_XS_KSLOT=k) on the RELEASE frame RTL.
Compiles one frame's op phases with xs_place.compile_frame (release flags + OT_XS_KSLOT from the environment), writes
each phase's bench vectors (gen_one), runs the -DTB_PVTRACE build of the release FSEQ tb (single phase, +PH=k), and
fits every element pv word to E(pair, seg) + d: d per (n slots in the element, slot j) must be ONE constant per shape
(pair-, phase-, row- and value-independent) or the measurement FAILS.
usage (cwd = root): python3 pvmeasure.py OUT FRAME PV_BUILD OP [PHASES...]"""
import collections, gzip, hashlib, json, os, re, subprocess, sys
from pathlib import Path
from types import SimpleNamespace
R = Path.cwd(); sys.path.insert(0, str(R / 'tools/s81_dv/layer_prog'))
import xs_place as X
import xs_topo as TP
import dv_layer_compile as C
O, FR, BLD, op = Path(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4]
want = [int(x) for x in sys.argv[5:]]
FX = '/srv/opentallas-scratch/claude/s81-calpipe/fixtures/L0'; DR = '/srv/opentallas-scratch/claude/toksim-s81b-fwoa/dieref'
L = Path('/srv/opentallas-scratch/claude/s81-romopt-c'); exe = L / BLD / 'obj/Vtb_toksim_fgu_seq'
die = C.Die(C.die_tree(None, DR))
env = {k: os.environ.get(k) for k in ('OT_XS_QPAIRS', 'OT_XS_GU_MERGE', 'OT_XS_TOPO', 'OT_XS_PROP', 'OT_XS_CAL_SEGMENT', 'OT_XS_KSLOT', 'OT_XS_KSLOT_OPS')}
V = O / FR / op.split('.')[-1]; V.mkdir(parents=True, exist_ok=True)
rec, field = X.compile_frame(die, FR, FX, [op])
phs = [p for p in rec['phases'] if p['op'] == op and p['rows'] > 0]
if want:
    phs = [p for p in phs if p['phase'] in want]
fits = collections.defaultdict(list)
runs = []
for ph in phs:
    out = V / f'p{ph["phase"]}'
    X.gen_one(SimpleNamespace(fixtures=FX, frame=FR, mutant=None, bf_measure=False), rec, field, ph, out)
    meta = json.loads((out / 'meta.json').read_text())
    em = meta['plan']['emission']
    args = (out / 'ARGS').read_text().split()
    log = out / 'run_pv.log'
    with log.open('w') as f:
        rr = subprocess.run([str(exe)] + args, stdout=f, stderr=subprocess.STDOUT)
    txt = log.read_text()
    # predicted single-slot edge per (pair, seg) and the slot of every super row
    slots = {}
    for d in meta['plan']['placement']:
        slots[(d['pair'], d['super_row'])] = (d['seg'], d.get('slot', 0), d.get('slots', 1))
    base = lambda p, s: em['e0'] + em['last_beat'][s] + em['off'][str(p)] + em['seg_extra'][s]
    bad = []
    nw = 0
    for m in re.finditer(r'^PV (\d+) (\S+) ([01]+) rows (\d+) (\d+) seg (\d+) (\d+) n (\d+)', txt, re.M):
        e, path, bits, r0, r1, s0, s1, n = m.groups()
        pm = re.search(r'u_e(\d+)', path)
        if not pm:
            bad.append(('no pair in path', path)); continue
        p = int(pm.group(1))
        for mb, (bit, row, sg) in enumerate(zip(bits[::-1], (r0, r1), (s0, s1))):
            if bit != '1':
                continue
            rr_ = int(row) & 0x3FFF
            key = (p, rr_ // 2)
            if key not in slots:
                bad.append(('unplaced pv word', p, rr_)); continue
            s, j, nn = slots[key]
            if int(sg) != s:
                bad.append(('seg mismatch', p, rr_, sg, s))
            d = int(e) - base(p, s)
            fits[(nn, j)].append(dict(d=d, pair=p, row=rr_, mb=mb, phase=ph['phase'], seg=s))
            nw += 1
    runs.append(dict(phase=ph['phase'], rows=ph['rows'], rc=rr.returncode, pv_words=nw, bad=bad[:10],
                     faults=re.findall(r'^FAULT .*$', txt, re.M)[:4], end=(re.findall(r'^END .*$', txt, re.M) or [None])[0]))
    with open(log, 'rb') as f_in, gzip.open(str(log) + '.gz', 'wb') as f_out:
        f_out.write(f_in.read())
    log.unlink()
    print('PVMEASURE', FR, op, 'phase', ph['phase'], 'rows', ph['rows'], 'pv_words', nw, 'bad', len(bad), runs[-1]['faults'], flush=True)
table = {}
ok = all(not r['bad'] and not r['faults'] and r['pv_words'] > 0 for r in runs)
for (nn, j), v in sorted(fits.items()):
    ds = sorted({x['d'] for x in v})
    table.setdefault(str(nn), {})[str(j)] = dict(d=ds, words=len(v), by_seg={str(s): sorted({x['d'] for x in v if x['seg'] == s}) for s in sorted({x['seg'] for x in v})})
    if len(ds) != 1:
        ok = False
res = dict(VERDICT='PASS' if ok else 'FAIL', frame=FR, op=op, env=env, topo=TP.describe(), runs=runs, table=table,
           rule='d = PV edge - (e0 + last_beat(seg) + off(pair) + seg_extra(seg)) per (slots n in the element, slot j)',
           binary_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(), verilator=(L / BLD / 'verilator.version').read_text().strip())
(V / 'pvmeasure.json').write_text(json.dumps(res, indent=1) + '\n')
print('PVMEASURE_TABLE', FR, op, res['VERDICT'], json.dumps({n: {j: t['d'] for j, t in v.items()} for n, v in table.items()}), flush=True)
