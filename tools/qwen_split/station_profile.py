"""Explicit M5-only station diagnostic; native launch/capture failures remain open."""
import hashlib
import os
import re
from pathlib import Path
from qwen_split.source_pin_plan import rtl_ports
ROOT = Path(__file__).resolve().parents[2]
SOURCE = 'rtl/qwen_sys/dvm_20261014/qfd_xcst_m5.sv'
MASTERS = ('qfd_xcst_s_m5', 'qfd_xcst_n_m5')
VIEWS = {m: f'physical/ref_tile/{m}/views/{m}' for m in MASTERS}

def selected():
    profile = os.environ.get('OT_SPLIT_STATION_PROFILE', 'legacy')
    if profile not in ('legacy', 'm5c_diagnostic'):
        raise ValueError(f'unknown station profile {profile}')
    return profile == 'm5c_diagnostic'

def geometry(master):
    path = ROOT / VIEWS[master] / (master + '.lef')
    text = path.read_text()
    size = re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)', text)
    pins = {}
    for q in re.finditer(r'^\s*PIN (\S+)\s*$(.*?)^\s*END \1\s*$', text, re.M | re.S):
        if q[1] in ('VDD', 'VSS'): continue
        rs = re.findall(r'LAYER (\S+) ;\s*RECT ([-\d. ]+) ;', q[2])
        if len(rs) != 1: raise ValueError(f'{master}.{q[1]}: expected one real rectangle')
        pins[q[1]] = (rs[0][0], tuple(map(float, rs[0][1].split())))
    ports = rtl_ports(ROOT / SOURCE, master)
    expected = {p if n == 1 else f'{p}[{b}]' for p,(n,_) in ports.items() for b in range(n)}
    if set(pins) != expected: raise ValueError(f'{master}: real LEF/RTL port mismatch {set(pins)^expected}')
    return tuple(map(float, size.groups())), ports, pins, hashlib.sha256(path.read_bytes()).hexdigest()

def apply(model):
    if not selected(): return None
    views = {}
    for master in MASTERS:
        wh, _, _, sha = geometry(master)
        old = master[:-3]
        for i in model['insts']:
            if i.master == old:
                i.master, i.w, i.h = master, *wh
        views[master] = dict(outline_um=wh, lef_sha256=sha, view=VIEWS[master])
    receipt = dict(profile='m5c_diagnostic', qualified=False,
                   native_status='FAIL: south launch224.724>220; north launch235.545>220/capture206.754>190',
                   source=SOURCE, source_sha256=hashlib.sha256((ROOT/SOURCE).read_bytes()).hexdigest(), views=views,
                   my_station_shift_nm=0, actual_pair_reach='OPEN', pg_connectivity='OPEN')
    model['station_profile'] = receipt
    return receipt

def install_masters(M, model, Master):
    if not model.get('station_profile'): return
    for master in MASTERS:
        wh, ports, pins, _ = geometry(master)
        q = Master(master, *wh, 5, 'Actual M5-only station view; diagnostic native timing FAIL')
        q.assigned_fragment_rects = {}
        for p, (n, _) in ports.items():
            rects = [pins[p if n == 1 else f'{p}[{b}]'] for b in range(n)]
            layers = {L for L,_ in rects}
            if len(layers) != 1: raise ValueError(f'{master}.{p}: mixed physical layers')
            q.ports[p] = ('xy', n, rects[0][0], [((a+c)/2,(b+d)/2) for _,(a,b,c,d) in rects], 1)
            q.order.append(p)
            q.assigned_fragment_rects[p] = rects
        M[master] = q
        if not any(i.master == master[:-3] for i in model['insts']): M.pop(master[:-3], None)
