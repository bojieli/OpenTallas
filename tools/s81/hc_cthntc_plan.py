#!/usr/bin/env python3
"""cth_ntc parent plan + top-down pins of its NEW leaves (HC-COLUMN 10-16, option A).

Parent = ot_s81_hc_cth_ntc, 576.72 x 844.56 um, R0 rows (y from N): ctrn_col slices 0, ctnl j0 12.96 / j1 112.32,
ctpl half0 211.68, ret_column row 330.48 (h 56.16), ctfxs 386.64, ctfn banks 412.56, ctfl 447.12, ctpl half1 473.04,
ctnl j2 591.84 / j3 691.2, ctfs 790.56 (Codex 844.56 plan, the 2x30.24/25.92 return strips merged into one 56.16 leaf).
The return chain runs bottom -> top: row p's slices (its N edge) feed row p-1's return leaves (457.9 um up).

New leaves get exact pins placed against the actual pins they join (closed LEFs: ctnl l0/l1 main views, ctnl_l3 np2,
ctpl v3, ctfl_nt s6; ctnl_l2io from its pin file):
  ot_s81_hc_ret_column_c{0..3}  144.18 x 56.16   N: lanes j0/j1 + requests + slice outputs; S: lanes j2/j3 + chain + fv/fdx;
                                                 W/E: y-beat / flag / cs / hov peer nets
  ot_s81_hc_ctrn_col_{e,w}      144.18 x 12.96   S: own + partner (partner E for columns 0/1, W for 2/3); N: bundle
Pin x = the joined pin's x, then packed per face/layer at 0.096 um (M5 + M3 on N/S, M4 on W/E).
Audit: every join of a new-leaf pin (driver -> each sink) with Manhattan length; target 0 over 500 um.

    hc_cthntc_plan.py --out physical/s81_die_pins/v28_hc_cthntc
"""
import argparse, collections, json, re, statistics, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/s81'))
import v19_pins_1014 as V  # noqa: E402

H, W = 844.56, 576.72
CW, LW = 144.18, 144.72          # new-leaf column pitch / closed lane-tile pitch
RET_T, RET_H = 330.48, 56.16
SL_H = 12.96
CTNL_T = [12.96, 112.32, 591.84, 691.2]
CTNL_H = [95.04, 95.04, 99.36, 99.36]
CTPL_T = [211.68, 473.04]
CTFL_T = 447.12
PITCH = 0.096
HELD_L3 = '/home/ubuntu/artifacts/s81-hccol-0600/heldviews/ctnl_l3_native_ref-np2-granted-57b4f1931/physical/ref_tile/s81hc_ctnl_l3_native_ref/views/ot_s81_hc_ctnl_l3/ot_s81_hc_ctnl_l3.lef'


def ybot(t, h):
    return H - t - h


def tcl_bits(path):
    d = {}
    for l in open(path):
        m = re.search(r'-pin_name \{([^}]+)\} -layer (\S+) -location \{([\d.]+) ([\d.]+)\}', l)
        if m:
            nm = re.match(r'(.*?)(?:\[(\d+)\])?$', m[1])
            d.setdefault(nm[1], {})[int(nm[2] or 0)] = ('?', m[2], float(m[3]), float(m[4]))
    return d


def closed():
    lanes = []
    for l in range(4):
        if l == 2:
            lanes.append(tcl_bits(ROOT / 'physical/s81_die_pins/v28_hc_ctnl_l2io/ot_s81_hc_ctnl_l2io.tcl'))
        elif l == 3:
            lanes.append(V.lef_bits(HELD_L3)[1])
        else:
            lanes.append(V.lef_bits(f'physical/ref_tile/s81hc_ctnl_l{l}_ref/views/ot_s81_hc_ctnl_l{l}/ot_s81_hc_ctnl_l{l}.lef')[1])
    ctpl = V.lef_bits('physical/ref_tile/s81hc_ctpl_ref/views/ot_s81_hc_ctpl/ot_s81_hc_ctpl.lef')[1]
    ctfl = V.lef_bits('physical/ref_tile/s81hc_ctflnt_ref/views/ot_s81_hc_ctfl_nt/ot_s81_hc_ctfl_nt.lef')[1]
    return lanes, ctpl, ctfl


def ctnl_abs(lanes, j, l, port, bit):
    f, ly, x, y = lanes[l][port][bit]
    return LW * l + x, ybot(CTNL_T[j], CTNL_H[l]) + y


