#!/usr/bin/env python3
"""Edge-exact chained-frame landing probe of a corrected die (S81-P9-FC 10-23; successor of the calendar-v2 probe).

The calendar-v2 probe started each chained lane at the UPSTREAM hop-0 gate and so missed the upstream lane flight
(the chained frame is clocked by the upstream frame's LANDED xk) and its own flight, and tied every landing to K 2:
it passed while fc30 u_f_3L03 faulted.  This vehicle extracts, from the corrected die, for every frame
frame_chain_reset_v2 changed AND its upstream frame:
  * the real reset cone (die rst_n -> dsfd_rly_1 stations, real ot_s81_rly W1 bodies) of the frame rst_n and of
    every hop-0 / chained lane ICG enable;
  * each lane clock: ICG -> the N forwarded stations' ck_o (dsfd_dvrlyh_* inverting, dsfd_dvrly_* 2 inverters) ->
    dv_flight_sim(F) with F from the GEN land plan at the corner (dv_slice_cut rule) -> frame xk;
    a chained lane's ICG is clocked by the upstream frame's xok[k] = its landed xk[k] (u_xo<k>, 2 inverters);
  * the frame landing: rst_n -> FRH10 2-stage pad on ck_r0 -> crs4 rsync (2 flops) -> real ot_s81_land per lane with
    the die's own lk strap.
Common-phase regional roots (as the cut benches); no datapath, ROM, arithmetic or physical skew claim.
+MUT=k selects, on every changed frame, the reset k stations before the corrected one (k = delay = the uncorrected
die; k = 4 on the 9 calendar-v2 frames = fc30): a real landing epoch fault must be caught.
Build with +define+FRAME_CAL_FF for the ff-corner flights (default tt).

usage: frame_chain_reset_probe.py --original die.v --corrected die.v --land-plan land.json --source-root SRC --out DIR
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
from frame_chain_reset_v2 import inspect
from dv_slice_cut import FLIGHT_SIM


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--original', required=True)
    ap.add_argument('--corrected', required=True)
    ap.add_argument('--land-plan', required=True)
    ap.add_argument('--source-root', required=True, help='executed source snapshot (ot_s81_rly / ot_s81_land bodies)')
    ap.add_argument('--sync', type=int, default=4)
    ap.add_argument('--out', required=True)
    a = ap.parse_args(); out = Path(a.out); out.mkdir(parents=True, exist_ok=False)
    land = json.loads(Path(a.land_plan).read_text())
    old = Path(a.original).read_text(); new = Path(a.corrected).read_text()
    _, changed, _, _ = inspect(old, a.sync, land)
    assert changed and not any(c.get('infeasible') for c in changed.values()), 'nothing (feasible) to probe'
    frames, after, relays, aliases = inspect(new, a.sync, land)
    assert not after, ('corrected die still needs delays', sorted(after))
    use = sorted(set(changed) | {u for c in changed.values() for u in c['upstream']})
    L = ['`timescale 1ns/1ps', 'module tb_frame_calendar;', 'reg ck = 0, por = 1; always #0.5 ck = ~ck;',
         'integer mut = 0, cyc = -1; initial begin void\'($value$plusargs("MUT=%d", mut)); #0.1 por = 0; #2.0 por = 1; end',
         'always @(posedge ck) if (por) cyc <= cyc + 1;']
    nets = set()
    def take(n):
        if n in nets:
            return n
        nets.add(n)
        if n in relays:
            r = relays[n]; take(r['inp']); assert r['rs'] == r['inp'], ('reset station rs != i', n)
            L.append(f'wire {n}; {r["master"]} {r["inst"]} (.ck(ck), .rs({r["inp"]}), .i({r["inp"]}), .o({n}));')
        elif n in aliases and n != 'rst_n':
            take(aliases[n]); L.append(f'wire {n}; assign {n} = {aliases[n]};')
        else:
            assert n in ('rst_n', 'i__rst_n', 'rst_sync1'), ('unknown reset root', n)
            L.append(f'wire {n} = por;')
        return n
    checks, counters = [], []
    for f in use:
        d = frames[f]; take(d['rst'])
        rst = d['rst']
        if f in changed:
            c = changed[f]; chain = [c['reset']] + [f'rsfc2_{f}_{k}' for k in range(c['delay'])]
            assert chain[-1] == rst, ('corrected frame reset is not the recorded station chain', f, rst)
            for n in chain:
                take(n)
            sel = ' : '.join(f'(mut == {k}) ? {chain[-1 - k]}' for k in range(1, c['delay'] + 1))
            L.append(f'wire {f}_rst = {sel} : {rst};')
            rst = f'{f}_rst'
        L += [f'reg [1:0] {f}_pad = 0; always @(posedge ck) {f}_pad <= {{{f}_pad[0], {rst}}};   // FRH10 u_frl_rst',
              f'reg [1:0] {f}_rsq = 0; always @(posedge ck or negedge {f}_pad[1]) if (!{f}_pad[1]) {f}_rsq <= 0; '
              f'else {f}_rsq <= {{{f}_rsq[0], 1\'b1}};   // crs4 rsync', f'wire {f}_rs = {f}_rsq[1];', f'wire [3:0] {f}_xok;']
        for l in d['lanes']:
            g = l['gate']; take(g['ena']); p = f'{f}_l{l["lane"]}'
            up = re.fullmatch(r'(u_f_\w+?)_xok\[(\d+)\]', g['ck'])
            ckn = f'{up[1]}_xok[{up[2]}]' if up else 'ck'
            assert up or g['ck'] not in nets, g['ck']
            L.append(f'wire {p}_g; ICGx4_ASAP7_75t_R {g["inst"]} (.CLK({ckn}), .ENA({g["ena"]}), .SE(1\'b0), .GCLK({p}_g));')
            L.append(f'wire {p}_f = {"~" if l["inv"] % 2 else ""}{p}_g;   // {l["stages"]} stations, {l["inv"]} half-cycle')
            L.append(f'wire {p}_xk; `ifdef FRAME_CAL_FF dv_flight_sim #(.W(1), .F({l["F"]["ff"]})) `else '
                     f'dv_flight_sim #(.W(1), .F({l["F"]["tt"]})) `endif {p}_fl (.ck_in({p}_f), .rs(1\'b1), .i_in(1\'b0), '
                     f'.ck_out({p}_xk), .i_out());')
            L += [f'assign {f}_xok[{l["lane"]}] = {p}_xk;   // u_xo{l["lane"]} ck_o',
                  f'wire {p}_o, {p}_fault;',
                  f'ot_s81_land #(.W(1), .D(4)) {p}_land (.k(3\'d{l["K"]}), .ck_f({p}_xk), .i(1\'b0), .ck(ck), .rs({f}_rs), '
                  f'.o({p}_o), .fault({p}_fault));',
                  f'integer {p}_w = 0, {p}_lost = 0; always @(posedge {p}_xk) if ($time > 0) begin {p}_w = {p}_w + 1; '
                  f'if (!{f}_rs) {p}_lost = {p}_lost + 1; end',
                  f'real {p}_A = -1, {p}_R = -1; always @(posedge {p}_xk) if ($time > 0 && {p}_A < 0) {p}_A = $realtime; '
                  f'always @(posedge {f}_rs) if ({p}_R < 0) {p}_R = $realtime;']
            checks.append((f, l['lane'], p)); counters.append(f'{p}_w')
    ncy = max(frames[f]['release'] for f in use) + 64
    L += [f'initial begin repeat({ncy}) @(negedge ck);',
          ' `ifdef FRAME_CAL_FF $display("FRAME_CAL corner ff mut=%0d", mut); `else $display("FRAME_CAL corner tt mut=%0d", mut); `endif']
    for f, k, p in checks:
        L.append(f' $display("FRAME_CAL {f} l{k} chained={int(f in changed)} dt=%0.1f lost=%0d fault=%0d writes=%0d", '
                 f'{p}_A - {p}_R, {p}_lost, {p}_fault, {p}_w);')
    L += [' if (' + ' | '.join(p + '_fault' for _, _, p in checks) + ') $fatal(1, "FRAME_CAL FAIL real landing epoch fault");',
          ' if (' + ' || '.join(p + '_lost != 0' for _, _, p in checks) + ') $fatal(1, "FRAME_CAL FAIL forwarded edge before release");',
          ' if (' + ' || '.join(n + ' < 32' for n in counters) + ') $fatal(1, "FRAME_CAL FAIL unexercised lane");',
          f' $display("FRAME_CAL PASS changed={len(changed)} frames={len(use)} lanes={len(checks)}"); $finish; end', 'endmodule']
    root = Path(a.source_root); hashes = {}
    for p in ('rtl/dsrom_sys/s81_glue/ot_s81_rly.sv', 'rtl/dsrom_sys/s81_dv/land/ot_s81_land.sv'):
        body = (root / p).read_bytes(); (out / Path(p).name).write_bytes(body); hashes[p] = hashlib.sha256(body).hexdigest()
    masters = sorted({relays[n]['master'] for n in nets if n in relays})
    cell = '\n'.join(f'module {m}(input ck, rs, i, output o); ot_s81_rly #(.W(1)) u(.ck(ck), .rs(rs), .i(i), .o(o)); endmodule'
                     for m in masters)
    cell += ('\nmodule ICGx4_ASAP7_75t_R(input CLK, ENA, SE, output GCLK); reg en_l; /* verilator lint_off COMBDLY */ '
             'always_latch if (!CLK) en_l = ENA | SE; /* verilator lint_on COMBDLY */ assign GCLK = CLK & en_l; endmodule\n')
    cell += FLIGHT_SIM
    (out / 'cells.sv').write_text(cell); (out / 'tb_frame_calendar.sv').write_text('\n'.join(L) + '\n')
    (out / 'source.json').write_text(json.dumps(dict(
        original_sha256=hashlib.sha256(old.encode()).hexdigest(), corrected_sha256=hashlib.sha256(new.encode()).hexdigest(),
        land_plan_sha256=hashlib.sha256(Path(a.land_plan).read_bytes()).hexdigest(), actual_source_sha256=hashes,
        reset_stations=len([n for n in nets if n in relays]), frames=use,
        delays={i: c['delay'] for i, c in changed.items()}, mutants=sorted({k for c in changed.values() for k in range(1, c['delay'] + 1)}),
        scope='real reset cone + lane clock parity + land-plan flights (dv_slice_cut rule) + real W1 landings with die lk; '
              'common-phase roots; no datapath or physical skew claim'), indent=1) + '\n')
    print('frames', len(use), 'lanes', len(checks), 'delays', {i: c['delay'] for i, c in changed.items()})


if __name__ == '__main__':
    main()
