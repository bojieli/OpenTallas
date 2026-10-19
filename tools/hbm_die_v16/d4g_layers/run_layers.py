#!/usr/bin/env python3
"""H-D4G3b 10-18: GEN1 pre-relay netlist = GEN0 contract -> l1 (host / x-load / stack services) -> l2 (SU / SFU) ->
l3 (VM / HC / COLL) -> l4 (IDX quad client) -> l5 (host endpoint), in this order (each layer is a contract post-layer IN OUT --report R).  Fails on the first layer
that fails.  The relay layer is spliced after this (d4g_relay_splice.py), on the GEN0 case pins.
    run_layers.py GEN0_contract.json.gz OUT.json.gz --report-dir DIR"""
import argparse, gzip, json, shutil, subprocess, sys, tempfile
from pathlib import Path

H = Path(__file__).resolve().parent
LAYERS = ['l3_vm_hc_coll.py', 'l1_host_xload_stack.py', 'l2_su_sfu.py',  # l1 reads the q0 SE/NE banks + vmdel_<E> that l3 makes
          'l4_idx_quad.py',  # HBM-RTL4 10-18 (e0c0120fd): IDX quad client; addresses l3's SE/NE banks + l1/l2 output
          'l5_rebind.py']  # H-D4G5/REBIND 10-18: port-identical rebinds (qdq split, fs wrappers, kshare splitstrap, VM SW/NW tiles, pg r5)
LAYERS += ['l5_host_ep.py']  # H-D4G5/HOSTEP 10-18 (0gd): host_cp endpoint -> hfd_ep_static (retires lk_ep / face / phy_adapt)
LAYERS += ['l5b_cij4.py']  # H-D4G GEN2 10-18 (0gl): cij in all 4 quadrants (IDX tx 4-sink fork tree) + SET 2 VM tile slots
LAYERS += ['l6_collq.py']  # H-D4G GEN2 10-18: COLL gather master (HBM-COLLQ) + ring B stops (HBM-RTL4), from the committed binding records
LAYERS += ['l7_wire.py']  # HBM-WIRE 10-18: functional check (d4g_functional_bind.py) + cxij SE/NW/NE inject slot behind cij + gap sync
ap = argparse.ArgumentParser(); ap.add_argument('inp'); ap.add_argument('out'); ap.add_argument('--report-dir', required=True)
a = ap.parse_args()
R = Path(a.report_dir); R.mkdir(parents=True, exist_ok=True)
T = Path(tempfile.mkdtemp(prefix='d4g_layers_'))
cur = T / 'c0.json'
cur.write_bytes(gzip.open(a.inp).read() if a.inp.endswith('.gz') else Path(a.inp).read_bytes())
for k, l in enumerate(LAYERS, 1):
    nxt = T / f'c{k}.json'
    r = subprocess.run([sys.executable, str(H / l), str(cur), str(nxt), '--report', str(R / (Path(l).stem + '.json'))])
    if r.returncode or not nxt.exists():
        print('LAYER FAIL', l, r.returncode); sys.exit(1)
    print('LAYER OK', l)
    cur = nxt
with open(cur, 'rb') as f, gzip.open(a.out, 'wb') as g:
    shutil.copyfileobj(f, g)
c = json.load(open(cur)); print('PRE_RELAY instances', len(c['instances']), 'edges', len(c['edges']))
shutil.rmtree(T)
