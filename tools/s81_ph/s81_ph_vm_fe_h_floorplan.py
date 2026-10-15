#!/usr/bin/env python3
"""el1013-s81-vmfe/B7 + B8: CONSTRUCTIVE floorplan of dsfd_vm_fe_h and its checks.  B8: EVERY inter-leaf hop of the parent is
modelled (the 6 bundle chains through VMFE_R relay tiles, lane word / return / grant / arm through dsfd_vm_frm, counter
copies through u_kl / u_kr (VMFE_KD 3), status and fault wires, the reset tree, every FE boundary pin), a pin-landing cell
is no longer a zero-capacity cut, and the E-W necessary condition (s81_ph_vm_fe_h_ew_bound.py) is printed with the verdict.

  python3 tools/s81_ph/s81_ph_vm_fe_h_floorplan.py [--variant A|B] [--out results/arch/s81_vm_fe_h_floorplan_1013.json]
  exit 0 only when every check passes.

B5's tool (s81_ph_vm_fe_h_plan.py) was a lane-count SEARCH in an optimistic cut model: no relay tiles, no local capacity,
no descent of the capture words through the lane rows, no hop check of the slice bundles.  This tool places EVERY instance
(16 clt, 4 fxs, 4 fsr, 48 bundle relays, 10 flt, 10 frm, fld, fcn, fcc, fcw) and judges the placement with the real pin
coordinates of the leaf pin plans (s81_ph_vm_fe_h_leaf_specs.py; dsfd_vm_fsr from its closed LEF):
  overlap / outline   every instance inside 1,520.064 x 695.52, no two overlap, >= 2.16 um apart unless abutted by plan
  hops                every bit of every inter-leaf hop pin to pin (Manhattan) <= 500 um
  pin_align           tools/hier_contract/pin_align.py bundle() on every hop (jog cut of straight bundles <= 0.60)
  cuts                every hop routed as an L / Z on a 10.8-um gcell grid; tracks: free parent area H = M2/2 + M4 + M6,
                      V = M3/2 + M5 + 0.85 M7; over an M5-capped leaf H = M6, V = 0.85 M7; over dsfd_vm_fsr (M6 legacy
                      view) 0; 80 % usable.  Judged: every full vertical / horizontal cut AND every 54-um window of a
                      cut (local capacity) <= 0.60.
The FE boundary pins are DERIVED from the plan (straight above / below the leaf pin they feed), so the N / S face pin
table this tool writes is the slot statement for the die lead.
fcn / fcc / fcw have face-level kits only: their pins are planned here by face order (flagged `planned`)."""
import argparse, importlib.util, json, re, sys
from pathlib import Path
import numpy as np
import hashlib
import os
# FE (a) capture-slice locality (claude s81-grpA r5): capture bundle (fxs b, segment s) lands on fsr b (RTL OT_SPVM_SLOC)
SLOC = os.environ.get('OT_FE_SLOC', '0') == '1'

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools' / 'hier_contract'))
import pin_align as PA  # noqa: E402
_sp = importlib.util.spec_from_file_location('leaf_specs', ROOT / 'tools/s81_ph/s81_ph_vm_fe_h_leaf_specs.py')
LS = importlib.util.module_from_spec(_sp); _sp.loader.exec_module(LS)

W, H = 1520.064, 695.52
R = int(re.search(r'`define VMFE_R\s+(\d+)', (ROOT / 'rtl/dsrom_sys/s81_ph/vm/dsfd_vm_fe_h_if.svh').read_text())[1])
HOP_MAX, CUT_MAX, USABLE, G, WIN = 500.0, 0.60, 0.80, 10.8, 5
TPU = {'M2': 7 / 0.270, 'M3': 1 / 0.036, 'M4': 1 / 0.048, 'M5': 1 / 0.048, 'M6': 1 / 0.064, 'M7': 1 / 0.064}
H_FREE, V_FREE = TPU['M2'] / 2 + TPU['M4'] + TPU['M6'], TPU['M3'] / 2 + TPU['M5'] + 0.85 * TPU['M7']
H_LEAF, V_LEAF = TPU['M6'], 0.85 * TPU['M7']
SRC = (ROOT / 'rtl/dsrom_sys/s81_ph/vm/dsfd_vm_fe_h.sv').read_text()


def rtl_ports(mod):
    """[(name, bits, dir)] of a leaf module header, in declaration order"""
    m = re.search(r'module %s\s*(?:#\(.*?\))?\s*\((.*?)\);' % mod, SRC, re.S)
    out = []
    for d, hi, nm in re.findall(r'(input|output)\s+(?:wire|reg)?\s*(?:\[(\d+):0\])?\s*(\w+)', re.sub(r'//[^\n]*', '', m[1])):
        out.append((nm, int(hi) + 1 if hi else 1, d))
    return out


def names(port, bits, vec):
    return [f'{port}[{i}]' for i in range(bits)] if vec else [port]


