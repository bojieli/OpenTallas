#!/usr/bin/env python3
"""frame_band_plan.py -- S81-P7 (10-23): frame-band PLAN CONTENTS (the G3 RTL blockers of the banded frame).

Input: the banded plan-width seam kit RTL (rtl/dsrom_sys/s81_dv/frame_lp/kit/col_<M>_l4_lp_kit_vgcs.sv: band modules
col_<M>_l4_lp_b<k> + the wiring top, tools/s81_dv/frame_hier_part.py + frame_seam_pipe.py).  Output: one plan content
module per band, col_<M>_l4_lp_r<k>, whose ports are exactly the die-plan partition buses of the frame types
(physical/die_plan/s81/die_plan.json, types col_<M>_r<k>*):

  clk                 the partition clock (spine tap); every band clock ck_r<k> and the x-lane clocks xk[3:0] load it
  rst_n               (r0 only) the partition's synchronised reset (gen_rtl ot_reset_sync) -> the frame rst_n
  x_i0 / xo_o0 / ret_o0   (r0 only) the frame data ports x / xo / ret
  frame_int_i<j> / frame_int_o<j>   the band seams to / from the neighbour band, packed per neighbour (bit map in the
                      --map json; LSB = the first seam port in natural order, lpr_root* last)
  parameter LK        the x-lane landing strap (was the static port lk[11:0]: 4 lanes x 3 b)

The five band RTL blockers (S81-P6 13:32 / COORD) and how this file resolves them:
  (a) lk port -> parameter LK (default {4{3'd2}}, the bench strap LK=2); no lk port.
  (b) xk / xok forwarded clocks: the die plan has ONE clock (spine + tap grid, neighbour skew <= 80 ps TT+FF, R4) and its
      x lanes are ft stations on that clock (R3), so a forwarded lane clock cannot travel with them (G0: no clock kind on
      a station lane).  The landing rings and xo relays take the partition clock (xk = {4{clk}}): the lane's last station
      IS on the neighbour's tap clock, the ring is then a same-clock fixed delay E (= LK), latency unchanged.  xok (the
      relays' forwarded clock out) is no longer a port (the next frame's x lane is its own station chain on clk).
  (c) band ports -> frame_int_* buses: packed here; the seam primitives become their plan forms (ot_pl_seam_w_pl /
      ot_pl_seam_r_pl, rtl/common/landed_parent/ot_pl_seam.sv) because the partition wrapper (tools/die_plan gen_rtl)
      already puts a boundary flop (ot_dp_st) on both sides of every bus: plan lane fi_* = 2 boundary flops +
      fixed_cycles 1 = the seam's K + 1 = 3 edges, cycle-exact with the vgcs twin.
  (e) lpr_root (the reset-forest root, made in r0) reached r2 through r1 as a wire: r1 now REGISTERS it (lpr_root__ft1,
      one flop) and every band pads its forest input so all three forests see the same root age as before relative to
      each other (r0 +2X+2, r1 +X+1 +pad, r2 +2X+2 with X = 2 boundary flops per crossing): the whole frame reset tree is
      uniformly 2X+2 = 6 edges later than the old root; no band skew.
  (d) hard-core / ROM macro positions are a plan item (gen_plan_v4.py contents[].hard_cores), not RTL; not done here.

S81-P9-RTL 10-23 (COORD 18:15 R3-INTERNAL: any reg-reg connection inside a partition > 750 um gets a FIRM station;
spec physical/die_plan/s81/inputs/r3_internal_v45.json).  Soft stations are relays named u_y_<name> that
tools/die_plan/relay_mid.tcl puts FIRM on the line between their FIXED source and FIXED sink (chain of n: L*j/(n+1)):
  (f) x forward (r0, XO_EN frames): the four hard x-forward relays u_xo<j> (dsfd_dvrly_276_NS, one stage, forwarded
      ck_o) become soft 2-stage chains u_y_xo<j>_0 -> u_y_xo<j>_1 (ot_s81_rly W 276 RSREG 1, ck = xk[j] = clk,
      rs = rst_n__xk[j]): x_i0 -> xo_o0 +1 edge (2 instead of 1), ~1.44 mm E->W in 3 hops of ~480 um.  xok (the
      forwarded clock) is gone with them (it was never a plan port).  u_xo<j> must leave the r0 hard-core list.
  (g) x -> far qbank (XQ_SPLIT): an x relay u_y_x{a,b}_<s>_0 (source = station u_t<s>, sinks = station u_t<s+1> + the
      qbank pair) whose E-column qbank sits ~860 um from the station gets a TWIN relay u_y_x{a,b}_<s>_bs<q>_0 (same input,
      same reset leaf, one stage) for that qbank only, so relay_mid puts each on its own straight line (~430-um hops).
      Latency-neutral: both qbanks of the pair still see x exactly one relay stage after u_t<s> (the pair shares one
      return-tree node and one emission offset off(pair), frame_return_plan.py, so the two must stay on the same edge;
      deepening only the far qbank would split the pair, deepening the trunk would shift every downstream station).
  (h) seams: readers -> ot_pl_seam_r_plq (flop-last = relay station <seam>.u_y_q, gating on its async clear) and every
      writer whose input is exactly one relay's output -> ot_pl_seam_w_plr (the relay and the writer gate as one station
      <seam>.u_y_w fed by the relay's input; the relay is dropped when the writer was its only load, else kept for its
      other loads and the writer takes a twin only if the relay's source is a hard core, so no relay chain forks).
      Both cycle-exact (K + 1 = 3 edges per seam unchanged) -- see rtl/common/landed_parent/ot_pl_seam.sv.

  frame_band_plan.py --master col_h9 [--kit KIT.sv] [--plan die_plan.json] --out OUT.sv --map MAP.json [--bench-top TOP.sv]

--bench-top also emits the wiring top col_<M>_l4_lp (the LP frame's ports, for tools/s81_dv/frame_bench.sh FRAME_LP_SV)
with the plan wrapper's two boundary flops on every frame_int bus (exactly ot_dp_st data: no reset), so the framed seam
bench (tools/s81_dv/frame_seam_bench.sh) proves the plan contents cycle-exact against the compiler calendar.
"""
import argparse, collections, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/s81_dv'))
import frame_seam_pipe as SP  # noqa: E402

