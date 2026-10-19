#!/usr/bin/env python3
"""Real RTL for the die-placed relay masters of a Qwen split compute die netlist (compute-die lead r3, 2026-10-14;
owner no-stub rule 08:05: every die instance binds to real RTL under its die name).

The die generator (qwen_rom_fulldie_b3r2._relays) names one relay master per (width, faces, frame):
  qfd_rly_<W>_<FiFo>_<w>x<h>    ports a [W] in, b [W] out, ck          one register stage (data only)
  qfd_rlyp_<W>_<FiFo>_<w>x<h>   ports a_d [W] in, b_d [W] out,         one register stage forward AND one register
                                a_r out, b_r in, ck                    stage on the returning ready (b_r -> a_r)
  qfd_rlyf_<W>_...              link-clock relays (fck_a / fck_b ...)  emitted when present (forwarded clock)
  qfd_rst_rep*                  reset-tree repeaters                   one register stage of the reset level
  qfd_clkrx                     pll_fwd in, one output per clock root  the die clock receiver (roots of this build)
  Q-DIE11-RLY 10-18 (OT_SPLIT_FWD_LANES=1, LANDING-CONTRACT): forwarded-clock HALF-CYCLE lanes, real RTL in
  rtl/qwen_split/qfd_fwd_lane.sv (ot_qfd_lane_st / ot_qfd_land); the wrappers below carry the die names:
  qfd_rlyh0_<W>_<FiFo>_<w>x<h>  ck en a b eb ck_o                       hop-0 station (inverting ICG on the source root)
  qfd_rlyh_<W>_...              ckf ea a b eb ck_o                      half-cycle station (ck_o = ~ckf)
  qfd_landh_<W>_...             ckf ea a ck rs k0 k1 k2 tie_hi tie_lo   landing (ring D 4 on ckf, read on the block
                                b fault                                 root ck at (rc - K) mod 8; K from own tie cells)
  qfd_landh0_<W>_...            ck_s en a ck rs k0..k2 tie_hi tie_lo    n = 1 lane: landing with the hop-0 gate
                                b fault

Protocol contract the relays implement (recorded, not hidden): every relay stage adds exactly one clock edge to the
data path and, for a ready pair, one edge to the ready path, so a hop of S relay stages has a ready round trip of 2 S
edges: the receiving end must absorb 2 S words after it drops ready (skid >= 2 S) or the pair must carry credits;
the die build reports S per bus (relay_run.json stage_of).  Data relays carry no reset: their content after reset is
flushed by the producer (held in reset >= the longest relay chain) -- the reset tree's release order guarantees it.
The module bodies are behaviour (always blocks), not shells: tools/die_port_bind.py accepts them as real RTL.

    python3 tools/qwen_split/gen_relay_rtl.py DIE_V OUT_SV      (prints a JSON summary)
"""
import json, re, sys
from pathlib import Path

INST = re.compile(r'^\s*(qfd_rly[pf]?_\w+|qfd_rlyh0?_\w+|qfd_rlyr[0l]?_\w+|qfd_landh0?_\w+|qfd_rst_rep\w*|qfd_clkrx)\s+(\w+)\s*\((.*)\);\s*$')
# Q-DIE11-RLY: the full port set of each forwarded-lane family (an open output, e.g. fault, is still a real port)
FWD = {'qfd_rlyh0_': ('ck', 'en', 'a', 'b', 'eb', 'ck_o'), 'qfd_rlyh_': ('ckf', 'ea', 'a', 'b', 'eb', 'ck_o'),
       'qfd_landh_': ('ckf', 'ea', 'a', 'ck', 'rs', 'k0', 'k1', 'k2', 'tie_hi', 'tie_lo', 'b', 'fault'),
       'qfd_landh0_': ('ck_s', 'en', 'a', 'ck', 'rs', 'k0', 'k1', 'k2', 'tie_hi', 'tie_lo', 'b', 'fault'),
       # LANDFIX-SQ 10-18 (OT_SPLIT_FWD_LANES_RST): forwarded RESET lanes (ot_qfd_rlane_st; the landing = one register on
       # the receiving block's root, no ring: the ring's read epoch would be the very reset the lane carries)
       'qfd_rlyr0_': ('ck', 'a', 'b', 'ck_o'), 'qfd_rlyr_': ('ckf', 'a', 'b', 'ck_o'), 'qfd_rlyrl_': ('ck', 'a', 'b')}
FWD_OUT = ('b', 'eb', 'ck_o', 'tie_hi', 'tie_lo', 'fault')