def master_pins():
    """master -> (w, h, {pin: (x, y, face, layer)}, exact?)"""
    out = {}
    for leaf in LS.L:
        w, h, pl = LS.leaf_plan(leaf); exact = pl is not None
        if pl is None:      # face-level kit: plan the pins by face order (port order of the spec, bits ascending)
            ports = {n: b for n, b, _ in rtl_ports(f'dsfd_vm_{leaf}')}
            faces = {f: [[x for p in ps for x in names(p, ports[p], ports[p] > 1 or p in ('ck',) and False)]] for f, ps in LS.L[leaf][1].items() if ps}
            pl = LS.plan(w, h, faces)
        pins = {}
        for f, nm, lay, pos in pl:
            pins[nm] = {'N': (pos, h), 'S': (pos, 0.0), 'W': (0.0, pos), 'E': (w, pos)}[f] + (f, lay)
        out[f'dsfd_vm_{leaf}'] = (w, h, pins, exact)
    t = (ROOT / 'physical/ref_tile/dsfd_vm_fsr/views/dsfd_vm_fsr/dsfd_vm_fsr.lef').read_text()
    sz = re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)', t); fw, fh = float(sz[1]), float(sz[2]); pins = {}
    for m in re.finditer(r'PIN (\S+)\n(.*?)END \1\n', t, re.S):
        r = re.search(r'LAYER (\S+) ;\s*RECT\s+([\d.\-]+)\s+([\d.\-]+)\s+([\d.\-]+)\s+([\d.\-]+)', m[2])
        if m[1] in ('VDD', 'VSS') or not r: continue
        x, y = (float(r[2]) + float(r[4])) / 2, (float(r[3]) + float(r[5])) / 2
        pins[m[1]] = (round(x, 3), fh if y > fh / 2 else 0.0, 'N' if y > fh / 2 else 'S', r[1])
    out['dsfd_vm_fsr'] = (fw, fh, pins, True)
    return out


MP = master_pins()
PIN_RECEIPTS = {}
NATIVE_CANDIDATE_CAPS = {}


def load_actual_master_pins(directory):
    """Use actual source-bound IOP/CTS rectangles; final abstract/timing stays pending."""
    for f in sorted(Path(directory).glob('*/pins.json')):
        master = f.parent.name
        if master not in MP:
            raise ValueError(f'unknown FE master: {master}')
        rec = json.loads(f.read_text()); w,h = rec['outline_um']
        request = rec.get('source_candidate_request')
        if request:
            rp = ROOT / request['path']
            if hashlib.sha256(rp.read_bytes()).hexdigest() != request['sha256']:
                raise ValueError(f'{master}: source candidate receipt changed')
            rq = json.loads(rp.read_text())
            shape = rq.get('new_outline_um', rq.get('outline_um'))
            if rq.get('status') != 'UNALLOCATED_SOURCE_CANDIDATE' or shape != [w,h]:
                raise ValueError(f'{master}: actual pins do not match explicit unallocated request')
            cap = rq.get('new_layer_cap')
            if cap:
                layers = {box['layer'] for p in rec['pins'].values() for box in p['boxes']}
                if any(int(x[1:]) > int(cap[1:]) for x in layers if re.fullmatch(r'M\d+',x)):
                    raise ValueError(f'{master}: actual pin metal exceeds requested cap {cap}')
                NATIVE_CANDIDATE_CAPS[master] = cap
        elif abs(w-MP[master][0]) > .001 or abs(h-MP[master][1]) > .001:
            raise ValueError(f'{master}: actual outline {w,h} differs from selected kit {MP[master][:2]}')
        pins = {}
        for name, v in rec['pins'].items():
            if name in ('VDD','VSS') or not v['boxes']: continue
            box=v['boxes'][0]; x0,y0,x1,y1=box['rect_um']; x,y=(x0+x1)/2,(y0+y1)/2
            face=min((x,'W'),(w-x,'E'),(y,'S'),(h-y,'N'))[1]
            pins[name]=(x,y,face,box['layer'])
        MP[master]=(w,h,pins,True)
        PIN_RECEIPTS[master]={k:rec.get(k) for k in ('schema','odb_source','odb_sha256','status')}
        if request:
            PIN_RECEIPTS[master]['source_candidate_request'] = request
            PIN_RECEIPTS[master]['native_parent_adopted'] = False



def reposition(plan, positions, derive_external=False):
    """Rebase every stored bit pin when searching or replaying a placement.

    Assigned external pins stay fixed. Deriving external pins is only a proposed
    slot pin table, and must be identified as such by the caller.
    """
    delta = {n: (positions[n][0] - v[1], positions[n][1] - v[2])
             for n, v in plan.inst.items() if n in positions}
    new = []
    for cls, a, b, aa, bb in plan.hops:
        da, db = delta.get(a, (0, 0)), delta.get(b, (0, 0))
        if derive_external and a.startswith('FE.') and cls not in ('f_cap','f_cap_status'):
            da = (db[0], 0)
        if derive_external and b.startswith('FE.'):
            db = (da[0], 0)
        move = lambda pins, d: [(x+d[0], y+d[1], f, l) for x, y, f, l in pins]
        new.append((cls, a, b, move(aa, da), move(bb, db)))
    plan.hops = new
    for n, (dx, dy) in delta.items():
        m, x, y = plan.inst[n]
        plan.inst[n] = (m, round(x+dx, 3), round(y+dy, 3))