X = 2                                   # boundary flops per plan crossing (gen_rtl ot_dp_st out + in)
# (g) far-qbank twins (S81-P8 r3_internal_v45: u_y_x{a,b}_<s>_0 -> u_bs<q> 765-873 um); {master: {band: {relay lane: qbank}}}
XQ_SPLIT = {'col_h9': {0: {'2': 'u_bs3'}},
            'col_h10': {0: {'3': 'u_bs4'}, 1: {'5': 'u_bs7', '6': 'u_bs9'}, 2: {'8': 'u_bs12'}}}
RLY_MASTERS = ['rtl/dsrom_sys/s81_dv/frame/dsfd_rly_frame_exact.sv'] + \
    ['rtl/dsrom_sys/s81_glue/dsfd_rly_masters%s.sv' % x for x in ('', '_266ew', '_536', '_c26l', '_gen18', '_v16')]
NET = r'\b[A-Za-z_]\w*(?:\[\d+\])?'


def rly_rsreg():
    """{dsfd_rly_* module: RSREG of its ot_s81_rly} over the relay master files the kit and the bench compile"""
    out = {}
    for f in RLY_MASTERS:
        for m, w, rest in re.findall(r'^module (dsfd_rly_\w+) .*?\n\s*ot_s81_rly #\(\.W\((\d+)\)(.*?)\) u ', (ROOT / f).read_text(),
                                     flags=re.M):
            r = re.search(r'RSREG\((\d)\)', rest)
            out.setdefault(m, int(r.group(1)) if r else 0)
    return out


def hard_modules(master):
    d = json.loads((ROOT / 'physical/die_plan/s81/inputs/frame_band_macros.json').read_text())
    return {x['module'] for r in d['masters'][master].values() for x in r}


