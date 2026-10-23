#!/usr/bin/env python3
"""REACH-M89 (10-22): per-cycle relay reach of a die wire on M8/M9 with repeaters, ASAP7 TT, T 833.333.

One OpenSTA design per relay master: for every (layer, buffer, spacing, L) a self-pair hop
  launch relay ETM (worst output bit) -> via stack down to M1 -> 5 um M4 stub -> repeater #1 (adjacent to the relay)
  -> [via stack M1->Mx, d um of Mx, via stack Mx->M1, repeater]* -> last <= d um of Mx -> via stack Mx->relay pin layer
  -> capture relay ETM (worst setup bit).
Ideal clock at both ck pins (self pair: insertion R cancels, as pair_check o = O - R, s = S + R), uncertainty
U 60 + SKEW 90 = 150 ps (the die_reach_1016 formula).  Wires are distributed RC ladders (<= 10 um sections) from
setRC.tcl per-layer values, vias lumped from set_layer_rc -via.  Slack per hop -> reach = largest L with slack >= 0.
Calibration rows: M4/M5 average, BUFx8 every 160 um (the source of the 0.76 ps/um constant).
"""
import json, re, sys, gzip
from pathlib import Path

# setRC.tcl (kohm/um, fF/um); vias kohm
RC = {'M2': (2.97127e-02, 1.74942e-01), 'M3': (3.12870e-02, 1.55554e-01), 'M4': (1.80365e-02, 1.78475e-01),
      'M5': (1.89935e-02, 1.64264e-01), 'M6': (1.18796e-02, 1.87426e-01), 'M7': (1.25096e-02, 1.62979e-01),
      'M8': (8.44765e-03, 1.03962e-01), 'M9': (8.89556e-03, 9.28446e-02)}
RC['M45'] = tuple((a + b) / 2 for a, b in zip(RC['M4'], RC['M5']))
VIA = {1: 1.72e-02, 2: 1.72e-02, 3: 1.72e-02, 4: 1.18e-02, 5: 1.18e-02, 6: 8.20e-03, 7: 8.20e-03, 8: 6.30e-03, 9: 6.30e-03}


def lnum(l):
    return 4 if l == 'M45' else int(l[1:])


def stack(lo, hi):
    """R of the via stack between metal lo and metal hi (V_k joins M_k and M_k+1)"""
    a, b = sorted((lnum(lo), lnum(hi)))
    return sum(VIA[k] for k in range(a, b))


RELAYS = {   # die -> list of (cell, view dir rel to repo, out bus, in bus, pin layer)
    's81': [('dsfd_dvrlyh_276_NS', 'physical/ref_tile/s81dv_rlyh_276_ns/views/dsfd_dvrlyh_276_NS', 'o', 'i', 'M3'),
            ('dsfd_rly_266_SN', 'physical/ref_tile/s81_rly_266_sn/views/dsfd_rly_266_SN', 'o', 'i', 'M5')],
    'qwen_compute': [('qfd_cst_n', 'physical/ref_tile/qfd_cst_n/views/qfd_cst_n', 'a_d', 'b_d', 'M5')],
    'qwen_kv': [('qkd_rlys_296', 'physical/ref_tile/qkd_rlys_296/views/qkd_rlys_296', 'b', 'a', 'M4')],
    'hbm': [('hbfd_rly_48_NS', 'physical/ref_tile/hbfd_rly_48_ns/views/hbfd_rly_48_NS', 'o', 'i', 'M5'),
            ('hbfd_rly_624_NS', 'physical/ref_tile/hbfd_rly_624_ns/views/hbfd_rly_624_NS', 'o', 'i', 'M5')],
}
BUFS = ['BUFx8_ASAP7_75t_R', 'BUFx12f_ASAP7_75t_R', 'BUFx16f_ASAP7_75t_R']
SPACINGS = [100, 150, 200, 250, 300, 450, 600, 800, 1000]
LAYERS = ['M8', 'M9']
import os
LGRID = [int(x) for x in os.environ['OT_LGRID'].split(',')] if os.environ.get('OT_LGRID') else list(range(200, 3001, 50))
CALIB = ('M45', 'BUFx8_ASAP7_75t_R', 160)


