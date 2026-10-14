#!/usr/bin/env python3
"""VM lane BAY as a routed cluster of its closed tiles (VM4, 2026-10-13): netlist + bench + ref_tile cluster spec of ONE
bay of the tile-level lane plan (vm_bay_tiles.py), with the bay's real lanes, tile kits and pin assignment.

    python3 tools/qwen_tp8/vm_bay_cluster.py BAY [--tiles results/arch/qwen_tp8_1012/vm_bay_tiles_claude.json] [--frame 21.6]
    python3 tools/qwen_tp8/vm_bay_cluster.py --alias          # (re)write the renamed view ot_qfd_vm_xrelay_w only

What it writes (BAY = vm_pad_15_S0 -> tag pad15s):
  rtl/qwen_sys/vm_plane_20261013/bay/ot_qfd_vm_bay_<tag>.sv      wires + hard children only: the bay's tiles in slot order
       (ot_qfd_vm_xpad2_t W 480, ot_qfd_vm_xrelay_t, ot_qfd_vm_xrelay_w = the mirrored-pin view) + ONE me fan stage
       (ot_qfd_vm_fan_t W 1 EN 0: me_d -> every tile's me_e).  One 8-b lane port pair per lane visit, grouped by the
       face of the neighbour it comes from / goes to: d_w / d_e / d_s in, q_w / q_e / q_n / q_s out.  Unused tile inputs are
       tied low.  MUT (bench only): 1 = lane 0 leaves one tile early, 2 = lanes 0 and 1 swapped at their last tile.
  rtl/qwen_sys/vm_plane_20261013/bay/tb_qfd_vm_bay_<tag>.sv      exact bench: every lane's 8 bits against a behavioural
       me-enabled shift register of the lane's planned stage count in this bay, every clock, random me; counts lanes and stages
  results/arch/qwen_tp8_1012/vm_bay_<tag>.json                   the lane table (ports, tiles, bit positions, stages)
  physical/ref_tile/qfd_vm_bay_<tag>.spec.json                   ref_tile cluster spec (children at the plan pitch 21.6 um)
The mirrored relay is the SAME closed route as kit qfd_vm_xrelay_w (module ot_qfd_vm_xrelay_t with d on E / q on W); two
views of one module name cannot stand in one netlist, so the view is re-published under the cell name ot_qfd_vm_xrelay_w
(LEF MACRO / Liberty cell renamed, nothing else; alias.json holds the source hashes) with a one-line RTL wrapper."""
import argparse, collections, hashlib, json, re, shutil, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
P = 'rtl/qwen_sys/vm_plane_20261013'
TW, SGAP = 17.28, 4.32
MOD = {'E': 'ot_qfd_vm_xrelay_t', 'W': 'ot_qfd_vm_xrelay_w', 'P': 'ot_qfd_vm_xpad2_t'}
VIEW = {'E': 'physical/ref_tile/qfd_vm_xrelay_t/views/ot_qfd_vm_xrelay_t', 'W': 'physical/ref_tile/qfd_vm_xrelay_w/views/ot_qfd_vm_xrelay_w',
        'P': 'physical/ref_tile/qfd_vm_xpad2_t/views/ot_qfd_vm_xpad2_t', 'F': 'physical/ref_tile/qfd_vm_fan_me/views/ot_qfd_vm_fan_t'}
WID = {'E': 512, 'W': 512, 'P': 480}