def inst_lines(text):
    """{inst: (line index, module, {port: expr})} for the one-line child instances of a band module"""
    out = {}
    for n, ln in enumerate(text.split('\n')):
        m = re.match(r'^\s+(\w+) (?:#\(.*?\) )?(u_\w+) \((\..*)\);\s*$', ln)
        if m:
            out[m.group(2)] = (n, m.group(1), dict(re.findall(r'\.(\w+)\(((?:[^()]|\([^()]*\))*)\)', m.group(3))))
    return out


def r3_band(text, master, k, hard, rsreg, log):
    """(g) far-qbank x twins and (h) relay-placeable seams on one band module text"""
    L = text.split('\n')
    ins = inst_lines(text)
    # ---- (g)
    for lane, bq in XQ_SPLIT.get(master, {}).get(k, {}).items():
        for xv, pin in (('xa', 'i_x0'), ('xb', 'i_x1')):
            rn = f'u_y_{xv}_{lane}_0'
            n, mod, c = ins[rn]
            qn, qmod, qc = ins[bq]
            assert qc[pin] == c['o'], (rn, bq, 'qbank x pin is not the relay output')
            tw = f'{rn[:-2]}_{bq[2:]}_0'
            w = int(re.search(r'_(\d+)_[A-Z]+$', mod).group(1))
            wn = f'{tw[2:]}_o'
            # S81-P9 10-23: the twin and its original have identical D/ck/rs, so Yosys opt_merge folded the twin back
            # (col_h10_r1__t1 kit synth: 0 u_y_xa_5_bs7_0 cells); BOTH become the kept relay ot_s81_rly_k (keep on the
            # flop processes; a kept cell next to an unkept identical one is still merged, so the original is kept too)
            kp = f'ot_s81_rly_k #(.W({w}), .RSREG({rsreg[mod]}), .ID'
            L[n] = L[n].replace(f'{mod} {rn} (', f'{kp}(0)) {rn} (', 1)
            assert kp in L[n], rn
            L[n] += (f'\n    wire [{w - 1}:0] {wn};   // (g) far-qbank twin of {rn} (R3-INTERNAL, latency-neutral, kept: no merge)'
                     f'\n    {kp}({int(bq[4:])})) {tw} (.i({c["i"]}), .o({wn}), .ck({c["ck"]}), .rs({c["rs"]}));')
            L[qn] = L[qn].replace(f'.{pin}({c["o"]})', f'.{pin}({wn})', 1)
            log.append(f'r{k} (g) {tw} -> {bq}.{pin} ({w} b)')
    text = '\n'.join(L)
    # ---- (h) readers
    nr = text.count('ot_pl_seam_r_pl #(')
    text = text.replace('ot_pl_seam_r_pl #(', 'ot_pl_seam_r_plq #(')
    log.append(f'r{k} (h) {nr} seam readers -> ot_pl_seam_r_plq (flop-last station u_y_q)')
    # ---- (h) writers fed by one relay
    ins = inst_lines(text)
    L = text.split('\n')
    asg = {m.group(1): (n, m.group(2)) for n, ln in enumerate(L)
           for m in [re.match(r'^\s*assign (\w+) = (\{.*\}|\w+(?:\[\d+\])?);\s*$', ln)] if m}
    by_o = {}
    for i, (n, mod, c) in ins.items():
        if 'o' in c:
            by_o.setdefault(c['o'], []).append(i)
    users = collections.Counter(t for ln in L for t in re.findall(r'\bn\d+\b', ln))
    drop = set()
    for wi, (n, mod, c) in sorted(ins.items()):
        if mod != 'ot_pl_seam_w_pl':
            continue
        e = c['i']
        lpg = asg.get(e) if re.match(r'^\w+$', e) else None
        ex = lpg[1] if lpg else e
        src = [r for r in by_o.get(ex, []) if ins[r][1].startswith('dsfd_rly_')]
        if len(src) != 1:
            continue
        rn = src[0]
        rl, rmod, rc = ins[rn]
        bits = re.findall(r'\bn\d+\b', ex)
        # other loads of the relay output: every bit appears in its decl, the relay, the assign (if any) and nowhere else
        sole = bool(bits) and all(users[b] == 3 for b in bits)
        if not sole:
            drv = {ins[j][1] for b in re.findall(r'\bn\d+\b', rc['i'])[:1] for j, (_, _, cj) in ins.items()
                   if j != rn and re.search(r'\b%s\b' % b, ' '.join(cj.values()))}
            if not (drv & hard):
                log.append(f'r{k} (h) {wi}: source relay {rn} has other loads and a soft source -> writer unchanged')
                continue
        W = re.search(r'\.W\((.*?)\), \.CHUNK', L[n]).group(1)
        L[n] = (f'    ot_pl_seam_w_plr #(.W({W}), .CHUNK_BITS(24), .RSREG({rsreg[rmod]})) {wi} (.ck({c["ck"]}), .rsi({c["rsi"]}), '
                f'.rse({rc["rs"]}), .ir({rc["i"]}), .q({c["q"]}));   // (h) registered writer = {rn} + gate')
        if lpg:
            drop.add(lpg[0])
            dn = [m for m, ln in enumerate(L) if re.match(r'^\s*wire \[\d+:0\] %s;\s*$' % e, ln)]
            assert len(dn) == 1, (wi, e)
            drop.add(dn[0])
        if sole:
            drop.add(rl)
            drop.update(m for m, ln in enumerate(L) if re.match(r'^\s*wire (%s);\s*$' % '|'.join(bits), ln))
            log.append(f'r{k} (h) {wi}: {rn} ({rmod}, sole load) folded into the writer station {wi}.u_y_w')
        else:
            log.append(f'r{k} (h) {wi}: twin of {rn} ({rmod}, hard source; relay kept for its other loads) = {wi}.u_y_w')
    L = [ln for m, ln in enumerate(L) if m not in drop]
    return '\n'.join(L)


