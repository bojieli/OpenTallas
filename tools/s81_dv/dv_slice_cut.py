#!/usr/bin/env python3
"""dv_slice_cut.py -- cut a slice top out of the GENERATED S81-DV die netlist (LAYERBENCH-S81, TOK.DS.BENCH.3, 10-18).

The slice is a set of die instances, copied VERBATIM from die.v (same masters, same parameters, same strap literals,
same internal net names): the real bound RTL, no stand-ins, no stubs, no ties added.  Every die net bit the slice
reads but does not drive becomes an input port bit; every bit it drives that is read outside the slice (or is a die
output) becomes an output port bit.  The replay bench (tb_dv_slice.sv) drives / checks those ports at the compiler's
scheduled cycles.

Instance set: --insts FILE (one instance name or /regex/ per line, # comments).  Growth (default on):
  * fan-in  : every relay-class instance (forwarded-lane relays dsfd_dvrlyh_* / dsfd_rly_*, landings dsfd_dvland_*,
              clock-forward cells BUFx* / INVx*) that drives a slice input bit is added, recursively through relay-class
              inputs: a lane arriving from a neighbour enters the slice at the neighbour master's output register (its
              real relay chain, forwarded clock and landing are inside the slice);
  * fan-out : every relay-class instance fed by a slice core output is added, recursively through relay-class
              outputs: the slice's outgoing lanes leave at the neighbour's landing input.
  Reset stations (dsfd_rly_1_*) are relay-class too, so the slice carries its reset tree path from the die rst_n.
Clock-type boundary inputs (bits that reach a ck / clk / ck_f pin) are reported with `clock_from`: the clock net of
the outside driver (a forwarded root = the source master's clk, e.g. ot_s81sl_slice ck_v = {2{clk}}), so the bench
drives them from that die clock.

Usage: dv_slice_cut.py --die-v die.v[.gz] --kit KITDIR (dv_rtl_kit.py of the die: master port directions)
                       --insts SET --out DIR [--name slice_top] [--no-grow]
Output: DIR/<name>.sv, DIR/slice_ports.json {port: {dir, width, net, lo, bits [boundary bit indices], peers, kind,
clock_from}}, DIR/slice_insts.json (instances by master, how each was included).
"""
import argparse
import gzip
import hashlib
import json
import math
import re
import sys
from collections import defaultdict, Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import dv_rtl_kit as K  # noqa: E402

RELAY_RE = re.compile(r'^(dsfd_dvrlyh_|dsfd_rly_|dsfd_dvland_|BUFx|INVx|ICGx)')   # ICGx: hop-0 lane clock gate (S81-LBGAP/G1)
RESET_RE = re.compile(r'^dsfd_rly_1_')
# RTLGAP-G9 (10-22): ck_r<k> = the H9/H10 frame region roots (col_h9_l4_lp ck_r0/ck_r1/ck_r2).  Without it ck_r1/ck_r2
# (which reach no other clock pin) were classed die_input and the bench held them at 0: two of the three frame regions
# never clocked on every G9 cut.
# TOK-DS-GAPS (10-24): ck_<REGION> = the MU72 / c1x / c3x slice region clocks (ck_K, ck_ML, ck_L0..L4, ck_CAP_CE/CW/RN/RS/RT;
# ck_S / ck_N<k> were caught only because a relay also takes them on `ck`).  Without it the fc31 cuts (0S, 0N, 7, 3S_ctl)
# held 10-22 slice region clocks at 0: leaves 0, 1, 3, 4, the lep K / ML regions and the CAP regions never clocked, and
# every replay of those cuts was fault-free by construction there (found by the cut_0S NX flit data check: zero partials).
CLOCK_PORT_RE = re.compile(r'^(clk|ck|ck_f|ck_i|ck_r\d+|cr|cr_s|CLK|ck_[A-Z][A-Z0-9_]*)$')