def worst_bits(lib, obus, ibus):
    s = Path(lib).read_text()
    best_o = best_i = None
    for m in re.finditer(r'pin\s*\("?(\w+)\[(\d+)\]"?\)\s*\{(.*?)\n    \}', s, re.S):
        bus, bit, body = m.group(1), int(m.group(2)), m.group(3)
        if bus == obus:
            v = re.search(r'cell_rise\(template_1\)\s*\{.*?values\("([^"]+)"\)', body, re.S)
            if v:
                x = float(v.group(1).split(',')[3])   # 11.52 fF point
                if best_o is None or x > best_o[1]:
                    best_o = (bit, x)
        elif bus == ibus:
            v = re.search(r'setup_rising;\s*rise_constraint\(scalar\)\s*\{\s*values\("([^"]+)"\)\s*;\s*\}\s*fall_constraint\(scalar\)\s*\{\s*values\("([^"]+)"\)', body, re.S)
            if v:
                x = max(float(v.group(1)), float(v.group(2)))
                if best_i is None or x > best_i[1]:
                    best_i = (bit, x)
    width_o = len(re.findall(r'pin\s*\("?%s\[\d+\]' % obus, s))
    width_i = len(re.findall(r'pin\s*\("?%s\[\d+\]' % ibus, s))
    return best_o, best_i, width_o, width_i


class Spef:
    def __init__(s):
        s.nets = []

    def net(s, name, drv, load, segs):
        """segs: list of ('R', r) lumped or ('W', layer, um) distributed; drv/load 'inst:pin' strings"""
        caps, ress = [], []
        node, k, tot = drv, 0, 0.0
        for sg in segs:
            if sg[0] == 'R':
                k += 1; nn = f'{name}:{k}'; ress.append((node, nn, sg[1])); node = nn
            else:
                r, c = RC[sg[1]]; um = sg[2]
                n = max(1, int(round(um / 10.0)))
                dx = um / n
                for _ in range(n):
                    k += 1; nn = f'{name}:{k}'
                    ress.append((node, nn, r * dx)); caps.append((nn, c * dx)); tot += c * dx; node = nn
        ress.append((node, load, 1e-6))
        s.nets.append((name, drv, load, caps, ress, tot))

    def text(s):
        o = ['*SPEF "IEEE 1481-1998"', '*DESIGN "top"', '*DATE "2026-10-22"', '*VENDOR "OT"', '*PROGRAM "die_reach_m89"',
             '*VERSION "1"', '*DESIGN_FLOW "NETLIST_TYPE_VERILOG"', '*DIVIDER /', '*DELIMITER :', '*BUS_DELIMITER [ ]',
             '*T_UNIT 1 PS', '*C_UNIT 1 FF', '*R_UNIT 1 KOHM', '*L_UNIT 1 HENRY', '']
        for name, drv, load, caps, ress, tot in s.nets:
            o.append(f'*D_NET {name} {tot:.5f}')
            o += ['*CONN', f'*I {drv} O', f'*I {load} I', '*CAP']
            o += [f'{i + 1} {n} {c:.6f}' for i, (n, c) in enumerate(caps)]
            o.append('*RES')
            o += [f'{i + 1} {a} {b} {r:.7f}' for i, (a, b, r) in enumerate(ress)]
            o += ['*END', '']
        return '\n'.join(o)


def esc(n):
    return n.replace('[', '\\[').replace(']', '\\]')