def fwd_family(mn):
    return next((f for f in sorted(FWD, key=len, reverse=True) if mn.startswith(f)), None)
CONN = re.compile(r'\.(\w+)\(([^()]*)\)')
WIRE = re.compile(r'^\s*wire\s*(?:\[(\d+):(\d+)\])?\s*(\w+)\s*;')


def width_of(expr, wires):
    expr = expr.strip()
    m = re.fullmatch(r"(\d+)'[dbh]\w+", expr)
    if m:
        return int(m.group(1))
    m = re.fullmatch(r'(\w+)\s*\[(\d+)(?::(\d+))?\]', expr)
    if m:
        return 1 if m.group(3) is None else abs(int(m.group(2)) - int(m.group(3))) + 1
    return wires.get(expr, 1)


def main(die_v, out_sv):
    wires, masters = {}, {}
    for line in open(die_v):
        w = WIRE.match(line)
        if w:
            wires[w.group(3)] = (abs(int(w.group(1)) - int(w.group(2))) + 1) if w.group(1) else 1
            continue
        m = INST.match(line)
        if not m:
            continue
        mn, conns = m.group(1), dict(CONN.findall(m.group(3)))
        ports = {p: width_of(e, wires) for p, e in conns.items()}
        if mn in ('qfd_rst_rep', 'qfd_rst_rep_p8'):
            # reset-tree repeater (ot_qwen_rst_rep): an instance may leave its second output q1 open, so the
            # master's port set is the union over its instances
            ports = {**masters.get(mn, {}), **ports}
        elif fwd_family(mn):
            # an instance may leave an output open (fault): the master's port set is the union over its instances
            ports = {**masters.get(mn, {}), **ports}
        elif mn in masters and masters[mn] != ports:
            raise SystemExit(f'{mn}: instances disagree on ports {masters[mn]} vs {ports}')
        masters[mn] = ports
    L = ['`timescale 1ns/1ps',
         f'// GENERATED by tools/qwen_split/gen_relay_rtl.py from {Path(die_v).name}: die relay masters as real RTL',
         '// (one register stage per relay; ready pairs register the returning ready too). Do not edit.']
    kinds = {}
    for mn, ports in sorted(masters.items()):
        if mn.startswith('qfd_rlyp_'):
            need = {'a_d', 'b_d', 'a_r', 'b_r', 'ck'}
            if set(ports) != need or ports['a_d'] != ports['b_d']:
                raise SystemExit(f'{mn}: unexpected ready-pair ports {ports}')
            W = ports['a_d']
            L += [f'module {mn} (input wire ck, input wire [{W - 1}:0] a_d, output reg [{W - 1}:0] b_d,',
                  '    output reg a_r, input wire b_r);',
                  '    always @(posedge ck) begin b_d <= a_d; a_r <= b_r; end',
                  'endmodule']
            kinds['ready_pair'] = kinds.get('ready_pair', 0) + 1
        elif fwd_family(mn):
            fam = fwd_family(mn)
            allp = FWD[fam]
            if set(ports) - set(allp) or not {'a', 'b'} <= set(ports) or ports['a'] != ports['b'] or \
                    any(w != 1 for p, w in ports.items() if p not in ('a', 'b')):
                raise SystemExit(f'{mn}: unexpected forwarded-lane ports {ports}')
            W = ports['a']
            decl = ', '.join(f'{"output" if p in FWD_OUT else "input"} wire {f"[{W - 1}:0] " if p in ("a", "b") else ""}{p}'
                             for p in allp)
            L += [f'module {mn} ({decl});']
            if fam in ('qfd_rlyr0_', 'qfd_rlyr_'):
                L += [f'    ot_qfd_rlane_st #(.W({W})) u_st (.cap({"ck" if fam == "qfd_rlyr0_" else "ckf"}), .a(a), .b(b), .ck_o(ck_o));']
                kinds['fwd_rst_station'] = kinds.get('fwd_rst_station', 0) + 1
            elif fam == 'qfd_rlyrl_':
                L += [f'    ot_qfd_rlane_land #(.W({W})) u_land (.ck(ck), .a(a), .b(b));']
                kinds['fwd_rst_landing'] = kinds.get('fwd_rst_landing', 0) + 1
            elif fam in ('qfd_rlyh0_', 'qfd_rlyh_'):
                ck_, en_ = ('ck', 'en') if fam == 'qfd_rlyh0_' else ('ckf', 'ea')
                L += [f'    ot_qfd_lane_st #(.W({W}), .FIRST({1 if fam == "qfd_rlyh0_" else 0})) u_st (.ck({ck_}), .en({en_}), '
                      '.a(a), .b(b), .eb(eb), .ck_o(ck_o));']
                kinds['fwd_station_hop0' if fam == 'qfd_rlyh0_' else 'fwd_station'] = \
                    kinds.get('fwd_station_hop0' if fam == 'qfd_rlyh0_' else 'fwd_station', 0) + 1
            else:
                first = fam == 'qfd_landh0_'
                L += ['    (* keep = "true" *) wire tie_hi_w = 1\'b1;', '    (* keep = "true" *) wire tie_lo_w = 1\'b0;',
                      '    assign tie_hi = tie_hi_w;', '    assign tie_lo = tie_lo_w;',
                      f'    ot_qfd_land #(.W({W}), .D(4), .FIRST({int(first)})) u_land (.ckf({"ck_s" if first else "ckf"}), '
                      f'.ea({"en" if first else "ea"}), .i(a), .ck(ck), .rs(rs), .k({{k2, k1, k0}}), .o(b), .fault(fault));']
                kinds['fwd_landing'] = kinds.get('fwd_landing', 0) + 1
            L += ['endmodule']
        elif mn.startswith('qfd_rly_'):
            if set(ports) != {'a', 'b', 'ck'} or ports['a'] != ports['b']:
                raise SystemExit(f'{mn}: unexpected relay ports {ports}')
            W = ports['a']
            L += [f'module {mn} (input wire ck, input wire [{W - 1}:0] a, output reg [{W - 1}:0] b);',
                  '    always @(posedge ck) b <= a;',
                  'endmodule']
            kinds['data'] = kinds.get('data', 0) + 1
        elif mn in ('qfd_rst_rep', 'qfd_rst_rep_p8'):
            # Q-BIND 10-17: the reset-tree repeaters of qwen_rom_fulldie_b3r2 (RST_REP / RST_PAD) are the real
            # ot_qwen_rst_rep (rtl/qwen_sys/reset_tree_20261013) at PAD 0 (2 cycles) / PAD 8 (10 cycles)
            if set(ports) - {'clk', 'd', 'q0', 'q1'} or not {'clk', 'd', 'q0'} <= set(ports) or any(w != 1 for w in ports.values()):
                raise SystemExit(f'{mn}: unexpected reset repeater ports {ports}')
            pad = 8 if mn.endswith('_p8') else 0
            L += [f'module {mn} (input wire clk, input wire d, output wire q0, output wire q1);',
                  f'    ot_qwen_rst_rep #(.PAD({pad})) u_rep (.clk(clk), .d(d), .q0(q0), .q1(q1));',
                  'endmodule']
            kinds['reset_repeater'] = kinds.get('reset_repeater', 0) + 1
        elif mn.startswith('qfd_rst_rep'):
            ins = [p for p in ports if p not in ('ck',)]
            if 'ck' not in ports or len(ins) != 2:
                raise SystemExit(f'{mn}: unexpected reset repeater ports {ports}')
            i_, o_ = sorted(ins, key=lambda p: (not p.startswith(('a', 'i', 'rsi', 'ri')), p))
            L += [f'module {mn} (input wire ck, input wire {i_}, output reg {o_});',
                  f'    always @(posedge ck or negedge {i_}) if (!{i_}) {o_} <= 1\'b0; else {o_} <= 1\'b1;',
                  'endmodule']
            kinds['reset_repeater'] = kinds.get('reset_repeater', 0) + 1
        elif mn == 'qfd_clkrx':
            # the die clock receiver: the forwarded clock (qfd_ckbump pll_ck -> pll_fwd) drives one root per clock region
            # of this build (pll_root, pll_d2d, pll_r<k>); each root is a clock-tree root that CTS builds from here
            if 'pll_fwd' not in ports or any(w != 1 for w in ports.values()):
                raise SystemExit(f'{mn}: unexpected clock receiver ports {ports}')
            outs = sorted(p for p in ports if p != 'pll_fwd')
            L += [f'module {mn} (input wire pll_fwd, ' + ', '.join(f'output wire {p}' for p in outs) + ');']
            L += [f'    assign {p} = pll_fwd;' for p in outs]
            L += ['endmodule']
            kinds['clock_receiver_roots'] = len(outs)
        else:
            raise SystemExit(f'{mn}: relay family not handled yet (ports {sorted(ports)}): extend gen_relay_rtl.py')
    Path(out_sv).write_text('\n'.join(L) + '\n')
    return dict(die_v=str(die_v), out=str(out_sv), masters=len(masters), kinds=kinds)


if __name__ == '__main__':
    print(json.dumps(main(sys.argv[1], sys.argv[2])))