def xo_chain(text, log):
    """(f) r0: hard x-forward relays u_xo<j> -> soft 2-stage chains u_y_xo<j>_0 -> u_y_xo<j>_1"""
    n = 0
    def rep(m):
        nonlocal n
        j, ck, rs, i, o = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
        assert ck == f'xk[{j}]' and m.group(6) == f'xok[{j}]', m.group(0)[:120]
        n += 1
        return (f'    wire [275:0] y_xo{j}_s;   // (f) x forward stage 0 -> 1 (R3-INTERNAL)\n'
                f'    ot_s81_rly #(.W(276), .RSREG(1)) u_y_xo{j}_0 (.ck({ck}), .rs({rs}), .i({i}), .o(y_xo{j}_s));\n'
                f'    ot_s81_rly #(.W(276), .RSREG(1)) u_y_xo{j}_1 (.ck({ck}), .rs({rs}), .i(y_xo{j}_s), .o({o}));')
    text = re.sub(r'^    dsfd_dvrly_276_NS u_xo(\d) \(\.ck\(([^()]*)\), \.rs\(([^()]*)\), \.i\((\{[^}]*\})\), \.o\((\{[^}]*\})\), '
                  r'\.ck_o\(([^()]*)\)\);$', rep, text, flags=re.M)
    assert n == 4, n
    assert text.count('    wire [3:0] xok;\n') == 1 and len(re.findall(r'\bxok\b', text)) == 1, 'xok still used'
    text = text.replace('    wire [3:0] xok;\n', '')
    log.append('r0 (f) u_xo0..3 -> u_y_xo<j>_0 -> u_y_xo<j>_1 (x_i0 -> xo_o0: 2 edges, was 1); xok removed')
    return text

LK_DEFAULT = "{4{3'd2}}"
FRAME_DATA = {'x': 'x_i0', 'xo': 'xo_o0', 'ret': 'ret_o0'}


def natkey(s):
    return [int(t) if t.isdigit() else t for t in re.split(r'(\d+)', s)] + [s.startswith('lpr_root')]


def split_modules(text):
    mods, cur, buf = collections.OrderedDict(), None, []
    for ln in text.split('\n'):
        m = SP.MOD_RE.match(ln)
        if m:
            cur, buf = m.group(1), [ln]
            continue
        if cur:
            buf.append(ln)
            if ln.startswith('endmodule'):
                mods[cur] = '\n'.join(buf)
                cur = None
    return mods