FLIGHT_SIM = """// dv_flight_sim (S81-LBGAP/G1, bench side): F whole periods of lane flight between the last relay station and its
// landing.  The word is delayed F edges of the lane clock and the lane clock reaches the landing F edges late: its first
// edge carries the word of hop-0 gate edge G, as the silicon ck_f edge 0 does (LANDING-CONTRACT L3).
module dv_flight_sim #(parameter integer W = 1, parameter integer F = 0) (
    input  wire ck_in, input wire rs, input wire [W-1:0] i_in, output wire ck_out, output wire [W-1:0] i_out);
    generate if (F == 0) begin : g0
        assign ck_out = ck_in; assign i_out = i_in;
    end else begin : gf
        reg [W-1:0] d [0:F-1];
        reg [31:0] n = 0;
        reg en_l = 1'b0;
        integer k;
        always @(posedge ck_in) begin
            d[0] <= i_in;
            for (k = 1; k < F; k = k + 1) d[k] <= d[k - 1];
        end
        // the flight count starts with the lane clock's first real edge: the time-0 settle of an idle-high (inverted,
        // half-cycle) lane clock is not an edge (rs kept on the port for the record; the wire delay ignores it)
        always @(posedge ck_in)
            if ($time > 0 && n < F) n <= n + 1;
        /* verilator lint_off COMBDLY */
        always_latch if (!ck_in) en_l = (n >= F);
        /* verilator lint_on COMBDLY */
        assign ck_out = ck_in & en_l;
        assign i_out = d[F - 1];
    end endgenerate
endmodule
"""

RST_LAND = """// dv_rst_land (TOKc-S81, 10-22, bench side): the kit reset landing of a hardened landing view (ref_tile reset_landing
// {"enable": true, "stages": N}, physical/common_flow/ot_pin_regs.tcl OT_RST_LAND: rs -> rs__ot_rl0 .. rs__ot_rl<N-1>
// plain ck flops -> core).  The die calendar (dv_bind landing_reset_stages, bind landing_reset_check.json) opens the
// hop-0 gate N edges later for exactly these masters, so the RTL landing body without it reads N edges early (fault).
module dv_rst_land #(parameter integer N = 2) (input wire ck, input wire rs, output wire o);
    reg [N-1:0] q = {N{1'b0}};
    always @(posedge ck) q <= {q, rs};
    assign o = q[N-1];
endmodule
"""




def load_masters(kit, D, names):
    """port directions of the masters, from the kit's chosen files"""
    rec = json.loads((Path(kit) / 'kit.json').read_text())
    out = {}
    for f in rec['files']:
        t = (Path(kit) / 'src' / f['path']).read_text(errors='replace')
        if not any(n in t for n in names):
            continue
        t = D.preprocess(D.strip_comments(t), {d: '' for d in rec.get('defines', [])})
        for m in D.parse_modules(t, f['path']):
            if m.name in names and m.name not in out:
                ch = rec['variant_choices'].get(m.name)
                if ch and ch['file'] != f['path']:
                    continue
                out[m.name] = m
    return out, rec