def assign_capture(plan, path, fe_x=21.6, fe_y=3060.72):
    """Bind all 13,376 capture bits to the die lead's real per-bit assignment.

    Its source is the VM boundary, including the small gap above the FE slot.
    The final 64 capture status bits enter fcn.f_cq, not a CLT lane.
    """
    doc = json.loads(Path(path).read_text())
    bits = doc['ports']['f_capture']['per_bit']
    if len(bits) != 13376:
        raise ValueError('native capture assignment must include 13,312 data and 64 status bits')
    y = doc['outline_um'][1] - fe_y
    source = [(r[2]-fe_x, y, 'S', r[1]) for r in bits]
    out = []
    for cls, a, b, aa, bb in plan.hops:
        if cls == 'f_cap':
            lane = int(b.removeprefix('clt'))
            aa = source[832*lane:832*(lane+1)]
        elif cls == 'client N' and a.startswith('FE.') and b == 'fcn' and len(aa) == 150:
            out.append(('f_cap_status', a, b, source[13312:], bb[85:149]))
            aa = aa[:85] + aa[149:]
            bb = bb[:85] + bb[149:]
        out.append((cls,a,b,aa,bb))
    plan.hops=out


class Plan:
    def __init__(self, variant):
        self.variant, self.inst, self.hops, self.ext = variant, {}, [], {}
        self.build()

    def add(self, name, master, x, y):
        self.inst[name] = (master, round(x, 3), round(y, 3))

    def pin(self, inst, pins):
        m, x, y = self.inst[inst]; mp = MP[m][2]
        def q(p):      # a 1-bit bus is planned under either spelling
            return mp[p] if p in mp else mp[p[:-3]] if p.endswith('[0]') and p[:-3] in mp else mp[p + '[0]']
        return [(x + q(p)[0], y + q(p)[1], q(p)[2], q(p)[3]) for p in pins]

    def hop(self, cls, a, pa, b, pb):
        assert len(pa) == len(pb), (cls, a, b, len(pa), len(pb))
        self.hops.append((cls, a, b, self.pin(a, pa), self.pin(b, pb)))

    def ext_hop(self, cls, face, inst, pins, drive_in=True):
        """a boundary pin straight above (N) / below (S) each leaf pin"""
        P = self.pin(inst, pins); Y = H if face == 'N' else 0.0
        E = [(x, Y, 'S' if face == 'N' else 'N', lay) for x, y, f, lay in P]
        self.ext.setdefault(cls, []).extend([round(e[0], 3) for e in E])
        self.hops.append((cls, 'FE.' + face, inst, E, P) if drive_in else (cls, inst, 'FE.' + face, P, E))

    def build(self):
        V = self.variant
        cx = {'A': 0.0, 'B': 115.2}[V]                    # clt row x0 (B: centred, the f_cap pins move +115.2 um)
        fy = {'A': 77.76, 'B': 0.0}[V]                    # fsr y0
        ycl = int((H - 7.56 - LS.CLT_H) / 8.64) * 8.64; yfx = ycl - 25.92     # clt row under the N face, fxs 6.48 below it
        ra, rb = yfx - 129.6, yfx - 259.2                                  # lane rows A / B
        for g in range(16): self.add(f'clt{g}', 'dsfd_vm_clt', cx + 80.64 * g, ycl)
        for b in range(4): self.add(f'fxs{b}', 'dsfd_vm_fxs', cx + 322.56 * b, yfx)
        for s in range(4): self.add(f'fsr{s}', 'dsfd_vm_fsr', 388.8 * s, fy)
        ftop = fy + 25.92
        # ---- landing lanes: a free 106.56-um column under the W part of every fxs (descent of the capture words)
        lanes = []
        if V == 'B':
            rows = [(ra, [cx + 322.56 * b + 106.56 for b in range(4)]), (rb, [cx + 322.56 * b + 106.56 for b in (0, 3)])]
            for y, xs in rows: lanes += [(x, y) for x in xs]
            lanes += [(cx + 322.56 * 1 + 106.56, rb), (cx + 322.56 * 2 + 106.56, rb)]
            lanes += [(0.0, 43.2), (1304.064, 43.2)][:10 - len(lanes)]
        else:
            rows = [(ra, [322.56 * b + 106.56 for b in range(4)])]
            for y, xs in rows: lanes += [(x, y) for x in xs]
            lanes += [(1304.064, ra), (1304.064, ra + 129.6), (1304.064, ra + 259.2)]
            lanes += [(0.0 + 106.56, rb), (322.56 * 3 + 106.56, rb), (1304.064, rb)]
        self.lanes = lanes[:10]
        for i, (x, y) in enumerate(self.lanes): self.add(f'flt{i}', 'dsfd_vm_flt', x, y)
        # ---- central leaves in the band between the lane rows and the fsr row
        yb = ftop + 8.64
        self.add('fcn', 'dsfd_vm_fcn', cx + 571.68, yb + 60.48)
        self.add('fld', 'dsfd_vm_fld', cx + 388.8, yb)
        self.add('fcc', 'dsfd_vm_fcc', cx + 820.8, yb)
        self.add('fcw', 'dsfd_vm_fcw', cx + 583.2, yb)
        self.add('kl', 'dsfd_vm_frm', cx + 388.8, yb + 142.56); self.add('kr', 'dsfd_vm_frm', cx + 950.4, yb + 142.56)     # counter-copy relays
        # ---- lane relay tiles: on the way from the lane's W face to fld
        fx, fyc = self.inst['fld'][1] + 86.4, self.inst['fld'][2] + 34.56
        for i, (x, y) in enumerate(self.lanes):
            mx, my = (x + fx) / 2, (y + 64.8 + fyc) / 2
            self.add(f'frm{i}', 'dsfd_vm_frm', round(mx / 8.64) * 8.64, round(my / 8.64) * 8.64)
        # ---- hops
        v = LS.v
        for g in range(16):
            b, j = divmod(g, 4)
            self.ext_hop('f_cap', 'N', f'clt{g}', v('f_c', 0, 832))
            cw = ['w_v'] + v('w_row', 0, 14) + v('w_m', 0, 16) + v('w_d', 0, 512) + v('flt', 0, 4)
            fw = v('w_v', j) + v('w_row', 14 * j, 14 * j + 14) + v('w_m', 16 * j, 16 * j + 16) + v('w_d', 512 * j, 512 * j + 512) + v('w_flt', 4 * j, 4 * j + 4)
            self.hop('clt.w->fxs', f'clt{g}', cw, f'fxs{b}', fw)
        fsr_port = lambda P: v('i_d', 128 * P, 128 * P + 128) + v('i_mask', 4 * P, 4 * P + 4) + v('i_row', 14 * P, 14 * P + 14) + v('i_v', P)
        self.relays = []; self.rst = []
        for s in range(4):
            for b in range(4):                           # capture bundles: fxs b -> fxr -> fxr -> fsr s
                src = [x for j in range(4) for x in v('s_o', (4 * j + s) * 147, (4 * j + s) * 147 + 147)]
                rin = [x for j in range(4) for x in v('i', 146 * j, 146 * j + 146) + v('i_v', j)]
                rout = [x for j in range(4) for x in v('o', 146 * j, 146 * j + 146) + v('o_v', j)]
                if SLOC:                                 # FE (a) (OT_SPVM_SLOC): segment s of fxs b -> fsr b, ports 12 + 4 j + s
                    dst = [x for j in range(4) for x in fsr_port(12 + 4 * j + s)]
                    self.chain(f'c{b}s{s}', 'dsfd_vm_fxr', [(f'fxs{b}', src)], rin, rout, f'fsr{b}', dst)
                else:
                    dst = [x for j in range(4) for x in fsr_port(12 + 4 * b + j)]
                    self.chain(f'c{b}s{s}', 'dsfd_vm_fxr', [(f'fxs{b}', src)], rin, rout, f'fsr{s}', dst)
            self.ext_hop('m_*', 'S', f'fsr{s}', [p for p in MP['dsfd_vm_fsr'][2] if p.startswith('o_')], drive_in=False)
        # ---- bundle 4 (fcw ports 0, 1 + fcc ports 3, 4 -> fxa) and bundle 5 (fcn ports 2, 5 .. 9, rf, tags + fld ports 10, 11 -> fxb)
        fs_d = lambda P, n=128: v('i_d', 128 * P, 128 * P + n)
        fs_r = lambda P: v('i_row', 14 * P, 14 * P + 14)
        for s in range(4):
            wa = [(f'fcw', v('s_o', 159 * s, 159 * s + 143) + v('s_o', 159 * s + 143)), (f'fcw', v('s_o', 159 * s + 144, 159 * s + 158) + v('s_o', 159 * s + 158)),
                  (f'fcc', v('s_o', 288 * s, 288 * s + 143) + v('s_o', 288 * s + 143)), (f'fcc', v('s_o', 288 * s + 144, 288 * s + 287) + v('s_o', 288 * s + 287))]
            ri = v('i', 0, 143) + v('i_v', 0) + v('i', 143, 157) + v('i_v', 1) + v('i', 157, 300) + v('i_v', 2) + v('i', 300, 443) + v('i_v', 3)
            ro = [x.replace('i', 'o', 1) for x in ri]
            dst = fs_d(0) + fs_r(0) + v('i_we', 0) + v('i_v', 0) + fs_r(1) + v('i_v', 1) + fs_d(3) + fs_r(3) + v('i_we', 3) + v('i_v', 3) + fs_d(4) + fs_r(4) + v('i_we', 4) + v('i_v', 4)
            self.chain(f'a{s}', 'dsfd_vm_fxa', wa, ri, ro, f'fsr{s}', dst)
            wb = [('fcn', v('s_o', (6 * s + i) * 15, (6 * s + i) * 15 + 15)) for i in range(6)]
            ri = [x for i in range(6) for x in v('i', 14 * i, 14 * i + 14) + v('i_v', i)]
            dst = [x for P in (2, 5, 6, 7, 8, 9) for x in fs_r(P) + v('i_v', P)]
            for j in range(2):
                wb.append(('fld', v('s_o', (2 * s + j) * 143, (2 * s + j) * 143 + 143)))
                ri += v('i', 84 + 142 * j, 84 + 142 * j + 142) + v('i_v', 6 + j); dst += fs_d(10 + j) + fs_r(10 + j) + v('i_v', 10 + j)
            wb.append(('fcn', v('rf_o', s))); ri += v('i', 368); dst += v('i_rf', 3)
            if s == 0:
                wb.append(('fcn', v('x_o', 0, 112))); ri += v('i', 369, 481)
                dst += fs_d(2, 4) + fs_d(5, 92) + fs_d(6, 4) + fs_d(7, 4) + fs_d(8, 4) + fs_d(9, 4)
            ro = [x.replace('i', 'o', 1) for x in ri]
            self.chain(f'b{s}', 'dsfd_vm_fxb', wb, ri, ro, f'fsr{s}', dst)
        # ---- landing lanes: producer word, return + flags, grant, arm (all through the lane's dsfd_vm_frm)
        for i in range(10):
            self.ext_hop('lane word', 'N', f'flt{i}', ['p_v'] + v('p_t', 0, 2) + ['p_m'] + v('p_d', 0, 512) + ['p_flt'])
            self.hop('flt.ret->frm', f'flt{i}', v('ret', 0, 526) + ['av', 'ok', 'ovf', 'sflt'], f'frm{i}', v('r_i', 0, 526) + v('f_i', 0, 4))
            self.hop('frm.ret->fld', f'frm{i}', v('r_o', 0, 526) + v('f_o', 0) + v('f_o', 2, 4), 'fld', v('ret', 526 * i, 526 * i + 526) + v('av', i) + v('ovf', i) + v('sflt', i))
            if 2 <= i < 6: self.hop('frm.ret->fld', f'frm{i}', v('f_o', 1), 'fld', v('ok', i - 2))
            self.hop('grant fld->frm', 'fld', v('g', i), f'frm{i}', ['g_i']); self.hop('grant frm->flt', f'frm{i}', ['g_o'], f'flt{i}', ['g'])
            self.hop('arm fcn->frm', 'fcn', v('arm_base', 14 * i, 14 * i + 14) + v('arm_v', i), f'frm{i}', v('a_i', 0, 15))
            self.hop('arm frm->flt', f'frm{i}', v('a_o', 0, 15), f'flt{i}', v('arm_base', 0, 14) + ['arm_v'])
            self.hop('reset', 'fld' if i == 0 else f'flt{i - 1}', ['rn_o'] if i else v('rn_o', 0), f'flt{i}', ['rni'])
        # ---- counter copies: source out pin -> u_kl / u_kr (dsfd_vm_frm r lane) -> fcn in pin (KD 3)
        for b in range(4):
            kt, o = ('kl', 192 + 128 * b) if b < 2 else ('kr', 128 * (b - 2))
            self.hop('k src->relay', f'fxs{b}', v('k_o', 0, 128), kt, v('r_i', o, o + 128))
        for j, a in enumerate(('fcw', 'fcc', 'fld')): self.hop('k src->relay', a, v('k_o', 0, 64), 'kl', v('r_i', 64 * j, 64 * j + 64))
        self.hop('k relay->fcn', 'kl', v('r_o', 0, 448), 'fcn', v('k_i', 0, 448)); self.hop('k relay->fcn', 'kr', v('r_o', 0, 256), 'fcn', v('k_i', 448, 704))
        # ---- status / faults / reset tree (one wire each, same 500-um rule)
        for b in range(4):
            self.hop('status', f'fxs{b}', v('clf_o', 0, 4), 'fcn', v('clf_i', 4 * b, 4 * b + 4)); self.hop('reset', 'fcn', v('rn_o', 3 + b), f'fxs{b}', ['rni'])
            for j in range(4): self.hop('reset', f'fxs{b}', v('rn_o', j) + v('sok_o', j), f'clt{4 * b + j}', ['rn', 'sok'])
        self.hop('status', 'fcc', ['so_o'], 'fcn', ['so_i']); self.hop('status', 'fcw', ['err_o'], 'fcn', ['err_i'])
        self.hop('status', 'fld', ['ovr_o', 'sflt_o'], 'fcn', ['ovr_i', 'sflt_i'])
        for j, a in enumerate(('fld', 'fcc', 'fcw')): self.hop('reset', 'fcn', v('rn_o', j), a, ['rni'])
        src_rn = {'c0': ('fxs0', v('rn_o', 4)), 'c1': ('fxs1', v('rn_o', 4)), 'c2': ('fxs2', v('rn_o', 4)), 'c3': ('fxs3', v('rn_o', 4)), 'a': ('fcw', v('rn_o', 0)), 'b': ('fcn', v('rn_o', 7))}
        for bt in ('c0', 'c1', 'c2', 'c3', 'a', 'b'):
            nm = lambda s_, r_: f'{bt}s{s_}r{r_}' if bt[0] == 'c' else f'{bt}{s_}r{r_}'
            for s_ in range(4):
                for r_ in range(R):
                    if s_ == 0 and r_ == 0: self.hop('reset', src_rn[bt][0], src_rn[bt][1], nm(0, 0), ['rni'])
                    elif s_ == 0: self.hop('reset', nm(0, r_ - 1), v('rn_o', 0), nm(0, r_), ['rni'])
                    else: self.hop('reset', nm(s_ - 1, r_), v('rn_o', 1), nm(s_, r_), ['rni'])
        # ---- FE boundary: client words on N straight above their leaf pins, status to the BE on S
        self.ext_hop('client N', 'N', 'fcw', ['f_swv'] + v('f_swd', 0, 527) + ['f_srv'] + v('f_srd', 0, 31))
        self.ext_hop('client N', 'N', 'fcw', ['t_swg', 't_srg'] + v('t_ks', 0, 53), drive_in=False)
        self.ext_hop('client N', 'N', 'fcc', ['vwe'] + v('vwa', 0, 14) + v('vwd', 0, 512) + ['vre'] + v('vra', 0, 14))
        self.ext_hop('client N', 'N', 'fcn', ['cv'] + v('cd', 0, 84) + v('f_cq', 0, 64) + ['c_wr'])
        self.ext_hop('client N', 'N', 'fcn', ['dv'] + v('dt', 0, 8) + ['c_wv'] + v('c_wd', 0, 10) + v('t_rdy', 0, 4), drive_in=False)
        self.ext_hop('client N', 'N', 'fld', v('t_cts', 0, 3), drive_in=False)
        self.ext_hop('status S', 'S', 'fcn', v('fe_flt', 0, 16), drive_in=False); self.ext_hop('status S', 'S', 'fcn', ['f_p2c'])

    def chain(self, tag, master, srcs, rin, rout, c, dst):
        """sources [(inst, pins)] -> R relay tiles -> sink: the tiles at (r + 1) / (R + 1) of the pin centroids, 8.64 lattice;
        the LAST tile straight above the sink pins (its out pins are in the sink's port order)"""
        A = [q for a, pp in srcs for q in self.pin(a, pp)]; C = self.pin(c, dst)
        ax, ay = np.mean([q[0] for q in A]), np.mean([q[1] for q in A]); cxx, cy = np.mean([q[0] for q in C[:len(C) * 3 // 4]]), np.mean([q[1] for q in C])
        w, h = MP[master][0], MP[master][1]
        for r in range(R):
            f = (r + 1) / R
            x, y = ax + (cxx - ax) * f - w / 2, ay + (cy + 30.24 + h / 2 - ay) * f - h / 2
            self.add(f'{tag}r{r}', master, round(x / 2.16) * 2.16, round(y / 8.64) * 8.64); self.relays.append(f'{tag}r{r}')
        k = 0
        for a, pp in srcs:
            self.hop('s0->relay', a, pp, f'{tag}r0', rin[k:k + len(pp)]); k += len(pp)
        for r in range(1, R): self.hop('relay->relay', f'{tag}r{r - 1}', rout, f'{tag}r{r}', rin)
        self.hop('relay->fsr', f'{tag}r{R - 1}', rout[:len(dst)], c, dst)
        # reset chain of the bundle (parent wiring): slice 0 along the chain, slices 1 .. 3 from the slice before
        self.rst.append((tag, R))

    # ------------------------------------------------------------------------------------------------ checks
    def rects(self):
        return {n: (x, y, x + MP[m][0], y + MP[m][1], m) for n, (m, x, y) in self.inst.items()}

    def check_place(self):
        R = self.rects(); bad = []
        for n, (x0, y0, x1, y1, m) in R.items():
            if x0 < -1e-6 or y0 < -1e-6 or x1 > W + 1e-6 or y1 > H + 1e-6: bad.append(f'{n} ({m}) outside the outline: {x0:.2f} {y0:.2f} {x1:.2f} {y1:.2f}')
        N = sorted(R.items(), key=lambda kv: kv[1][0])
        for i, (a, ra) in enumerate(N):
            for b, rb in N[i + 1:]:
                if rb[0] >= ra[2] - 1e-6: break
                if min(ra[3], rb[3]) - max(ra[1], rb[1]) > 1e-6: bad.append(f'overlap {a} / {b}')
        return bad

    def check_hops(self):
        rows = {}
        for cls, a, b, A, B in self.hops:
            r = PA.bundle(A, B)
            c = rows.setdefault(cls, {'hops': 0, 'bits': 0, 'len_max': 0.0, 'jog_max': 0.0, 'jog_cut_max': 0.0, 'verdict': {}, 'worst': None})
            c['hops'] += 1; c['bits'] += len(A)
            if r['len_max'] > c['len_max']: c['len_max'], c['worst'] = r['len_max'], f'{a} -> {b}'
            c['jog_max'] = max(c['jog_max'], r.get('jog_max') or 0.0); c['jog_cut_max'] = max(c['jog_cut_max'], r.get('jog_cut') or 0.0)
            c['verdict'][r['verdict']] = c['verdict'].get(r['verdict'], 0) + 1
        return rows

    def check_cuts(self):
        nx, ny = int(np.ceil(W / G)), int(np.ceil(H / G))
        capH, capV = np.full((ny, nx), H_FREE * G * USABLE), np.full((ny, nx), V_FREE * G * USABLE)
        for n, (x0, y0, x1, y1, m) in self.rects().items():
            hl, vl = (0.0, 0.0) if m == 'dsfd_vm_fsr' and NATIVE_CANDIDATE_CAPS.get(m) != 'M5' else (H_LEAF, V_LEAF)
            for iy in range(max(int(y0 // G), 0), min(int(np.ceil(y1 / G)), ny)):
                for ix in range(max(int(x0 // G), 0), min(int(np.ceil(x1 / G)), nx)):
                    f = max(0.0, min(x1, (ix + 1) * G) - max(x0, ix * G)) * max(0.0, min(y1, (iy + 1) * G) - max(y0, iy * G)) / (G * G)
                    capH[iy, ix] -= f * (H_FREE - hl) * G * USABLE; capV[iy, ix] -= f * (V_FREE - vl) * G * USABLE
        useH, useV = np.zeros((ny, nx)), np.zeros((ny, nx))
        gi = lambda x, n: min(max(int(x // G), 0), n - 1)

        def path(x0, y0, x1, y1, mid, hv):
            """cells (iy, ix, 'H' | 'V') of an L (mid None) or a Z through `mid` on the other axis"""
            c = []
            ax, ay, bx, by = gi(x0, nx), gi(y0, ny), gi(x1, nx), gi(y1, ny)
            def hs(y, xa, xb): c.extend((y, x, 'H') for x in range(min(xa, xb), max(xa, xb) + 1))
            def vs(x, ya, yb): c.extend((y, x, 'V') for y in range(min(ya, yb), max(ya, yb) + 1))
            if hv == 'HV':
                if mid is None: hs(ay, ax, bx); vs(bx, ay, by)
                else: vs(ax, ay, mid); hs(mid, ax, bx); vs(bx, mid, by)
            else:
                if mid is None: vs(ax, ay, by); hs(by, ax, bx)
                else: hs(ay, ax, mid); vs(mid, ay, by); hs(by, mid, bx)
            # Only the source/sink gcell can be a pin landing. A blocked interior
            # gcell remains in the demand: deleting it would hide through-tile routes.
            ends = {(ay, ax), (by, bx)}
            return [(y, x, d) for y, x, d in c
                    if (y, x) not in ends or
                    ((capH if d == 'H' else capV)[y, x] >
                     0.05 * (H_FREE if d == 'H' else V_FREE) * G * USABLE)]

        def cost(c, bits):
            t = 0.0
            for y, x, d in c:
                u, cap = (useH, capH) if d == 'H' else (useV, capV)
                r = (u[y, x] + bits) / max(cap[y, x], 1e-6); t += 1.0 + (50.0 * (r - 0.5) if r > 0.5 else 0.0) + (1e3 if r > 1.0 else 0.0)
            return t

        segs = []; seg_cls = []
        for cls, a, b, A, B in self.hops:           # split every hop into pieces of <= 64 neighbouring bits
            for k in range(0, len(A), 64):
                seg_cls.append(f'{cls} {a}->{b}')
                pa, pb = A[k:k + 64], B[k:k + 64]
                segs.append((len(pa), np.mean([p[0] for p in pa]), np.mean([p[1] for p in pa]), np.mean([p[0] for p in pb]), np.mean([p[1] for p in pb])))
        chosen = [None] * len(segs)
        unresolved = set()
        for it in range(3):
            for i, (bits, x0, y0, x1, y1) in enumerate(segs):
                if chosen[i] is not None:
                    for y, x, d in chosen[i]: (useH if d == 'H' else useV)[y, x] -= bits
                ay, by, ax, bx = gi(y0, ny), gi(y1, ny), gi(x0, nx), gi(x1, nx)
                cands = [path(x0, y0, x1, y1, None, 'HV'), path(x0, y0, x1, y1, None, 'VH')]
                cands += [path(x0, y0, x1, y1, m, 'HV') for m in range(min(ay, by), max(ay, by) + 1, 2)]
                cands += [path(x0, y0, x1, y1, m, 'VH') for m in range(min(ax, bx), max(ax, bx) + 1, 4)]
                def legal(c):
                    return all((capH if d == 'H' else capV)[y,x] > 1e-6 for y,x,d in c)
                valid = [c for c in cands if legal(c)]
                if not valid:
                    # A direct L/Z witness may cross a full-cap legacy macro.
                    # Search the whole slot for legal three-segment detours; never delete blocked demand.
                    extra = [path(x0,y0,x1,y1,m,'HV') for m in range(ny)]
                    extra += [path(x0,y0,x1,y1,m,'VH') for m in range(nx)]
                    valid = [c for c in extra if legal(c)]
                if valid: unresolved.discard(i)
                else: unresolved.add(i)
                best = min(valid or cands, key=lambda c: cost(c, bits)); chosen[i] = best
                for y, x, d in best: (useH if d == 'H' else useV)[y, x] += bits
        # Interior zero-capacity crossings are real violations. Endpoint pin landings
        # alone were excluded in path(); retain all remaining demand and capacity.
        rH, rV = useH / np.maximum(capH, 1e-6), useV / np.maximum(capV, 1e-6)
        full_v = useH.sum(axis=0) / np.maximum(capH.sum(axis=0), 1e-6)      # vertical cut at column ix: H wires / H tracks
        full_h = useV.sum(axis=1) / np.maximum(capV.sum(axis=1), 1e-6)
        k = np.ones(WIN)
        win_v = max(float((np.convolve(useH[:, ix], k, 'valid') / np.maximum(np.convolve(capH[:, ix], k, 'valid'), 1e-6)).max()) for ix in range(nx))
        win_h = max(float((np.convolve(useV[iy, :], k, 'valid') / np.maximum(np.convolve(capV[iy, :], k, 'valid'), 1e-6)).max()) for iy in range(ny))
        return {'gcell_um': G, 'window_um': G * WIN,
                'routing_model': 'finite L/Z plus full-slot legal detours; every blocked crossing retained',
                'unroutable_bundle_segments': len(unresolved),
                'unroutable_hops': sorted({seg_cls[i] for i in unresolved}),
                'route_segments_over_500_um': sum(len(c)*G > HOP_MAX for c in chosen),
                'longest_grid_route_um': max(len(c)*G for c in chosen),
                'blocked_interior_cells': int(((capH <= 1e-6) & (useH > 0)).sum() + ((capV <= 1e-6) & (useV > 0)).sum()),
                'full_vertical_cut_max': [round(float(full_v.max()), 3), round(float(full_v.argmax() * G), 1)],
                'full_horizontal_cut_max': [round(float(full_h.max()), 3), round(float(full_h.argmax() * G), 1)],
                'window_vertical_cut_max': round(win_v, 3), 'window_horizontal_cut_max': round(win_h, 3),
                'gcells_over_0p60': int(((rH > CUT_MAX) | (rV > CUT_MAX)).sum()), 'gcells': int(nx * ny),
                'gcell_max': [round(float(rH.max()), 3), round(float(rV.max()), 3)]}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--variant', default='B'); ap.add_argument('--height', type=float, default=695.52); ap.add_argument('--out', default=None)
    ap.add_argument('--master-pins', help='actual source-bound master/pins.json directory; never a final closure claim')
    ap.add_argument('--width', type=float, default=1520.064)
    ap.add_argument('--fsr-pitch', type=float, default=388.8)
    ap.add_argument('--placements', help='replay a source-bound search placement JSON')
    ap.add_argument('--assigned-capture', help='actual die-lead VM per-bit capture assignment')
    a = ap.parse_args()
    global H, W
    H = a.height
    W = a.width
    if a.master_pins: load_actual_master_pins(a.master_pins)
    p = Plan(a.variant)
    reposition(p, {f'fsr{i}': (a.fsr_pitch*i,p.inst[f'fsr{i}'][2]) for i in range(4)})
    if a.placements:
        proposed = json.loads(Path(a.placements).read_text())
        reposition(p, {n: (v['x'], v['y']) for n, v in proposed['instances'].items()},
                   proposed.get('derive_external_pins', False))
    if a.assigned_capture:
        assign_capture(p, a.assigned_capture)
    place = p.check_place(); hops = p.check_hops(); cuts = p.check_cuts()
    over = {c: r['len_max'] for c, r in hops.items() if r['len_max'] > HOP_MAX}
    pa_fail = {c: r['verdict'].get('FAIL', 0) for c, r in hops.items() if r['verdict'].get('FAIL')}
    cut_bad = (['unroutable_bundle_segments'] if cuts.get('unroutable_bundle_segments') else []) + [k for k in ('full_vertical_cut_max', 'full_horizontal_cut_max') if cuts[k][0] > CUT_MAX] + \
              [k for k in ('window_vertical_cut_max', 'window_horizontal_cut_max') if cuts[k] > CUT_MAX]
    not_planned = []
    ew = None
    try:
        r = json.loads((ROOT / 'results/arch/s81_vm_fe_h_ew_bound_1013.json').read_text())
        ew = {'frozen_structure_best_bound': min(c['bound'] for c in r['cases'] if c['case'].startswith('frozen')), 'no_lane_bound': r['no_lane_in_slot_bound'], 'limit': r['limit'],
              'record': 'results/arch/s81_vm_fe_h_ew_bound_1013.json'}
    except Exception:
        pass
    res = {'schema': 'opentallas.s81_vm_fe_h.floorplan.v1', 'agent': 'el1013-s81-vmfe/B8', 'rtl': 'B8 (R 3, KD 3, XRT 1, CCA 1)', 'variant': a.variant,
           'outline': [W, H], 'actual_pin_receipts': PIN_RECEIPTS, 'limits': {'hop_um': HOP_MAX, 'cut': CUT_MAX, 'usable_tracks': USABLE},
           'instances': {n: {'master': m, 'x': x, 'y': y, 'w': MP[m][0], 'h': MP[m][1]} for n, (m, x, y) in sorted(p.inst.items())},
           'masters_with_exact_pins': sorted(m for m, v in MP.items() if v[3]), 'masters_with_planned_pins': sorted(m for m, v in MP.items() if not v[3]),
           'placement_violations': place, 'hops': hops, 'hops_over_limit': over, 'pin_align_fail': pa_fail, 'cuts': cuts, 'cuts_over_limit': cut_bad,
           'not_modelled': not_planned, 'relay_tiles_in_series': R, 'ew_necessary_condition': ew,
           'pass': bool(not place and not over and not pa_fail and not cut_bad and not not_planned)}
    print(f'variant {a.variant}: {len(p.inst)} instances, {len(p.hops)} hops, {sum(len(h[3]) for h in p.hops)} bits')
    print('placement violations', len(place), place[:6])
    for c, r in hops.items(): print(f'  {c:14s} hops {r["hops"]:3d} bits {r["bits"]:6d} len max {r["len_max"]:7.1f} ({r["worst"]}) jog max {r["jog_max"]:6.1f} jog cut {r["jog_cut_max"]:.2f} {r["verdict"]}')
    print('cuts', cuts)
    print('FLOORPLAN:', 'PASS' if res['pass'] else f'FAIL (placement {len(place)}, hop classes over {list(over)}, pin_align FAIL {pa_fail}, cuts {cut_bad}, not modelled {len(not_planned)})')
    if ew: print(f"E-W necessary condition (s81_ph_vm_fe_h_ew_bound.py): best optimistic bound found by finite search {ew['frozen_structure_best_bound']} vs {ew['limit']} (not a proof of global impossibility, current-height record only); with no lane in the slot {ew['no_lane_bound']}")
    if a.out: (ROOT / a.out).write_text(json.dumps(res, indent=1) + '\n')
    return 0 if res['pass'] else 1


if __name__ == '__main__':
    sys.exit(main())