def top_conns(top_text, top):
    """[(band module, inst, {port: net})] from the wiring top"""
    out = []
    for mod, inst, conns in re.findall(r'^\s*(%s_b\d+) #\(.*?\) (u_b\d+) \((.*?)\);' % re.escape(top), top_text,
                                       flags=re.M | re.S):
        out.append((mod, inst, dict((p, n.strip()) for p, n in re.findall(r'\.(\w+)\(([^()]*)\)', conns))))
    return out


def plan_buses(plan, master, k):
    """{(dir, width): bus name} of the frame_int buses of every plan type col_<M>_r<k>* (all variants must agree)"""
    d = json.loads(Path(plan).read_text())
    want, seen = None, []
    for tn, t in d['partition_types'].items():
        if not re.match(r'%s_r%d(_p\d+)?__t\d+$' % (master, k), tn):
            continue
        fb = {}
        for b in t['buses']:
            if b['name'].startswith('frame_int_'):
                key = ('in' if b['dir'] == 'in' else 'out', b['width'])
                assert key not in fb, (tn, key, 'frame_int widths must identify the neighbour')
                fb[key] = b['name']
        assert want is None or fb == want, (tn, fb, want)
        want = fb
        seen.append(tn)
    assert seen, f'no plan type for {master} r{k}'
    return want, seen


R3, R3LOG, HARD, RSREG = True, [], set(), {}