def ranges(bits):
    """sorted ints -> [(hi, lo)] contiguous runs, high first"""
    bits = sorted(bits)
    out, s, p = [], None, None
    for b in bits:
        if s is None:
            s = p = b
        elif b == p + 1:
            p = b
        else:
            out.append((p, s)); s = p = b
    if s is not None:
        out.append((p, s))
    return out[::-1]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--die-v', required=True)
    ap.add_argument('--kit', required=True)
    ap.add_argument('--insts', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--name', default='slice_top')
    ap.add_argument('--top', default='dv_die')
    ap.add_argument('--no-grow', action='store_true')
    ap.add_argument('--land-plan', help='p4l land_plan.json: back-annotate every landing input (ck_f and i together) with '
                    'the lane flight time at --corner as a CYCLE model (S81-LBGAP/G1): F = ceil(-S1/T) whole periods '
                    '(E - 1 at the corner that sets E), clipped into the landing window [K-D+1, K-1] (K = the plan strap, G8). '
                    'RTL relays are zero-delay, so without it every lane with E >= D aliases its ring.  The model delays the '
                    'lane word by F ck_f edges and opens ck_f F edges late -- the hop-0 gate (die.v ICG, LANDING-CONTRACT '
                    'L3) is what makes the late first edge carry the calendar epoch.  Bench side only (wire flight), never '
                    'in the die netlist.  Within the window the landing output is independent of F (run both corners).')
    ap.add_argument('--corner', default='tt', choices=['tt', 'ff'])
    ap.add_argument('--land-model', action='store_true', help='TOK-FUNC-S81: landings without a land-plan row / S1 '
                    '(model rows, die.v K placeholders) get flight F = K - 1 instead of failing (recorded source model)')
    ap.add_argument('--flight-shift', type=int, default=0,
                    help='MUTANT ONLY: add this many cycles to every F (outside the window -> the landings must fault)')
    ap.add_argument('--rom-instance', action='store_true',
                    help='give every instance of a master with a string INSTANCE parameter (the frames: their ROM macros '
                         'load <OT_ROM_DIR>/<INSTANCE>_cX_Y.viamap.hex) .INSTANCE("<instance name>") -- die.v passes none, so '
                         'every frame of one master would read the same ROM image (die-netlist gap, recorded)')
    ap.add_argument('--landing-reset', default='auto',
                    help='bind landing_reset_check.json (rows master/rl): every landing whose bound view carries the kit '
                         'reset landing (rl > 0) gets dv_rst_land #(rl) on its rs, as the hardened view and the die gate '
                         'calendar have it; auto = <die.v dir>/landing_reset_check.json when present, none = off (pre-po2 dies)')
    ap.add_argument('--repo', default=str(K.ROOT))
    a = ap.parse_args(argv)
    out = Path(a.out).resolve(); out.mkdir(parents=True, exist_ok=True)
    kitrec = json.loads((Path(a.kit) / 'kit.json').read_text())
    D = K.load_dpb(Path(a.repo), kitrec['sha'])
    dv = a.die_v
    if dv.endswith('.gz'):
        p = out / 'die.v'
        p.write_text(gzip.open(dv, 'rt').read()); dv = str(p)
    text = Path(dv).read_text(errors='replace')
    nets, tin, tout, insts = D.parse_die(dv, a.top)
    insts = [i for i in insts if i[0] != '__assign__']
    byname = {i[1]: i for i in insts}
    masters, _ = load_masters(a.kit, D, {i[0] for i in insts})
    miss = sorted({i[0] for i in insts} - set(masters))
    if miss:
        raise SystemExit(f'dv_slice_cut: no RTL port list for masters {miss}')

    # per instance: [(port, dir, bits)]
    conns = {}
    drv, use = {}, defaultdict(set)              # (net, bit) -> inst / {inst}
    for mst, inst, params, cm in insts:
        mod = masters[mst]
        lst = []
        for port, expr in cm.items():
            if port not in mod.ports:
                raise SystemExit(f'dv_slice_cut: {inst}.{port} not a port of {mst}')
            d = mod.ports[port][0]
            bits = D.expr_bits(expr, nets)
            if bits is None:
                raise SystemExit(f'dv_slice_cut: unparsable connection {inst}.{port}({expr[:80]})')
            nb = [b for b in bits if b[0] not in ('CONST', 'Z', 'UNDECL')]
            lst.append((port, d, nb))
            for b in nb:
                if d == 'output':
                    if b in drv:
                        raise SystemExit(f'dv_slice_cut: {b} driven by {drv[b]} and {inst}')
                    drv[b] = inst
                else:
                    use[b].add(inst)
        conns[inst] = lst
    for n in tin:
        w, lo = nets[n]
        for i in range(lo, lo + w):
            drv[(n, i)] = '<die_in>'
    for n in tout:
        w, lo = nets[n]
        for i in range(lo, lo + w):
            use[(n, i)].add('<die_out>')

    # ---- instance set
    S, how = set(), {}
    pats = [ln.split('#')[0].strip() for ln in Path(a.insts).read_text().split('\n')]
    for p in [p for p in pats if p]:
        if p.startswith('/') and p.endswith('/'):
            rx = re.compile(p[1:-1])
            hit = [i for i in byname if rx.fullmatch(i)]
        else:
            hit = [p] if p in byname else []
        if not hit:
            raise SystemExit(f'dv_slice_cut: instance pattern {p!r} matches nothing in {a.top}')
        for h in hit:
            S.add(h); how[h] = 'set'
    def fan_in(seeds):
        todo = list(seeds)
        while todo:                               # fan-in through relay-class drivers (lanes, reset stations, fwd cells)
            i = todo.pop()
            for port, d, bits in conns[i]:
                if d == 'output':
                    continue
                for b in bits:
                    j = drv.get(b)
                    if j and j in byname and j not in S and RELAY_RE.match(byname[j][0]):
                        S.add(j); how[j] = f'fan-in of {i}'; todo.append(j)

    if not a.no_grow:
        fan_in(list(S))
        todo, new = [i for i in S if how[i] == 'set'], []
        while todo:                               # fan-out through LANE relays / landings (never the reset tree)
            i = todo.pop()
            for port, d, bits in conns[i]:
                if d != 'output':
                    continue
                for b in bits:
                    for j in use.get(b, ()):
                        if j in byname and j not in S and RELAY_RE.match(byname[j][0]) and not RESET_RE.match(byname[j][0]):
                            S.add(j); how[j] = f'fan-out of {i}'; todo.append(j); new.append(j)
        fan_in(new)                               # their forwarded clocks / reset leaves back to the die roots

    # ---- boundary
    snets = set()
    in_bits, out_bits = defaultdict(set), defaultdict(set)
    peers_in, peers_out = defaultdict(set), defaultdict(set)
    clk_bits = defaultdict(set)
    for i in S:
        for port, d, bits in conns[i]:
            for b in bits:
                snets.add(b[0])
                if d != 'output':
                    j = drv.get(b)
                    if j not in S:
                        in_bits[b[0]].add(b[1]); peers_in[b[0]].add(j or '<undriven>')
                        if CLOCK_PORT_RE.match(port):
                            clk_bits[b[0]].add(b[1])
                else:
                    outside = [j for j in use.get(b, ()) if j not in S]
                    if outside:
                        out_bits[b[0]].add(b[1]); peers_out[b[0]].update(outside)

    def clock_from(net):
        srcs = set()
        for i in sorted(peers_in[net]):
            if i == '<die_in>':
                srcs.add(net)
                continue
            if i not in byname:
                continue
            for port, d, bits in conns[i]:
                if d != 'output' and CLOCK_PORT_RE.match(port) and bits:
                    srcs.add(bits[0][0])
        return sorted(srcs)

    ports, decl, body = {}, [], []
    # a 1-bit net the die declares as [0:0] and the instance lines bit-select (dv_bind nc fillers `u_x_p_nc3[0:0]`) keeps
    # its range (LB2-S81 L0 10-18: cut_svc failed Verilator "Illegal bit or array select" x8 on scalar re-declarations)
    selected = set(re.findall(r'([A-Za-z_]\w*)\s*\[', text))
    for n in sorted(snets):
        w, lo = nets[n]
        rng = f'[{lo + w - 1}:{lo}] ' if (w > 1 or lo or n in selected) else ''
        if n in in_bits:
            pn = f'i__{n}'
            kind = 'clock' if clk_bits.get(n) else ('die_input' if peers_in[n] == {'<die_in>'} else 'boundary')
            ports[pn] = dict(dir='input', width=w, lo=lo, net=n, bits=ranges(in_bits[n]), peers=sorted(peers_in[n]),
                             kind=kind, clock_from=clock_from(n) if kind == 'clock' else None)
            decl.append(f'  input wire {rng}{pn};')
        if n in out_bits:
            pn = f'o__{n}'
            ports[pn] = dict(dir='output', width=w, lo=lo, net=n, bits=ranges(out_bits[n]), peers=sorted(peers_out[n]),
                             kind='die_output' if peers_out[n] == {'<die_out>'} else 'boundary')
            decl.append(f'  output wire {rng}{pn};')
        body.append(f'  wire {rng}{n};')
        for hi, lo_ in ranges(in_bits.get(n, ())):
            sel = f'[{hi}:{lo_}]' if (w > 1 or lo) else ''
            body.append(f'  assign {n}{sel} = i__{n}{sel};')
        if n in out_bits:
            body.append(f'  assign o__{n} = {n};')
    # instance lines verbatim from die.v (statement text, comments dropped)
    lines = {}
    for ln in text.split('\n'):
        # die.v declares a few nets on the instance's line ('wire u_rsv_00_rst; INVx2_ASAP7_75t_R rinv_rsv_00 (...)');
        # the cut declares every net itself, so the leading declaration is dropped
        ln = re.sub(r'^(\s*)wire\b[^;(]*;\s*', r'\1', ln)
        m = re.match(r'\s*([\w\\]\S*)\s+(?:#\s*\(.*?\)\s*)?([\w\\]\S*)\s*\(', ln)
        if m and m.group(2) in S:
            lines[m.group(2)] = ln.split(');')[0].rstrip() + ');'
    rom_inst = []
    if a.rom_instance:
        for i in sorted(lines):
            mst = byname[i][0]
            if 'INSTANCE' in masters[mst].params and 'INSTANCE' not in byname[i][2]:
                ln = lines[i]
                if re.match(r'\s*\S+\s+#\s*\(', ln):
                    ln = re.sub(r'#\s*\(', f'#(.INSTANCE("{i}"), ', ln, count=1)
                else:
                    ln = re.sub(r'^(\s*\S+)\s+', lambda m: f'{m.group(1)} #(.INSTANCE("{i}")) ', ln, count=1)
                lines[i] = ln
                rom_inst.append(i)
    lane_dl = {}
    if a.land_plan:
        LPJ = json.loads(Path(a.land_plan).read_text())
        LP = {r['link']: r for r in LPJ['links']}
        T_ps = float(LPJ['T_ps'])
        for i in sorted(lines):
            if not byname[i][0].startswith('dsfd_dvland'):
                continue
            r = LP.get(i[3:] if i.startswith('ld_') else i)
            src = 'land_plan'
            if r is None or r.get('s1', {}).get(a.corner) is None:
                # TOK-FUNC-S81 (10-21, --land-model): an RTL-only source assembly has no routed flight for model rows
                # (G7 MODEL K = F + 1) and the die.v K placeholder landings (no row): F = K - 1, the flight the strap assumes
                if not a.land_model:
                    raise SystemExit(f'dv_slice_cut: landing {i} has no land-plan row / S1 at {a.corner}')
                km = re.fullmatch(r"(\d+)'[dh]([0-9a-fA-F]+)", byname[i][3].get('k', '').strip())
                kk = int(r['K']) if r and r.get('K') else (int(km.group(2), 16 if "'h" in byname[i][3]['k'] else 10) if km else 1)
                r = dict(r or {}, E=(r or {}).get('E') or kk, K=kk)
                src = 'model'
                s1 = -(kk - 1) * T_ps
            else:
                s1 = r['s1'].get(a.corner)
            E_, D_ = int(r['E']), int(r.get('D', LPJ.get('D', 4)))
            K_ = int(r.get('K') or E_)      # S81-LBGAP/G8: the landing reads at K (bundle age), the window is K's
            # whole periods the lane clock lags beyond the single-cycle hop, kept inside the window: with the hop-0
            # gate and the calendar R0 = G + (N mod 2) the ring occupancy is K - 1 - F + (N mod 2), legal for
            # K - D + 1 <= F <= K - 1
            f_raw = math.ceil(-float(s1) / T_ps)
            F = min(max(f_raw, K_ - D_ + 1), K_ - 1) + a.flight_shift
            F = max(F, 0)
            cm = byname[i][3]
            ln = lines[i]
            ln = ln.replace(f'.ck_f({cm["ck_f"]})', f'.ck_f({i}__ckf_d)', 1).replace(f'.i({cm["i"]})', f'.i({i}__i_d)', 1)
            w = nets[re.match(r'[\w\\]+', cm['i']).group(0)][0] if re.fullmatch(r'[\w\\]+', cm['i'].strip()) else None
            if w is None:
                raise SystemExit(f'dv_slice_cut: landing {i} data is not a whole net: {cm["i"][:60]}')
            # CYCLE flight model (zero-delay RTL): Verilator 5.050 drops transport-delayed clock pulses, so the flight is
            # whole periods on the lane's own (gated) clock
            body.append(f'  wire {i}__ckf_d; wire [{w - 1}:0] {i}__i_d;   // lane flight {F} cycles ({a.corner}: S1 {float(s1):.1f} ps, E {E_}, K {K_}, D {D_})')
            body.append(f'  dv_flight_sim #(.W({w}), .F({F})) {i}__flight (.ck_in({cm["ck_f"]}), .rs({cm["rs"]}), .i_in({cm["i"]}), .ck_out({i}__ckf_d), .i_out({i}__i_d));')
            lines[i] = ln
            lane_dl[i] = dict(F=F, F_raw=f_raw, clipped=F - a.flight_shift != f_raw, s1_ps=float(s1), E=E_, D=D_, K=K_,
                              corner=a.corner, flight_shift=a.flight_shift, source=src)
    # TOKc-S81b (10-22): frame x-lane flight.  A landed frame (col_h*_l4_lp: ports xk / x / lk) lands each 276-b lane in
    # its OWN ot_s81_land ring inside dsfd_cfifo_crs4, read at the frame strap K = lk[3k +: 3] (bind_case frame_lk: max
    # land-plan K over the frame's x lanes, every lane at K).  The strap assumes the lane's routed flight, exactly as
    # a dsfd_dvland strap does, but the zero-delay RTL cut delivered xk / x with NO flight, so every K = 5 frame (long
    # station chains, F 3-4 at TT) faulted its lane ring at warm-up (occupancy K - 1 - F = 4 > D - 1) and the fault
    # reached the slice capc2 on the frame's ret word (rd[69]) -> slice block_fault (G9 HOST u_s_3S/4S, KV u_s_3N).
    # Same cycle model and window clamp as the landings above; land-plan link x_<frame>_l<k>; a lane without a row is
    # a no-station lane (K 1 -> F 0) or, with --land-model, F = K - 1 (the flight the strap assumes).
    frame_dl = {}
    if a.land_plan:
        def split_concat(e):
            e = e.strip()
            if not (e.startswith('{') and e.endswith('}')):
                return [e]
            return [s.strip() for s in e[1:-1].split(',')]
        for i in sorted(lines):
            cm = byname[i][3]
            if not all(p in cm for p in ('xk', 'x', 'lk')) or byname[i][0].startswith('dsfd_'):
                continue
            xk, xs = split_concat(cm['xk']), split_concat(cm['x'])
            km = re.fullmatch(r"(\d+)'([dhb])([0-9a-fA-F_]+)", cm['lk'].strip())
            if len(xk) != len(xs) or not km:
                raise SystemExit(f'dv_slice_cut: frame {i} xk/x/lk not per-lane literals: {cm["lk"][:40]}')
            nl = len(xk)
            lkv = int(km.group(3).replace('_', ''), {'d': 10, 'h': 16, 'b': 2}[km.group(2)])
            kw = int(km.group(1)) // nl
            fname = i[2:] if i.startswith('u_') else i
            nk, nx, rows = [], [], {}
            for pos, (ke, xe) in enumerate(zip(xk, xs)):
                lane = nl - 1 - pos                      # concatenation is high lane first
                K_ = (lkv >> (kw * lane)) & ((1 << kw) - 1)
                r = LP.get(f'x_{fname}_l{lane}')
                if r is not None and r.get('s1', {}).get(a.corner) is not None:
                    s1, src = float(r['s1'][a.corner]), 'land_plan'
                elif K_ <= 1:
                    s1, src = 0.0, 'no_row_K1'
                elif a.land_model:
                    s1, src = -(K_ - 1) * T_ps, 'model'
                else:
                    raise SystemExit(f'dv_slice_cut: frame lane x_{fname}_l{lane} (K {K_}) has no land-plan row at {a.corner}')
                D_ = int(LPJ.get('D', 4))
                f_raw = math.ceil(-s1 / T_ps)
                F = max(min(max(f_raw, K_ - D_ + 1), K_ - 1) + a.flight_shift, 0)
                rows[lane] = dict(F=F, F_raw=f_raw, clipped=F - a.flight_shift != f_raw, s1_ps=s1, K=K_, D=D_,
                                  corner=a.corner, flight_shift=a.flight_shift, source=src)
                if F == 0:
                    nk.append(ke); nx.append(xe); continue
                mw = re.fullmatch(r'([\w\\]+)\s*\[(\d+):(\d+)\]', xe)
                w = (int(mw.group(2)) - int(mw.group(3)) + 1) if mw else (nets[xe][0] if xe in nets else None)
                if w is None:
                    raise SystemExit(f'dv_slice_cut: frame {i} lane {lane} data is not a net / slice: {xe[:60]}')
                p = f'{i}__xl{lane}'
                body.append(f'  wire {p}__ckf_d; wire [{w - 1}:0] {p}__i_d;   // frame lane flight {F} cycles '
                            f'({a.corner}: S1 {s1:.1f} ps, K {K_}, D {D_}, {src})')
                body.append(f'  dv_flight_sim #(.W({w}), .F({F})) {p}__flight (.ck_in({ke}), .rs({cm["rst_n"]}), '
                            f'.i_in({xe}), .ck_out({p}__ckf_d), .i_out({p}__i_d));')
                nk.append(f'{p}__ckf_d'); nx.append(f'{p}__i_d')
            ln = lines[i]
            for port, old, new in (('xk', cm['xk'], nk), ('x', cm['x'], nx)):
                pat = f'.{port}({old})'
                if ln.count(pat) != 1:
                    raise SystemExit(f'dv_slice_cut: frame {i} .{port}(...) not found verbatim once')
                ln = ln.replace(pat, f'.{port}({{{", ".join(new)}}})', 1)
            lines[i] = ln
            frame_dl[i] = rows
    land_rl, land_rl_src = {}, None
    lr_path = (Path(a.die_v).parent / 'landing_reset_check.json') if a.landing_reset == 'auto' else \
        (None if a.landing_reset == 'none' else Path(a.landing_reset))
    if lr_path is not None and lr_path.exists():
        LR = json.loads(lr_path.read_text())
        if LR.get('verdict') != 'PASS':
            raise SystemExit(f'dv_slice_cut: {lr_path} verdict {LR.get("verdict")} (die calendar vs views unresolved)')
        rl_by_master = {r['master']: int(r['rl']) for r in LR['rows']}
        land_rl_src = dict(path=str(lr_path), sha256=hashlib.sha256(lr_path.read_bytes()).hexdigest(), by_master=rl_by_master)
        for i in sorted(lines):
            mst = byname[i][0]
            if not mst.startswith('dsfd_dvland'):
                continue
            if mst not in rl_by_master:
                raise SystemExit(f'dv_slice_cut: landing {i} master {mst} not in {lr_path}')
            rl = rl_by_master[mst]
            if rl <= 0:
                continue
            cm = byname[i][3]
            ln = lines[i]
            if ln.count(f'.rs({cm["rs"]})') != 1:
                raise SystemExit(f'dv_slice_cut: landing {i}: rs pin not found once')
            lines[i] = ln.replace(f'.rs({cm["rs"]})', f'.rs({i}__rs_l)', 1)
            body.append(f'  wire {i}__rs_l;   // kit reset landing {rl} stages ({mst} view)')
            body.append(f'  dv_rst_land #(.N({rl})) {i}__rl (.ck({cm["ck"]}), .rs({cm["rs"]}), .o({i}__rs_l));')
            land_rl[i] = rl
    elif a.landing_reset not in ('auto', 'none'):
        raise SystemExit(f'dv_slice_cut: --landing-reset {a.landing_reset} not found')
    lost = sorted(S - set(lines))
    if lost:
        raise SystemExit(f'dv_slice_cut: instance line not found verbatim for {lost[:5]}')
    hdr = '`timescale 1ns/1ps\n' + f'// {a.name}: cut by tools/s81_dv/dv_slice_cut.py from {Path(a.die_v).name} ({a.top}); {len(S)} instances, ' \
          f'{len(ports)} ports -- instance lines verbatim from the die netlist\nmodule {a.name} (\n' + \
          ',\n'.join(f'  {p}' for p in ports) + '\n);'
    sv = [hdr] + decl + body + [lines[i] for i in sorted(S, key=lambda x: list(byname).index(x))] + ['endmodule', '']
    if lane_dl or any(r['F'] for rows in frame_dl.values() for r in rows.values()):
        sv += [FLIGHT_SIM]
    if land_rl:
        sv += [RST_LAND]
    (out / f'{a.name}.sv').write_text('\n'.join(sv))
    (out / 'slice_ports.json').write_text(json.dumps(dict(schema='opentallas.s81_dv.slice_ports.v1', top=a.name,
                                                          die_v=a.die_v, ports=ports), indent=1) + '\n')
    cnt = Counter(byname[i][0] for i in S)
    (out / 'slice_insts.json').write_text(json.dumps(dict(instances=len(S), by_master=dict(sorted(cnt.items())),
                                                          how={i: how[i] for i in sorted(S)}, rom_instance_param=rom_inst, lane_flight_time=lane_dl, frame_lane_flight=frame_dl,
                                                          landing_reset=dict(source=land_rl_src, stages=land_rl)), indent=1) + '\n')
    nin = sum(sum(h - l + 1 for h, l in p['bits']) for p in ports.values() if p['dir'] == 'input')
    nout = sum(sum(h - l + 1 for h, l in p['bits']) for p in ports.values() if p['dir'] == 'output')
    print(f'dv_slice_cut: {len(S)} instances {dict(sorted(cnt.items()))}; ports {len(ports)} '
          f'(in bits {nin}, out bits {nout}; clock ports {sum(p["kind"] == "clock" for p in ports.values())})')
    return 0


if __name__ == '__main__':
    sys.exit(main())
