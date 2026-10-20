#!/usr/bin/env python3
"""KV-HEALTH 10-19: whole-plane logical bench generated from the EMITTED laned die netlist (not from the plan).

  kv_health_bench.py gen --run RUN --out DIR [--mutant none|drop_join_b|sink_nonsticky|hold128|ufh_unhooked]

The plane module copies every hp_* cell line of RUN/case_kv/die.v verbatim (real masters qkd_hp_or2 / qkd_rlys_1 /
qkd_astk_fault_join, their real RTL compiled in), and the kvs_attn.ufh connection as the health output.  Forwarded
lane bits in the cone are fixed-latency delay lines of the plan's transport latency (abstract: NOT CDC / phase evidence).
Every source net is a bench input; sticky sources hold until their region reset, the existing_ufh source is a 1-edge
pulse.  Checks (Verilator 5.050, random power-up state in every no-reset flop):
  POR    no source -> health stays 0 after the sink region release (no false positive from random flop state);
  each source alone: health rises EXACTLY at its leaf latency (0 one edge before -> STATUS boundary witness), stays 1
         (continuous sticky; a pulse source is retained);
  reset  re-assert: sources clear with their region, the sink region holds HOLD_K (273) edges -> health 0 for the whole
         plane depth after release (no stale in-flight re-latch); then the next source is admitted;
  dup    all sources together, and pairs -> health at the minimum latency, no glitch;
  late   a fault injected long after the boundary still raises health (never masked).
Mutants (each must FAIL with its regex): drop_join_b (one join loses an input), sink_nonsticky (sink feedback cut),
hold128 (sink region held only 128 edges: stale re-latch), ufh_unhooked (kvs_attn.ufh back on the old net).
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools' / 'qwen_kv_die'))
import kv_health_plane as H        # noqa: E402

RTL = ['rtl/qwen_sys/kv_health_20261019/qkd_hp_or2.sv', 'rtl/qwen_sys/kv_rly_std_20261016/qkd_rlys.sv',
       'rtl/qwen_sys/split_20261014/qkd_astk_phys.sv']
MUTANTS = ('none', 'drop_join_b', 'sink_nonsticky', 'hold128', 'ufh_unhooked')


def gen(run, out, mutant='none'):
    rep = json.loads((run / 'health_plane.json').read_text())
    plan = rep['plan']
    die = H.Die(run)
    text = (run / 'case_kv' / 'die.v').read_text().split('\n')
    hp_lines = [ln for ln in text if (m := H.INST.match(ln)) and m.group(3).startswith('hp_')]
    attn = next(ln for ln in text if (m := H.INST.match(ln)) and m.group(3) == 'kvs_attn')
    ufh = re.search(r'\.ufh\(([^()]*)\)', attn).group(1).strip()
    old_ufh = next(s for s in plan['sources'] if s['id'] == 'existing_ufh')['signal']
    old_ufh = f'{old_ufh[0]}[{old_ufh[1]}]'
    if mutant == 'ufh_unhooked':
        ufh = old_ufh
    sink = plan['sink']
    sticky_ids = {n['id'] for n in plan['nodes'] if n['kind'] == 'sticky'}
    if mutant == 'drop_join_b':
        j = next(k for k, ln in enumerate(hp_lines) if ' qkd_hp_or2 ' in ' ' + ln.strip() + ' ')
        hp_lines[j] = re.sub(r'\.b\([^()]*\)', ".b(1'b0)", hp_lines[j], count=1)
    if mutant == 'sink_nonsticky':
        j = next(k for k, ln in enumerate(hp_lines) if f' hp_{sink} ' in ln)
        hp_lines[j] = re.sub(r'\.b\([^()]*\)', ".b(1'b0)", hp_lines[j], count=1)
    # every net bit referenced by the plane
    used = {}
    for ln in hp_lines + [f'x y (.u({ufh}));']:
        for nm, bit in re.findall(r'(\bn_\w+)\[(\d+)\]', ln):
            used[nm] = max(used.get(nm, 0), int(bit))
    srcs = [s for s in plan['sources']]
    lat = {k: v for k, v in rep['leaf_latency'].items()}
    lat['existing_ufh'] -= H.AHUB_UFH_EDGES          # the 36 AHUB edges are upstream of the old ufh net
    cons_rst = next(n['reset'] for n in plan['nodes'] if n['id'] == sink)
    assigns, regs = [], []
    drivers = set()
    for k, s in enumerate(srcs):
        net = f"{s['signal'][0]}[{s['signal'][1]}]"
        assigns.append(f'  assign {net} = src[{k}];')
        drivers.add(net)
        used[s["signal"][0]] = max(used.get(s["signal"][0], 0), int(s["signal"][1]))
    # lanes: first-station input bit -> last-station output bit, L-cycle delay
    for t in plan['transports']:
        lane = next(l for l in rep_lanes(run) if l['id'] == t['lane_id'])
        chain, w, b = lane['stations'], lane['S'], t['payload_bit']
        a0 = die.bits(die.cells[chain[0]][2]['a'])[w - 1 - b]
        bl = die.bits(die.cells[chain[-1]][2]['b'])[w - 1 - b]
        L = int(t['latency_cycles'])
        nm = f'lane_{t["id"]}'
        regs.append(f'  reg [{L - 1}:0] {nm} /*verilator public*/;\n  always @(posedge ck) {nm} <= '
                    + (f'{{{nm}[{L - 2}:0], {a0[0]}[{a0[1]}]}};' if L > 1 else f'{a0[0]}[{a0[1]}];'))
        assigns.append(f'  assign {bl[0]}[{bl[1]}] = {nm}[{L - 1}];')
        for x in (a0, bl):
            used[x[0]] = max(used.get(x[0], 0), int(x[1]))
    clocks = sorted({re.search(r'\.ck\(([^()]*)\)', ln).group(1).strip() for ln in hp_lines})
    for c in clocks:
        assigns.append(f'  assign {c} = ck;')
    resets = sorted({re.search(r'\.rst_n\(([^()]*)\)', ln).group(1).strip() for ln in hp_lines if '.rst_n(' in ln})
    for r in resets:
        assigns.append(f'  assign {r} = ' + ('rst_k;' if r == cons_rst else 'rst_s;'))
    decl = [f'  wire [{w}:0] {nm};' for nm, w in sorted(used.items())]
    if mutant == 'ufh_unhooked':
        pass
    plane = ['`timescale 1ns/1ps', f'module kv_health_plane_dut(input wire ck, input wire rst_s, input wire rst_k,',
             f'    input wire [{len(srcs) - 1}:0] src, output wire health);'] + decl + assigns + regs + hp_lines + \
            [f'  assign health = {ufh};', 'endmodule']
    out.mkdir(parents=True, exist_ok=True)
    (out / 'plane.sv').write_text('\n'.join(plane) + '\n')
    pulse = [k for k, s in enumerate(srcs) if not s.get('sticky')]
    holdk = 128 if mutant == 'hold128' else 273
    dmax = max(lat.values())
    (out / 'lat.txt').write_text(''.join(f'{lat[s["id"]]:x}\n' for s in srcs))
    tb = TB.replace('NS', str(len(srcs))).replace('HOLDK', str(holdk)).replace('DMAX', str(dmax)) \
        .replace('PULSEMASK', "{" + ', '.join(("1'b1" if k in pulse else "1'b0") for k in reversed(range(len(srcs)))) + "}")
    (out / 'tb.sv').write_text(tb)
    meta = dict(sources=len(srcs), cells=len(hp_lines), transports=len(plan['transports']), dmax_plane=dmax,
                hold_k=holdk, mutant=mutant, ufh=ufh, rtl=RTL, clocks=clocks, resets=resets, sink_reset=cons_rst,
                qualification='logical plane on the emitted netlist; lane transports abstract fixed delays')
    (out / 'manifest.json').write_text(json.dumps(meta, indent=1) + '\n')
    return meta


def rep_lanes(run):
    if not hasattr(rep_lanes, 'c'):
        rep_lanes.c = [dict(l, id=f'lane_{n}') for n, l in enumerate(json.loads((run / 'fwd_lanes.json').read_text())['lanes'])]
    return rep_lanes.c


TB = r'''`timescale 1ns/1ps
module tb;
  reg ck = 0; always #0.5 ck = ~ck;
  reg rst_s = 0, rst_k = 0;
  reg [NS-1:0] src = 0;
  wire health;
  kv_health_plane_dut dut (.ck(ck), .rst_s(rst_s), .rst_k(rst_k), .src(src), .health(health));
  integer lat [0:NS-1];
  localparam [NS-1:0] PULSE = PULSEMASK;
  integer i, j, t, errs = 0, cyc = 0, checks = 0, minl;
  always @(posedge ck) cyc <= cyc + 1;
  task fail(input [8*40-1:0] what, input integer s); begin
    errs = errs + 1; if (errs < 12) $display("%0s src=%0d cyc=%0d lat=%0d", what, s, cyc, (s >= 0) ? lat[s] : -1);
  end endtask
  // host re-assert: every region drops; sources clear with their region; the source regions release after 4 edges,
  // the sink region after HOLDK edges (qkd_rst_region HOLD) -- then no stale fault may re-latch
  task region_reset; begin
    @(negedge ck); rst_s = 0; rst_k = 0; src = 0;
    repeat (4) @(negedge ck); rst_s = 1;
    repeat (HOLDK - 4) @(negedge ck); rst_k = 1;
    for (t = 0; t < DMAX + 12; t = t + 1) begin @(negedge ck); checks = checks + 1; if (health) fail("HEALTH_STALE_RELATCH", -1); end
  end endtask
  task one(input integer s); integer k; begin
    @(negedge ck); src[s] = 1'b1;                      // asserted for the edge at k = 1
    for (k = 1; k <= lat[s] + 4; k = k + 1) begin
      @(negedge ck); if (PULSE[s]) src[s] = 1'b0;
      checks = checks + 1;
      if (k < lat[s] && health) fail("HEALTH_EARLY", s);
      if (k >= lat[s] && !health) fail(k == lat[s] ? "HEALTH_MISSING_AT_LATENCY" : "HEALTH_NOT_STICKY", s);
    end
    repeat (8) begin @(negedge ck); checks = checks + 1; if (!health) fail("HEALTH_NOT_STICKY", s); end
    region_reset;
  end endtask
  initial begin
    $readmemh("lat.txt", lat);
    // POR: random flop state; sources in reset, sink region held; then released with no source
    repeat (300) @(negedge ck); rst_s = 1; repeat (HOLDK) @(negedge ck); rst_k = 1;
    for (t = 0; t < 2 * DMAX; t = t + 1) begin @(negedge ck); checks = checks + 1; if (health) fail("HEALTH_FALSE_POSITIVE", -1); end
    for (i = 0; i < NS; i = i + 1) one(i);
    // duplicate: all sources together -> the minimum latency, then pairs
    minl = 100000; for (i = 0; i < NS; i = i + 1) if (lat[i] < minl) minl = lat[i];
    @(negedge ck); src = {NS{1'b1}};
    for (t = 1; t <= minl + 2; t = t + 1) begin
      @(negedge ck); src = src & ~PULSE; checks = checks + 1;
      if (t < minl && health) fail("HEALTH_DUP_EARLY", -1);
      if (t >= minl && !health) fail("HEALTH_DUP_MISSING", -1);
    end
    region_reset;
    for (i = 0; i + 1 < NS; i = i + 37) begin
      @(negedge ck); src[i] = 1; src[i + 1] = 1; j = (lat[i] > lat[i + 1]) ? lat[i] : lat[i + 1];
      repeat (j + 2) @(negedge ck); src = src & ~PULSE; checks = checks + 1; if (!health) fail("HEALTH_PAIR_MISSING", i);
      region_reset;
    end
    // late: long after any STATUS boundary the plane still raises health
    repeat (3000) @(negedge ck); src[NS - 1] = 1; @(negedge ck); src = src & ~PULSE;
    repeat (lat[NS - 1] + 2) @(negedge ck); checks = checks + 1; if (!health) fail("HEALTH_LATE_MASKED", NS - 1);
    if (errs) begin $display("KV_HEALTH_PLANE_FAIL errors=%0d checks=%0d", errs, checks); $fatal(1); end
    $display("KV_HEALTH_PLANE_PASS sources=NS dmax_plane=DMAX hold_k=HOLDK checks=%0d cycles=%0d", checks, cyc);
    $finish;
  end
endmodule
'''


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sp = ap.add_subparsers(dest='cmd', required=True)
    g = sp.add_parser('gen')
    g.add_argument('--run', type=Path, required=True)
    g.add_argument('--out', type=Path, required=True)
    g.add_argument('--mutant', choices=MUTANTS, default='none')
    a = ap.parse_args(argv)
    print(json.dumps(gen(a.run, a.out, a.mutant)))


if __name__ == '__main__':
    main()