def gen(kit, master, plan):
    global HARD, RSREG
    HARD, RSREG = hard_modules(master), rly_rsreg()
    text = Path(kit).read_text()
    top = f'{master}_l4_lp'
    mods = split_modules(text)
    ports = SP.band_ports(text.split('\n'))
    conns = top_conns(mods[top], top)
    bands = {inst: mod for mod, inst, _ in conns}
    kof = {inst: int(inst[3:]) for inst in bands}
    # bench-twin loop-backs through the wiring top (lp.py MUT 1 bypass of one landing): at MUT 0 they are intra-band
    # wires.  lpg_N_i = {bits}: the source band's own outputs back into its seam writer; lpg_N_i__l_rD = MUT==1 ? ... :
    # lpl_N_o and X__l_rD = lpg_N_i__l_rD[k]: the reader band's seam output back into its own inputs.
    owner = {}
    for mod, inst, cs in conns:
        for p, n in cs.items():
            owner.setdefault(n, set()).add(inst)
    loops, internal = collections.defaultdict(list), collections.defaultdict(set)
    for lhs, rhs in re.findall(r'^\s*assign (\w+) = (.*?);\s*$', mods[top], flags=re.M):
        m = re.match(r'\(MUT == 1\) \? \w+ : (\w+)$', rhs)
        if m:
            rhs = m.group(1)
            band, = owner[rhs]
            loops[band].append(f'    wire [{ports[bands[band]][rhs][1] - 1}:0] {lhs} = {rhs};   // MUT 0 (no bypass)')
            owner[lhs] = {band}
            internal[band].add(rhs)
            continue
        nets = re.findall(r'\b(?!MUT\b)[A-Za-z_]\w*', rhs)
        bands_ = set().union(*(owner[n] for n in nets)) | owner.get(lhs, set())
        assert len(bands_) == 1, (lhs, rhs[:80], bands_)
        band, = bands_
        loops[band].append(f'    assign {lhs} = {rhs};')
        internal[band] |= set(nets) | {lhs}
    drv, rd = {}, collections.defaultdict(list)
    for mod, inst, cs in conns:
        for p, n in cs.items():
            if p in internal[inst]:
                continue
            (drv.__setitem__(n, (inst, p)) if ports[mod][p][0] == 'output' else rd[n].append((inst, p)))
    # groups: (src band, dst band) -> [net] (each a seam port name in both bands)
    groups = collections.defaultdict(list)
    for n, (si, sp) in drv.items():
        for di, dp in rd.get(n, []):
            groups[(si, di)].append((sp, dp, ports[bands[si]][sp][1]))
    out_mods, bmap = [], dict(master=master, kit=str(kit), x_boundary_flops=X, bands={})
    for inst in sorted(bands, key=lambda s: kof[s]):
        k, mod = kof[inst], bands[inst]
        pb, ptypes = plan_buses(plan, master, k)
        hdr, body_assign, bm = [], [], dict(plan_types=ptypes, buses={})
        hdr.append('    input  wire clk')
        frame_ports = {p: n for p, n in dict(next(c for m, i, c in conns if i == inst)).items()}
        if 'rst_n' in ports[mod]:
            hdr.append('    input  wire rst_n')
        for p, pn in FRAME_DATA.items():
            if p in ports[mod]:
                d, w = ports[mod][p]
                hdr.append(f"    {'input ' if d == 'input' else 'output'} wire [{w - 1}:0] {pn}")
                body_assign.append(f'    assign {p} = {pn};' if d == 'input' else f'    assign {pn} = {p};')
        for (si, di), lst in sorted(groups.items(), key=lambda kv: (kof[kv[0][0]], kof[kv[0][1]])):
            if inst not in (si, di):
                continue
            lst = sorted(lst, key=lambda t: natkey(t[0]))
            W = sum(w for _, _, w in lst)
            d = 'out' if si == inst else 'in'
            bus = pb.get((d, W))
            assert bus, (inst, d, W, pb, 'band seam group width has no plan bus')
            hdr.append(f"    {'output' if d == 'out' else 'input '} wire [{W - 1}:0] {bus}")
            lo, fields = 0, []
            for sp, dp, w in lst:
                p = sp if d == 'out' else dp
                sl = f'{bus}[{lo + w - 1}:{lo}]' if w > 1 else f'{bus}[{lo}]'
                body_assign.append(f'    assign {sl} = {p};' if d == 'out' else f'    assign {p} = {sl};')
                fields.append(dict(lsb=lo, width=w, src_port=sp, dst_port=dp))
                lo += w
            bm['buses'][bus] = dict(dir=d, width=W, peer=f'r{kof[di] if d == "out" else kof[si]}', fields=fields)
        bmap['bands'][f'r{k}'] = bm
        # module text: new header, old ports as internal wires
        src = mods[mod]
        m = re.match(r'module %s #\((.*?)\) \((.*?)\);' % re.escape(mod), src, flags=re.S)
        assert m, mod
        params = [p.strip().rstrip(',') for p in m.group(1).strip().split('\n') if p.strip()]
        params = [p for p in params] + [f"parameter [11:0] LK = {LK_DEFAULT}"]
        body = src[m.end():]
        decl = []
        for p, (d, w) in sorted(ports[mod].items()):
            if p.startswith('ck_r'):
                decl.append(f'    wire {p} = clk;')
            elif p == 'lk':
                decl.append('    wire [11:0] lk = LK;')
            elif p == 'xk':
                decl.append('    wire [3:0] xk = {4{clk}};       // (b) x-lane clocks = the partition clock')
            elif p == 'rst_n':
                continue
            else:
                decl.append(f'    wire [{w - 1}:0] {p};' if w > 1 else f'    wire {p};')
        # (c) seam primitives -> plan forms (the partition wrapper's boundary flops are the seam's outer flops)
        nw, nr = body.count('ot_pl_seam_w #('), body.count('ot_pl_seam_r #(')
        body = body.replace('ot_pl_seam_w #(', 'ot_pl_seam_w_pl #(').replace('ot_pl_seam_r #(', 'ot_pl_seam_r_pl #(')
        # (e) reset root: equal forest age in every band, r1 registers the feedthrough
        fr = re.search(r'ot_pl_land_reset_forest #\(.*?\) u_lpr_r%d \(\.ck\((\w+)\), \.d\((\w+)\),' % k, body)
        assert fr, (mod, 'no reset forest')
        ck, rootn = fr.group(1), fr.group(2)
        body = body[:fr.start()] + fr.group(0).replace(f'.d({fr.group(2)}),', '.d(lpr_root__age),') + body[fr.end():]
        extra = []
        if k == 0:
            pad = 2 * X + 2
        elif 'lpr_root__ft1' in ports[mod]:
            a = 'assign lpr_root__ft1 = lpr_root;'
            assert body.count(a) == 1, mod
            body = body.replace(a, f'ot_pl_pad #(.W(1), .N(1)) u_lpr_ft1 (.ck({ck}), .d(lpr_root), .q(lpr_root__ft1));'
                                '   // (e) registered reset feedthrough')
            rootn, pad = 'lpr_root__ft1', (2 * X + 2) - (X + 1)
        else:
            pad = (2 * X + 2) - (2 * X + 1)
        extra.append(f'    wire lpr_root__age;  // (e) forest root at the common age 2X+2 = {2 * X + 2} edges after r0 lpr_root')
        extra.append(f'    ot_pl_pad #(.W(1), .N({pad})) u_lpr_age (.ck({ck}), .d({rootn}), .q(lpr_root__age));')
        bm.update(seams_w=nw, seams_r=nr, reset_root_pad=pad)
        decl += loops[inst]
        name = f'{top}_r{k}'
        mtxt = (f'module {name} #(\n    ' + ',\n    '.join(params) + '\n) (\n' + ',\n'.join(hdr) + '\n);\n'
                + '\n'.join(decl + extra + body_assign) + '\n' + body.lstrip('\n'))
        out_mods.append(r3_band(mtxt, master, k, HARD, RSREG, R3LOG) if R3 else mtxt)
    return out_mods, bmap, groups, bands, kof, ports