class Leaf:
    """pins of one new master: port -> list of [face, layer, desired coord] per bit; packed in place"""
    def __init__(self, name, w, h):
        self.name, self.w, self.h, self.p = name, w, h, {}

    def add(self, port, face, desired, layer=None):
        self.p.setdefault(port, []).append([face, layer, desired])

    def pack(self):
        groups = collections.defaultdict(list)
        for port, bits in self.p.items():
            for i, b in enumerate(bits):
                groups[b[0]].append((b[2], port, i))
        for face, vals in groups.items():
            length = self.w if face in 'NS' else self.h
            layers = ['M5', 'M3'] if face in 'NS' else ['M4']
            vals.sort()
            n = len(vals)
            per = (n + len(layers) - 1) // len(layers)
            # interleave layers: slot k of layer L sits at an offset PITCH/len(layers) * L
            slots = []
            cap = int((length - 0.6) / PITCH) + 1
            assert per <= cap, (self.name, face, n, cap * len(layers))
            # assign in desired order to the nearest free slot (layer-major round robin keeps order)
            prev = -1.0
            for k, (d, port, i) in enumerate(vals):
                ly = layers[k % len(layers)]
                off = (PITCH / len(layers)) * (k % len(layers))
                lo = 0.3 + off + (k // len(layers)) * PITCH
                hi = length - 0.3 - ((n - 1 - k) // len(layers)) * PITCH
                pos = max(lo, prev + PITCH / len(layers), min(d, hi))
                pos = round(round((pos - off - 0.3) / PITCH) * PITCH + 0.3 + off, 3)
                if pos <= prev:
                    pos = round(prev + PITCH / len(layers), 3)
                prev = pos
                self.p[port][i] = [face, ly, pos]

    def xy(self, port, bit, x0, y0):
        f, ly, c = self.p[port][bit]
        if f == 'N':
            return x0 + c, y0 + self.h
        if f == 'S':
            return x0 + c, y0
        if f == 'W':
            return x0, y0 + c
        return x0 + self.w, y0 + c

    def tcl(self):
        out = []
        for port, bits in sorted(self.p.items()):
            for i, (f, ly, c) in enumerate(bits):
                name = port if len(bits) == 1 and port in SCALAR else f'{port}[{i}]'
                x, y = {'N': (c, self.h - 0.042), 'S': (c, 0.042), 'W': (0.042, c), 'E': (self.w - 0.042, c)}[f]
                out.append(f'place_pin -pin_name {{{name}}} -layer {ly} -location {{{x:.3f} {y:.3f}}} -force_to_die_boundary')
        return '\n'.join(out) + '\n'


SCALAR = {'clk', 'rst_in', 'last', 'hs_run', 'hov_in', 'hov_rel', 'hov_fwd', 'hnz_n', 'hnz_s', 'pflt_n', 'pflt_s',
          'flag_fault', 'flag_hnz'}


def build():
    lanes, ctpl, ctfl = closed()
    rets = []
    for c in range(4):
        L = Leaf(f'ot_s81_hc_ret_column_c{c}', CW, RET_H)
        x0, y0 = CW * c, ybot(RET_T, RET_H)
        rel = lambda X: X - x0
        part_e = c < 2                       # partner slice / column to the E
        # lanes: hrq_col (4 j x 256), yb_loc (4 j x 16), nflt_col (4 j), requests
        for j in range(4):
            face = 'N' if j < 2 else 'S'
            for b in range(256):
                L.add('hrq_col', face, rel(ctnl_abs(lanes, j, c, 'hrq', b)[0]))
            for b in range(16):
                pass
        for k in range(4):
            face = 'N' if k < 2 else 'S'
            for b in range(16):
                L.add('yb_loc', face, rel(ctnl_abs(lanes, k, c, 'yb', b)[0]))
        for j in range(4):
            L.add('nflt_col', 'N' if j < 2 else 'S', rel(ctnl_abs(lanes, j, c, 'flt', 0)[0]))
        for port, bits in (('rq_q', 16 * 4), ('hs_run', 1), ('hs_c', 16)):
            for b in range(bits):
                L.add(port, 'N', rel(statistics.mean(ctnl_abs(lanes, j, c, port, b)[0] for j in range(4))))
        # ctpl group c flags; hov (column 0 source)
        for nm, half, face in (('hnz_n', 0, 'N'), ('pflt_n', 0, 'N'), ('hnz_s', 1, 'S'), ('pflt_s', 1, 'S')):
            L.add(nm, face, rel(LW * c + ctpl[nm[:-2] + '_d'][0][2]))
        if c == 0:
            L.add('hov_in', 'N', rel(ctpl['hov_d'][0][2]))
        else:
            L.add('hov_in', 'W', RET_H - 2.0)
        # fv-domain broadcast from ctfl (S of the row) and parent inputs
        for port, src, bits in (('fv', 'fv_local', 7), ('fdx', 'fdx_local', 104)):
            for b in range(bits):
                L.add(port, 'S', rel(ctfl[src][b][2]))
        for port, bits in (('tid', 8), ('last', 1), ('rst_in', 1)):
            for b in range(bits):
                L.add(port, 'S', CW / 2)
        # chain inputs from the previous row's slice (its N face, directly below): bundle order, own then partner
        for port, bits in (('rv_in', 8), ('hdr_in', 108), ('ao_in', 256), ('bo_in', 256)):
            for b in range(bits):
                L.add(port, 'S', 4.0 if part_e else CW - 4.0)          # packed from the edge AWAY from the partner
        for port in ('ap_in', 'bp_in'):
            for b in range(256):
                L.add(port, 'S', CW - 4.0 if part_e else 4.0)
        # outputs to this row's slices (N): own slice directly above, partner slice (c+2) across -> pack toward partner
        for port, bits in (('rvm', 8), ('hdr', 108), ('a_rdm', 256), ('b_rdm', 256)):
            for b in range(bits):
                L.add(port, 'N', CW - 2.0 if part_e else 2.0)
        # cs: column 3 takes the column-3 accumulators (E face of ctnl l3, 2 tiles above / 2 below)
        for b in range(128):
            j = b // 32
            if c == 3:
                L.add('cs_in', 'N' if j < 2 else 'S', CW - 2.0)
                L.add('cs_fwd', 'W', RET_H / 2)
            else:
                L.add('cs_in', 'E', RET_H / 2)
        if c != 3:
            L.add('cs_fwd', 'E', 1.0)                           # 1-b constant (non-relaying column)
        L.add('hov_fwd', 'E' if c == 0 else 'W', RET_H - 1.0)
        # y beat / flag peer nets on W/E toward the peer
        for b in range(64):
            L.add('yb_fwd', 'E' if c < 2 else 'W', RET_H / 2)
        for pi, pc in enumerate([x for x in range(4) if x != c]):
            for b in range(64):
                L.add('yb_peer', 'W' if pc < c else 'E', RET_H / 2)
        for p in ('flag_fault', 'flag_hnz'):
            L.add(p, 'E' if c < 2 else 'W', 5.0)
        for p in ('peer_fault', 'peer_hnz'):
            for pi, pc in enumerate([x for x in range(4) if x != c]):
                L.add(p, 'W' if pc < c else 'E', 5.0)
        L.add('clk', 'N', CW / 2)
        L.pack()
        rets.append(L)
    # slices: E (columns 0/1) and W (2/3); own pins under the ret leaf's own outputs, partner toward the partner
    slices = {}
    for kind, part_e in (('e', True), ('w', False)):
        S = Leaf(f'ot_s81_hc_ctrn_col_{kind}', CW, SL_H)
        ref = rets[0 if part_e else 2]
        for port, src in (('rv_c', 'rvm'), ('hdr_c', 'hdr'), ('a_own', 'a_rdm'), ('b_own', 'b_rdm')):
            for b in range(len(ref.p[src])):
                S.add(port, 'S', ref.p[src][b][2])
        for port in ('a_par', 'b_par'):
            for b in range(256):
                S.add(port, 'S', CW - 2.0 if part_e else 2.0)
        # N: bundle out, aligned to the ret leaf's chain inputs (same x relative to the column)
        for port, src in (('rv_out', 'rv_in'), ('hdr_out', 'hdr_in'), ('a_own_out', 'ao_in'), ('b_own_out', 'bo_in'),
                          ('a_par_out', 'ap_in'), ('b_par_out', 'bp_in')):
            for b in range(len(ref.p[src])):
                S.add(port, 'N', ref.p[src][b][2])
        S.add('clk', 'W', SL_H / 2)
        S.add('rst_in', 'W', SL_H / 2 - 1)
        S.pack()
        slices[kind] = S
    return lanes, ctpl, ctfl, rets, slices


def audit(lanes, ctpl, ctfl, rets, slices):
    joins = []
    rpos = lambda c: (CW * c, ybot(RET_T, RET_H))
    spos = lambda c: (CW * c, ybot(0, SL_H))
    skind = lambda c: 'e' if c < 2 else 'w'
    def j(kind, a, b):
        joins.append(dict(kind=kind, um=round(abs(a[0] - b[0]) + abs(a[1] - b[1]), 3)))
    for c in range(4):
        R = rets[c]; x0, y0 = rpos(c)
        for jj in range(4):
            for b in range(256):
                j('hrq', ctnl_abs(lanes, jj, c, 'hrq', b), R.xy('hrq_col', 256 * jj + b, x0, y0))
            for b in range(16):
                j('yb_loc', ctnl_abs(lanes, jj, c, 'yb', b), R.xy('yb_loc', 16 * jj + b, x0, y0))
            j('nflt', ctnl_abs(lanes, jj, c, 'flt', 0), R.xy('nflt_col', jj, x0, y0))
            for port, bits in (('rq_q', 64), ('hs_run', 1), ('hs_c', 16)):
                for b in range(bits):
                    j('request', R.xy(port, b, x0, y0), ctnl_abs(lanes, jj, c, port, b))
        for b in range(7):
            j('fv', (ctfl['fv_local'][b][2], ybot(CTFL_T, 25.92) + ctfl['fv_local'][b][3]), R.xy('fv', b, x0, y0))
        for b in range(104):
            j('fdx', (ctfl['fdx_local'][b][2], ybot(CTFL_T, 25.92) + ctfl['fdx_local'][b][3]), R.xy('fdx', b, x0, y0))
        for nm, half in (('hnz_n', 0), ('pflt_n', 0), ('hnz_s', 1), ('pflt_s', 1)):
            src = ctpl[nm[:-2] + '_d'][0]
            j('ctpl_flag', (LW * c + src[2], ybot(CTPL_T[half], 118.8) + src[3]), R.xy(nm, 0, x0, y0))
        if c == 0:
            src = ctpl['hov_d'][0]; j('hov_src', (src[2], ybot(CTPL_T[0], 118.8) + src[3]), R.xy('hov_in', 0, x0, y0))
        # row-internal: outputs -> own slice and partner slice
        S = slices[skind(c)]; sx, sy = spos(c)
        pc = (c + 2) % 4; P = slices[skind(pc)]; px, py = spos(pc)
        for port, sp in (('rvm', 'rv_c'), ('hdr', 'hdr_c'), ('a_rdm', 'a_own'), ('b_rdm', 'b_own')):
            for b in range(len(R.p[port])):
                j('to_slice', R.xy(port, b, x0, y0), S.xy(sp, b, sx, sy))
        for port, sp in (('a_rdm', 'a_par'), ('b_rdm', 'b_par')):
            for b in range(256):
                j('to_partner_slice', R.xy(port, b, x0, y0), P.xy(sp, b, px, py))
        # chain: this row's slice c (N edge) -> next row's ret c (above): + H
        for port, rp in (('rv_out', 'rv_in'), ('hdr_out', 'hdr_in'), ('a_own_out', 'ao_in'), ('b_own_out', 'bo_in'),
                         ('a_par_out', 'ap_in'), ('b_par_out', 'bp_in')):
            for b in range(len(S.p[port])):
                a = S.xy(port, b, sx, sy); r = R.xy(rp, b, x0, y0 + H)
                j('chain', a, r)
        # peers
        for pc2 in range(4):
            if pc2 == c:
                continue
            Q = rets[pc2]; qx, qy = rpos(pc2)
            pi = pc2 if pc2 < c else pc2 - 1
            for b in range(64):
                j('yb_peer', Q.xy('yb_fwd', b, qx, qy), R.xy('yb_peer', 64 * pi + b, x0, y0))
            j('flags', Q.xy('flag_fault', 0, qx, qy), R.xy('peer_fault', pi, x0, y0))
        if c != 3:
            Q = rets[3]; qx, qy = rpos(3)
            for b in range(128):
                j('cs_rel', Q.xy('cs_fwd', b, qx, qy), R.xy('cs_in', b, x0, y0))
        else:
            for b in range(128):
                jj = b // 32
                f, ly, x, y = lanes[3]['acc_out'][b % 32]
                j('cs_src', (LW * 3 + x, ybot(CTNL_T[jj], CTNL_H[3]) + y), R.xy('cs_in', b, x0, y0))
        if c != 0:
            Q = rets[0]; qx, qy = rpos(0)
            j('hov_rel', Q.xy('hov_fwd', 0, qx, qy), R.xy('hov_in', 0, x0, y0))
    by = collections.defaultdict(list)
    for x in joins:
        by[x['kind']].append(x['um'])
    return {k: dict(n=len(v), max_um=max(v), over500=sum(1 for u in v if u > 500), over440=sum(1 for u in v if u > 440)) for k, v in by.items()}, joins


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--out', required=True, type=Path); a = ap.parse_args()
    lanes, ctpl, ctfl, rets, slices = build()
    summ, joins = audit(lanes, ctpl, ctfl, rets, slices)
    a.out.mkdir(parents=True, exist_ok=True)
    for L in rets + list(slices.values()):
        (a.out / f'{L.name}.tcl').write_text(L.tcl())
    tot = dict(joins=len(joins), over500=sum(1 for x in joins if x['um'] > 500), max_um=max(x['um'] for x in joins))
    rep = dict(schema='opentallas.s81.cthntc_plan.v1', parent=dict(w=W, h=H), total=tot, by_kind=summ,
               scope='GEOMETRY ONLY (pin-to-pin Manhattan); timing by the leaf gates/routes and the parent trial')
    (a.out / 'audit.json').write_text(json.dumps(rep, indent=1) + '\n')
    print(json.dumps(rep, indent=1))


if __name__ == '__main__':
    main()