def alias():
    src = ROOT / 'physical/ref_tile/qfd_vm_xrelay_w/views/ot_qfd_vm_xrelay_t'; dst = ROOT / VIEW['W']; dst.mkdir(parents=True, exist_ok=True)
    rec = dict(schema='opentallas.qwen-tp8.view-alias.v1', cell='ot_qfd_vm_xrelay_w', source_view=str(src.relative_to(ROOT)), source_job='qfd_vm_xrelay_w-xw1-5a0fc3266',
               what='the closed mirrored-pin relay view re-published under its own cell name (LEF MACRO / FOREIGN / END and the Liberty cell + library names); geometry, pins, timing arcs untouched', files={})
    for f in sorted(src.iterdir()):
        if f.suffix not in ('.lef', '.lib') and f.name != 'insertion.json': continue
        t = f.read_text(); n = f.name.replace('ot_qfd_vm_xrelay_t', 'ot_qfd_vm_xrelay_w')
        if f.suffix in ('.lef', '.lib'): t = re.sub(r'\bot_qfd_vm_xrelay_t\b', 'ot_qfd_vm_xrelay_w', t)
        (dst / n).write_text(t); rec['files'][n] = dict(source=f.name, source_sha256=hashlib.sha256(f.read_bytes()).hexdigest())
    for f in ('abstract.json', 'child_lint.json'):
        d = json.loads((src / f).read_text())
        if f == 'abstract.json': d['name'] = 'ot_qfd_vm_xrelay_w'; d['alias_of'] = 'ot_qfd_vm_xrelay_t (kit qfd_vm_xrelay_w)'
        (dst / f).write_text(json.dumps(d, indent=1) + '\n')
    (dst / 'alias.json').write_text(json.dumps(rec, indent=1) + '\n')
    return dst


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('bay', nargs='?'); ap.add_argument('--alias', action='store_true')
    ap.add_argument('--tiles', default='results/arch/qwen_tp8_1012/vm_bay_tiles_claude.json'); ap.add_argument('--plan', default='results/arch/qwen_tp8_1012/vm_leaf_plan_claude.json')
    ap.add_argument('--frame', type=float, default=21.6); ap.add_argument('--tag', default='')
    a = ap.parse_args()
    alias()
    if a.alias or not a.bay: return
    T = json.loads((ROOT / a.tiles).read_text()); plan = json.loads((ROOT / a.plan).read_text())
    bays = {b['n']: b for b in plan['x_relay_bays']}; ch = {c['n']: c for c in plan['children']}; B = bays[a.bay]
    tag = a.tag or a.bay.replace('vm_', '').replace('_', '').lower(); top = f'ot_qfd_vm_bay_{tag}'
    tl = T['bay_tiles'][a.bay]; cxy = lambda o: (o['x'] + o['w'] / 2, o['y'] + o['h'] / 2); bc = cxy(B)
    def face(o, col=False):
        if col: return 'n' if o['y'] > B['y'] else 's'
        x, y = cxy(o); dx, dy = x - bc[0], y - bc[1]
        return ('e' if dx > 0 else 'w') if abs(dx) >= abs(dy) else ('n' if dy > 0 else 's')
    lanes = []
    for name, chain in T['lane_chain'].items():
        for i, c in enumerate(chain):
            if c['bay'] != a.bay: continue
            src, pl = name.split('>')
            fi = face(bays[chain[i - 1]['bay']]) if i else face(ch[src])
            fo = face(bays[chain[i + 1]['bay']]) if i + 1 < len(chain) else face(ch[f'vm_xcol_{pl[1:]}'], col=True)
            lanes.append(dict(lane=name, visit=c['visit'], fin=fi, fout=fo, stages=c['stages'], tiles=c['tiles'], frm=chain[i - 1]['bay'] if i else src,
                              to=chain[i + 1]['bay'] if i + 1 < len(chain) else f'vm_xcol_{pl[1:]}'))
    lanes.sort(key=lambda l: (l['tiles'][0]['slot'], l['tiles'][0]['bit0']))
    nin = collections.Counter(); nout = collections.Counter()
    for l in lanes:
        l['pin'] = (f"d_{l['fin']}", 8 * nin[l['fin']]); nin[l['fin']] += 1
        l['pout'] = (f"q_{l['fout']}", 8 * nout[l['fout']]); nout[l['fout']] += 1
    # ---------------------------------------------------------------- netlist
    V = [f'// GENERATED by tools/qwen_tp8/vm_bay_cluster.py {a.bay} -- do not edit (lane table results/arch/qwen_tp8_1012/vm_bay_{tag}.json)',
         f'// Qwen TP8 VM lane bay {a.bay}: {len(tl)} closed tiles in {B["tiles"]} slots, {len(lanes)} lane visits of 8 b, {sum(8 * l["stages"] for l in lanes)} stage bits.',
         '// Wires + hard children only.  me_d = the me tree level-1 word (one fan stage here, then the tiles\' own me_e flop).',
         f'module {top} #(parameter integer MUT = 0) (', '    input  wire clk,', '    input  wire me_d,']
    for f in 'wesn':
        if nin[f]: V.append(f'    input  wire [{8 * nin[f] - 1}:0] d_{f},')
    outs = [f'    output wire [{8 * nout[f] - 1}:0] q_{f}' for f in 'wesn' if nout[f]]
    V += [',\n'.join(outs), ');', '    wire me_f;',
          '`ifndef OT_QFD_VM_HARD', '    ot_qfd_vm_fan_t #(.W(1), .EN(0), .MEREG(1)) u_fan (.clk(clk), .me_e(1\'b0), .d(me_d), .q(me_f));',
          '`else', '    ot_qfd_vm_fan_t u_fan (.clk(clk), .me_e(1\'b0), .d(me_d), .q(me_f));', '`endif']
    for t in tl:
        w = WID[t['kind']]; s = t['slot']
        V += [f'    wire [{w - 1}:0] td{s}, tq{s};', '`ifndef OT_QFD_VM_HARD',
              f'    {MOD[t["kind"]]} #(.W({w}), .MEREG(1)) u_t{s} (.clk(clk), .me_e(me_f), .d(td{s}), .q(tq{s}));', '`else',
              f'    {MOD[t["kind"]]} u_t{s} (.clk(clk), .me_e(me_f), .d(td{s}), .q(tq{s}));', '`endif']
    used = collections.defaultdict(set)
    for k, l in enumerate(lanes):
        prev = f'{l["pin"][0]}[{l["pin"][1]} +: 8]'
        for j, sg in enumerate(l['tiles']):
            src = prev
            if k < 2 and j == len(l['tiles']) - 1:       # MUT 2: lanes 0 / 1 swapped at their last tile
                o = lanes[1 - k]; op = (f'tq{o["tiles"][-2]["slot"]}[{o["tiles"][-2]["bit0"]} +: 8]' if len(o['tiles']) > 1 else f'{o["pin"][0]}[{o["pin"][1]} +: 8]')
                src = f'(MUT == 2) ? {op} : {prev}'
            V.append(f'    assign td{sg["slot"]}[{sg["bit0"]} +: 8] = {src};'); used[sg['slot']].add(sg['bit0'])
            before = prev; prev = f'tq{sg["slot"]}[{sg["bit0"]} +: 8]'
        V.append(f'    assign {l["pout"][0]}[{l["pout"][1]} +: 8] = ' + (f'(MUT == 1) ? {before} : {prev};' if k == 0 else f'{prev};'))
    for t in tl:
        for b0 in range(0, WID[t['kind']], 8):
            if b0 not in used[t['slot']]: V.append(f'    assign td{t["slot"]}[{b0} +: 8] = 8\'h00;')
    V.append('endmodule')
    od = ROOT / P / 'bay'; od.mkdir(exist_ok=True)
    (od / f'{top}.sv').write_text('\n'.join(V) + '\n')
    # ---------------------------------------------------------------- bench
    NL = len(lanes); MS = max(l['stages'] for l in lanes)
    tb = [f'// GENERATED by tools/qwen_tp8/vm_bay_cluster.py {a.bay} -- do not edit',
          '`timescale 1ns/1ps', f'module tb_qfd_vm_bay_{tag} #(parameter integer MUT = 0, parameter integer SEED = 1, parameter integer CYCLES = 4000);',
          '    reg clk = 0; always #1 clk = ~clk;', '    reg me_d = 0;'] + [f'    reg [{8 * nin[f] - 1}:0] d_{f} = 0;' for f in 'wesn' if nin[f]] + \
         [f'    wire [{8 * nout[f] - 1}:0] q_{f};' for f in 'wesn' if nout[f]] + \
         [f'    {top} #(.MUT(MUT)) dut (.clk(clk), .me_d(me_d)' + ''.join(f', .d_{f}(d_{f})' for f in 'wesn' if nin[f]) + ''.join(f', .q_{f}(q_{f})' for f in 'wesn' if nout[f]) + ');',
          f'    localparam integer NL = {NL}, MS = {MS};', '    reg [7:0] sh [0:NL-1][0:MS-1];', '    reg [7:0] din [0:NL-1];', '    wire [7:0] got [0:NL-1];', '    integer st [0:NL-1];',
          '    reg me1 = 0, me2 = 0;', '    integer i, k, cyc = 0, errors = 0, checks = 0, moves = 0, seed;']
    for k, l in enumerate(lanes):
        tb.append(f'    assign got[{k}] = {l["pout"][0]}[{l["pout"][1]} +: 8]; always @* din[{k}] = {l["pin"][0]}[{l["pin"][1]} +: 8];')
    tb += ['    initial begin', '        seed = SEED;'] + [f'        st[{k}] = {l["stages"]};' for k, l in enumerate(lanes)] + \
          ['        for (i = 0; i < NL; i = i + 1) for (k = 0; k < MS; k = k + 1) sh[i][k] = 8\'h00;', '    end',
           '    // the fan stage and the tiles\' me_e flop: a tile stage moves two edges after me_d',
           '    always @(posedge clk) begin', '        me1 <= me_d; me2 <= me1;',
           '        if (me2) begin moves = moves + 1; for (i = 0; i < NL; i = i + 1) begin for (k = MS - 1; k > 0; k = k - 1) sh[i][k] <= sh[i][k-1]; sh[i][0] <= din[i]; end end',
           '    end',
           '    reg [63:0] rs;', '    function [7:0] rnd8; input dummy; begin rs = rs ^ (rs << 13); rs = rs ^ (rs >> 7); rs = rs ^ (rs << 17); rnd8 = rs[23:16] ^ rs[47:40]; end endfunction',
           '    initial rs = 64\'h9E3779B97F4A7C15 ^ {32\'d0, SEED[31:0]} ^ ({32\'d0, SEED[31:0]} << 32);',
           '    always @(negedge clk) begin', '        cyc = cyc + 1;', '        me_d = (rnd8(0) % 8) != 0;'] + \
          [f'        for (i = 0; i < {nin[f]}; i = i + 1) d_{f}[i*8 +: 8] = rnd8(0);' for f in 'wesn' if nin[f]] + \
          ['        if (cyc > 4 + 2 * MS) for (i = 0; i < NL; i = i + 1) begin checks = checks + 1; if (got[i] !== sh[i][st[i]-1]) begin errors = errors + 1;',
           '            if (errors <= 5) $display("  mismatch cyc %0d lane %0d got %02x exp %02x", cyc, i, got[i], sh[i][st[i]-1]); end end',
           '        if (cyc == CYCLES) begin',
           f'            if (moves < CYCLES / 2) begin $display("FAIL qfd_vm_bay_{tag} VACUOUS moves=%0d", moves); $finish; end',
           f'            if (errors != 0) $display("FAIL qfd_vm_bay_{tag} MUT=%0d errors=%0d of %0d", MUT, errors, checks);',
           f'            else $display("PASS qfd_vm_bay_{tag} exact %0d checks: lanes={NL} stage_bits={sum(8 * l["stages"] for l in lanes)} tiles={len(tl)} moves=%0d", checks, moves);',
           '            $finish;', '        end', '    end', 'endmodule']
    (od / f'tb_qfd_vm_bay_{tag}.sv').write_text('\n'.join(tb) + '\n')
    # ---------------------------------------------------------------- lane table + spec
    fr = a.frame; g = lambda v, q=2.16: round(round(v / q) * q, 4)
    x0 = g(fr + 2.16); y0 = g(fr + 4.32)
    W_ = g((x0 + B['tiles'] * (TW + SGAP) - SGAP + fr + 2.16) / 8.64 + 0.4999, 1) * 8.64; H_ = g((y0 + 97.2 + fr + 2.16) / 8.64 + 0.4999, 1) * 8.64
    children = [dict(view=VIEW[t['kind']], count=1, inst=f'u_t{t["slot"]}', at=[g(x0 + t['slot'] * (TW + SGAP)), y0], orient='R0') for t in tl]
    children.append(dict(view=VIEW['F'], count=1, inst='u_fan', at=[g(x0 + 2.16), g(y0 - 12.96)], orient='R0'))
    pins = {'W': [p for p in ('d_w', 'q_w') if (nin if p[0] == 'd' else nout)[p[2]]], 'E': [p for p in ('d_e', 'q_e') if (nin if p[0] == 'd' else nout)[p[2]]],
            'S': ['clk', 'me_d'] + [p for p in ('d_s', 'q_s') if (nin if p[0] == 'd' else nout)[p[2]]], 'N': [p for p in ('d_n', 'q_n') if (nin if p[0] == 'd' else nout)[p[2]]]}
    srcs = [f'{P}/bay/{top}.sv', f'{P}/bay/ot_qfd_vm_xrelay_w.sv', f'{P}/ot_qfd_vm_xplane.sv', f'{P}/ot_qfd_vm_xpad2.sv', f'{P}/ot_qfd_vm_xtree.sv', 'rtl/hdc/ot_hdc_delay.sv']
    vb = ('mkdir -p {RUN}/bench && $HOME/.local/opentallas-tools/verilator-5.050/bin/verilator --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-TIMESCALEMOD -Wno-PINMISSING '
          f'-CFLAGS -O0 -j 2 --top-module tb_qfd_vm_bay_{tag} %s --Mdir {{RUN}}/bench/%s {P}/bay/tb_qfd_vm_bay_{tag}.sv ' + ' '.join(srcs) +
          f' > {{RUN}}/bench/%s.build.log 2>&1 && {{RUN}}/bench/%s/Vtb_qfd_vm_bay_{tag} > {{RUN}}/bench/%s.log 2>&1; tail -3 {{RUN}}/bench/%s.log; grep -q \'^PASS qfd_vm_bay_{tag}\' {{RUN}}/bench/%s.log')
    def bench(n, args, exp): return dict(name=n, cmd=vb % ((args, n) + (n,) * 5), expect=exp, threads=2, peak_ram_gb=4, needs=['verilator'])
    spec = dict(name=f'qfd_vm_bay_{tag}', top=top, kind='cluster', sources=srcs, params={}, clock_port='clk', reset_ports=[], hard_define='OT_QFD_VM_HARD', defines=['OT_QFD_VM_HARD'],
                outline=dict(w=W_, h=H_), child_lattice_um=2.16, children=children,
                abut_plan=dict(channel_um=4.32, edge_um=8.64, why='the VM lane plan stands relay / pad tiles at 21.6-um pitch (4.32-um channels, pins face to face); this probe routes the fullest bay to measure that channel'), pins=pins, inter=['*'], refglob='*',
                slot_change_request='el1011-qwen-tp8.log 2026-10-13 VM4: bay PILOT, not a die slot: the fullest pad-row bay of the tile-level lane plan with a 21.6-um routing frame; the band cluster takes these tiles flat',
                route=dict(pd=0.5, period_ps=770, threads=8, peak_ram_gb=16, hold_margin_ns=0.03),
                job=dict(owner='Claude:qwen_tp8_vm4', branch='claude/qwen-tp8-vm-phys', tag='bp2',
                         purpose=f'Qwen TP8 VM lane-bay PILOT ({a.bay}, the fullest pad-row bay: {len(tl)} closed tiles in {B["tiles"]} slots at the plan pitch 21.6 um, 4.32-um channels, '
                                 f'{len(lanes)} lanes of 8 b, {sum(8 * l["stages"] for l in lanes)} stage bits; wires + hard children only): measures the real congestion / DRC / timing of abutted relay and pad tiles '
                                 'with their closed pins before the band and region clusters are cut. Bench = every lane against its planned me-enabled stage count, every clock; mutants: one lane a tile short, two lanes swapped.',
                         hold_merge='physical probe of one lane bay (congestion pilot): the die sees the band cluster, never this block',
                         extra_paths=[P, 'rtl/hdc', 'results/arch/qwen_tp8_1012/vm_bay_' + tag + '.json'],
                         benches=[bench('bay_ok', '-GSEED=1', 'pass'), bench('bay_ok_s2', '-GSEED=2', 'pass'), bench('bay_mut1', '-GMUT=1', 'fail'), bench('bay_mut2', '-GMUT=2', 'fail')]))
    (ROOT / f'physical/ref_tile/qfd_vm_bay_{tag}.spec.json').write_text(json.dumps(spec, indent=1) + '\n')
    rec = dict(schema='opentallas.qwen-tp8.vm-bay.v1', bay=a.bay, top=top, bay_um=[B['x'], B['y'], B['w'], B['h']], slots=B['tiles'], tiles=[dict(slot=t['slot'], kind=t['kind'], kit=t['kit'], lanes=len(t['lanes'])) for t in tl],
               outline_um=[W_, H_], tile_origin_um=[x0, y0], frame_um=fr, ports=dict(inputs={f'd_{f}': 8 * nin[f] for f in 'wesn' if nin[f]}, outputs={f'q_{f}': 8 * nout[f] for f in 'wesn' if nout[f]}),
               lanes=len(lanes), stage_bits=sum(8 * l['stages'] for l in lanes), signal_pins=8 * (sum(nin.values()) + sum(nout.values())),
               loopbacks=sum(1 for l in lanes for j in range(1, len(l['tiles'])) if l['tiles'][j]['slot'] <= l['tiles'][j - 1]['slot']), lane_table=lanes)
    (ROOT / f'results/arch/qwen_tp8_1012/vm_bay_{tag}.json').write_text(json.dumps(rec, separators=(',', ':')) + '\n')
    print(json.dumps({k: v for k, v in rec.items() if k != 'lane_table'}))


if __name__ == '__main__':
    main()