def bench_top(master, bmap, kit):
    """the LP frame ports around the plan contents, two boundary flops (ot_dp_st data) on every frame_int bus"""
    top = f'{master}_l4_lp'
    L = ['`ifndef LK\n`define LK 2\n`endif', f'// bench twin: plan contents {top}_r0..r2 + the plan wrapper boundary flops (2 per frame_int bus, ot_dp_st data)',
         f'module {top} #(\n    parameter string INSTANCE = "{master}",\n    parameter integer MUT = 0\n) (',
         '    input wire rst_n,\n    input wire [1103:0] x,\n    input wire [3:0] xk,\n    input wire [11:0] lk,',
         '    output wire [1103:0] xo,\n    output wire [3:0] xok,\n    output wire [69:0] ret,',
         '    input wire ck_r0,\n    input wire ck_r1,\n    input wire ck_r2\n);',
         '    assign xok = 4\'b0;   // bench only: the plan has no forwarded x clock out (unused by tb_s81dv_frame)']
    flops, conns = [], collections.defaultdict(list)
    for r, bm in bmap['bands'].items():
        for bus, b in bm['buses'].items():
            if b['dir'] != 'out':
                continue
            peer = b['peer']
            dbus = next(n for n, x in bmap['bands'][peer]['buses'].items() if x['dir'] == 'in' and x['peer'] == r)
            w = b['width']
            s, a, d = f'{r}_{bus}', f'{r}_{bus}_q', f'{peer}_{dbus}'
            L.append(f'    wire [{w - 1}:0] {s}, {a};\n    reg [{w - 1}:0] {a}_r, {d}_r;\n    wire [{w - 1}:0] {d};')
            flops.append(f'    always @(posedge ck_{r}) {a}_r <= {s};          // src boundary flop\n'
                         f'    always @(posedge ck_{peer}) {d}_r <= {a}_r;    // dst boundary flop\n'
                         f'    assign {a} = {a}_r;\n    assign {d} = {d}_r;')
            conns[r].append(f'.{bus}({s})')
            conns[peer].append(f'.{dbus}({d})')
    L += flops
    for r in sorted(bmap['bands']):
        extra = ['.rst_n(rst_n)', '.x_i0(x)', '.xo_o0(xo)', '.ret_o0(ret)'] if r == 'r0' else []
        L.append(f'    {top}_{r} #(.INSTANCE(INSTANCE), .MUT(MUT), .LK({{4{{3\'d`LK}}}})) u_{r} (.clk(ck_{r}), '
                 + ', '.join(extra + conns[r]) + ');')
    L.append('endmodule')
    return '\n'.join(L) + '\n'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--master', default='col_h9')
    ap.add_argument('--kit')
    ap.add_argument('--plan', default=str(ROOT / 'physical/die_plan/s81/die_plan.json'))
    ap.add_argument('--out', required=True)
    ap.add_argument('--map', required=True)
    ap.add_argument('--bench-top', help='also write the bench wiring top (LP frame ports) to this file')
    ap.add_argument('--no-r3', action='store_true', help='without the S81-P9-RTL R3-INTERNAL stations (f)(g)(h) (the P7 form)')
    a = ap.parse_args()
    # the vgcs bench twin (full leaf parameters; the kit RTL has the hard-child overrides removed and does not simulate)
    kit = a.kit or str(ROOT / f'rtl/dsrom_sys/s81_dv/frame_lp/vgcs/{a.master}_l4_lp_rf3r.sv')
    global R3
    R3 = not a.no_r3
    mods, bmap, *_ = gen(kit, a.master, a.plan)
    head = (f'// GENERATED by tools/s81_dv/frame_band_plan.py from {Path(kit).relative_to(ROOT) if Path(kit).is_absolute() else kit}: '
            'die-plan contents of the frame bands (frame_int buses, LK parameter, xk = clk, registered lpr_root ft).\n'
            '`timescale 1ns/1ps\n`default_nettype none\n')
    # XO_EN 0 (plan chain-end frames p3 / p6: no xo_o0 bus): r0 WITHOUT the x-forward stations u_xo<j> and the xo port
    # (a chain end forwards no x; the stations would be unloaded).  Same instance paths as r0 for every other child.
    r0 = next(m for m in mods if m.startswith(f'module {a.master}_l4_lp_r0 '))
    nxt = r0.replace(f'module {a.master}_l4_lp_r0 ', f'module {a.master}_l4_lp_r0_nx ', 1)
    n0 = len(nxt.splitlines())
    nxt = '\n'.join(l for l in nxt.splitlines()
                    if not re.match(r'^\s*(output wire \[\d+:0\] xo_o0,|wire \[\d+:0\] xo;|wire \[3:0\] xok;|'
                                    r'assign xo_o0 = xo;|\w+ u_xo\d+ \()', l)) + '\n'
    assert n0 - len(nxt.splitlines()) == 8, n0 - len(nxt.splitlines())
    nx = [nxt]
    mods.append('\n'.join(nx) + '\n')
    if R3:
        i0 = mods.index(r0)
        mods[i0] = xo_chain(r0, R3LOG)
    txt = head + '\n'.join(mods) + '\n`default_nettype wire\n'
    Path(a.out).write_text(txt)
    if a.bench_top:
        Path(a.bench_top).write_text('// GENERATED by tools/s81_dv/frame_band_plan.py --bench-top\n`timescale 1ns/1ps\n'
                                     + bench_top(a.master, bmap, kit))
    bmap['kit'] = str(Path(kit).resolve().relative_to(ROOT)) if Path(kit).resolve().is_relative_to(ROOT) else str(kit)
    bmap['r3_internal'] = R3LOG if R3 else None
    # S81-P9-RTL: frame-internal latencies the die compiler / TOK must add to the plan lane table (die_plan latency lists
    # lanes only: an xo lane's cycles are its 2 boundary flops; the source frame's own x_i0 -> xo_o0 forward is internal)
    bmap['latency_edges'] = dict(x_i0_to_xo_o0=2 if R3 else 1, x_i0_to_xo_o0_was=1,
                                 seam_K_plus_1=X + 1, note='seams (frame_int) unchanged; x arrival at chain position j '
                                 '(0-based from the chain head p1 / p4) moves by +j edges vs the P7 contents')
    Path(a.map).write_text(json.dumps(bmap, indent=1) + '\n')
    for ln in R3LOG:
        print(ln)
    for r, bm in bmap['bands'].items():
        print(r, {b: (x['dir'], x['width'], x['peer']) for b, x in bm['buses'].items()}, 'seams w/r', bm['seams_w'],
              bm['seams_r'], 'root pad', bm['reset_root_pad'])


if __name__ == '__main__':
    main()