def build(root, die, relay, out):
    cell, vdir, ob, ib, play = relay
    lib = Path(root) / vdir / f'{cell}_tt.lib'
    bo, bi, wo, wi = worst_bits(lib, ob, ib)
    configs = [(l, b, d) for l in LAYERS for b in BUFS for d in SPACINGS] + [CALIB]
    sp = Spef(); v = []; paths = []
    v.append('module top(clk);\ninput clk;')
    pid = 0
    for (lay, buf, d) in configs:
        for L in LGRID:
            if lay == 'M45' and L > 1200:
                continue
            p = f'p{pid}'; pid += 1
            nrep = 1 + int((L - 1e-9) // d)       # repeater #1 adjacent to the launch relay, then one every d um
            last = L - (nrep - 1) * d
            v.append(f'wire [{wo - 1}:0] {p}_lo; wire [{wi - 1}:0] {p}_ci;')
            v.append(f'{cell} {p}_L (.ck(clk), .{ob}({p}_lo));')
            v.append(f'{cell} {p}_C (.ck(clk), .{ib}({p}_ci));')
            # stub: relay pin layer -> M1 buffer input, 5 um M4
            src = f'{p}_lo[{bo[0]}]'
            v.append(f'wire {p}_n0; wire {p}_lo{bo[0]}x = {p}_lo[{bo[0]}];')
            # use the bus bit net directly
            sp.net(f'{p}_lo[{bo[0]}]', f'{p}_L:{ob}[{bo[0]}]', f'{p}_b0:A',
                   [('R', stack(play, 'M4')), ('W', 'M4', 5.0), ('R', stack('M1', 'M4'))])
            for k in range(nrep):
                nin = f'{p}_lo[{bo[0]}]' if k == 0 else f'{p}_n{k}'
                nout = f'{p}_n{k + 1}' if k < nrep - 1 else f'{p}_ci[{bi[0]}]'
                if k < nrep - 1:
                    v.append(f'wire {p}_n{k + 1};')
                v.append(f'{buf} {p}_b{k} (.A({nin}), .Y({nout}));')
                if k < nrep - 1:
                    sp.net(nout, f'{p}_b{k}:Y', f'{p}_b{k + 1}:A',
                           [('R', stack('M1', lay)), ('W', lay, float(d)), ('R', stack('M1', lay))])
                else:
                    sp.net(nout, f'{p}_b{k}:Y', f'{p}_C:{ib}[{bi[0]}]',
                           [('R', stack('M1', lay)), ('W', lay, float(last)), ('R', stack(play, lay))])
            paths.append(dict(id=p, layer=lay, buf=buf, d=d, L=L, nrep=nrep, ep=f'{p}_C/{ib}[{bi[0]}]',
                              sp=f'{p}_L/ck', mid=[f'{p}_b{k}/A' for k in range(nrep)]))
    v = [x for x in v if 'x = ' not in x]
    v.append('endmodule')
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    (out / 'top.v').write_text('\n'.join(v) + '\n')
    (out / 'top.spef').write_text(sp.text())
    (out / 'paths.json').write_text(json.dumps(dict(die=die, cell=cell, lib=str(lib), pin_layer=play,
                                                    worst_out_bit=bo, worst_in_bit=bi, paths=paths)))
    # tcl
    t = [f'read_liberty asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz',
         f'read_liberty {cell}_tt.lib', 'read_verilog top.v', 'link_design top', 'read_spef top.spef',
         'create_clock -name clk -period 833.333 [get_ports clk]', 'set_clock_uncertainty -setup 150 [all_clocks]',
         'set_input_transition 20 [get_ports clk]',
         'set fo [open res_dmp.txt w]',
         'set fi [open pins.txt r]', 'while {[gets $fi line] >= 0} {',
         '  set pin [get_pins $line]',
         '  puts $fo "$line [get_property $pin slack_max] [get_property $pin arrival_max_rise] [get_property $pin arrival_max_fall] [get_property $pin slew_max]"', '}',
         'close $fi',
         'close $fo',
         'set_delay_calculator arnoldi',
         'set fo [open res.txt w]',
         'set fi [open pins.txt r]', 'while {[gets $fi line] >= 0} {',
         '  set pin [get_pins $line]',
         '  puts $fo "$line [get_property $pin slack_max] [get_property $pin arrival_max_rise] [get_property $pin arrival_max_fall] [get_property $pin slew_max]"', '}',
         'close $fi',
         'close $fo', 'report_checks -path_delay max -fields {slew cap} -digits 1 > worst.rpt', 'exit']
    (out / 'pins.txt').write_text('\n'.join(x for q in paths for x in [q['ep']] + q['mid']) + '\n')
    (out / 'sta.tcl').write_text('\n'.join(t) + '\n')
    import shutil
    shutil.copy(lib, out / f'{cell}_tt.lib')
    shutil.copy(os.environ.get('OT_INVBUF_LIB', '/home/ubuntu/.local/opentallas-pdk-asap7-platform/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz'), out)
    return len(paths)


if __name__ == '__main__':
    root, outdir = sys.argv[1], Path(sys.argv[2])
    only = sys.argv[3:] or None
    for die, rl in RELAYS.items():
        for r in rl:
            if only and r[0] not in only:
                continue
            n = build(root, die, r, outdir / r[0])
            print(die, r[0], n, 'paths')
