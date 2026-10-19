#!/usr/bin/env python3
"""Qwen ROM die: interface-timing Liberty views of the die's placeholder elements, for die-level OpenSTA.

Every die element boundary is register-to-register (owner rule 2026-10-06: inputs captured in a flop at the pin,
outputs launched from a flop at the pin, no logic between pin and flop), so an element's interface timing is one
flop: setup/hold at every input pin against the element clock pin, clock->Q plus the output drive at every output
pin.  This writes those views; the values are ASSUMED single-flop constants (ASAP7 DFFHQNx1 class at SS 0.63 V /
FF 0.77 V, scaled up for an output driver), NOT characterised element ETMs: no Qwen element has an ETM yet.  The
die STA they feed is therefore a die-WIRE audit (routed top-level RC between registered pins), not block sign-off.

Directions per bit: die_top_lint's registered stubs (inout ports: the bits the stub assigns from a flop are outputs),
real shells (ot_qwen_stream4_cdc_pc) through the die's abstract port names (qfd_cdc: ho/hi on hclk, co/ci on clk).
Clock pins (ck, ckx, cks, cku, ckd, clk, hclk) are clock inputs; forwarded-clock (fck_*) and PLL (pll_*) pins carry
no arcs (the STA creates its clocks on the PLL pins).

    python3 tools/qwen_die_element_lib.py --stubs LINTDIR/qwen_rom_lint_top_stubs.sv --lef CASE/elements.lef --out DIR
"""
import argparse
import re
from collections import defaultdict
from pathlib import Path



class _Clocks(tuple):
    """the clock pin names; qwen-split kvsys v1.1 adds the per-child clock entries of a wires-only parent frame
    (ck_<letter>[<index>]: ck_a / ck_b / ck_c of the control tile, ck_f / ck_k / ck_s / ck_t0..15 / ck_l0..15 of the
    native head), each its own clock input"""
    # kvsys v1.4 (2026-10-15): the HOST root core's named clock inputs (qkd_host_root_pt) and the HOST slice entries
    HOST_V14 = frozenset(('ck_station', 'ck_static', 'ck_boot', 'ck_boot_test', 'ck_pad', 'ck_phy_rx_w', 'ck_phy_rx_r',
                          'ck_phy_tx_w', 'ck_phy_tx_r', 'ck_peer', 'ck_program_rx', 'ck_program_loader', 'ck_host', 'ck_csr',
                          'ck_rst', 'ck_ctl', 'ck_prompt', 'ck_rx', 'ck_tx', 'ck_axi', 'ck_ctrl', 'ck_hc', 'ck_qm_queue',
                          'ck_qm_ing_w', 'ck_qm_ing_r', 'ck_qm_credit', 'ck_qm_done_w', 'ck_qm_done_r', 'ck_qm_core',
                          'ck_qm_host', 'ck_qm_ingest', 'ck_qm_out', 'ck_map', 'ck_sum', 'ck_order', 'ck_dispatch',
                          'ck_retire', 'ck_bootbarrier', 'ck_fence_core', 'ck_fence_host', 'ck_guard', 'ck_native',
                          'ck_records', 'ck_root_mux', 'ck_coordinator_codec', 'ck_coordinator_lifecycle',
                          'ck_coordinator_post') + tuple(f'ck_phy{i}' for i in range(8)) + ('ck_qm_bank0', 'ck_qm_bank1'))

    # KV-CASE2 10-18: the static KV die's composite tiles (qkd_kvs_*, kv_static_die) name each child's clock entry
    # <child>__<clock> (pc__ck, bcdc0__hck, pc__pll_hbm ...); the HBM-domain child clocks (kv_static_die HBM_CK)
    STATIC_SUB = frozenset(('hck', 'pll_hbm', 'pll_hbm_port', 'pll_hbm_ecc', 'pll_hbm_cdc', 'pll_hbm_obs', 'cal_hck',
                            'front_hck', 'return_hck', 'return_ck'))

    def __contains__(self, p):
        if str(p) == 'hck':                 # OT_KV_TILE_KITS: a kit tile's one HBM-domain clock port
            return True
        if '__' in str(p):
            b_ = str(p).rsplit('__', 1)[1]
            if b_ and (b_ in self.STATIC_SUB or self.__contains__(b_)):
                return True
        return tuple.__contains__(self, p) or str(p) in self.HOST_V14 or \
            bool(re.fullmatch(r'(ck|hk)_[a-z]\d{0,2}', str(p)))   # hk_*: v1.2 HBM-clock entries


# KV-WIRE2 10-18: + 'hck' = the HBM-domain clock port of the OT_KV_TILE_KITS kit tiles (kv_static_die kit_clocks)
CLOCKS = _Clocks(('ck', 'ckx', 'cks', 'cku', 'ckd', 'clk', 'hclk', 'hck') + tuple(f'ck{i}' for i in range(9)) + ('ck_pin','ck_head','ck_tree','ck_xpf','ck_me_sched','ck_sched'))   # + per-child clock entries (qwen split compute C5: xcol ck0..8, tt_up4 ck_pin / ck_l0..3)
CORNERS = dict(  # setup, hold, clk->q base, ps/fF output slope, output transition base, ps/fF, input cap fF (ASSUMED)
    ss=dict(setup=30.0, hold=5.0, cq=75.0, k=0.9, tr=25.0, tk=1.6, cin=0.7, volt=0.63, temp=100),
    ff=dict(setup=12.0, hold=12.0, cq=32.0, k=0.35, tr=10.0, tk=0.7, cin=0.6, volt=0.77, temp=0))
# TT (owner option B setup corner): the SS constants, PESSIMISTIC and disclosed (no characterised TT placeholder exists)
CORNERS['tt'] = dict(CORNERS['ss'], volt=0.7, temp=25)
# qwen-1010/b 2026-10-10 (KV die die_kv14 FF hold -5.74 ps on every abutted element hop): the pin flop of a routed
# element reaches its face pin through the port buffer every ORFS route inserts (buffer_ports: an output BUF after the
# launching flop, an input BUF before the capturing flop) -- the single-flop view had neither, so two abutted views
# met hold with a bare clk->q against a bare hold time.  The views now carry that buffer stage (ASAP7 BUFx2 class:
# SS 25 ps, FF 12 ps): + on clk->out, + on setup, - on hold.  The closed ETMs carry far more (qkd_ectl_b FF: clk->out
# 477 ps vs hold 257 ps, insertion included).
PORT_BUF = dict(ss=25.0, tt=25.0, ff=12.0)
LOADS = (0.5, 5.0, 20.0, 80.0, 300.0, 1200.0)      # fF
SLEWS = (5.0, 20.0, 80.0, 300.0)                   # ps


IDX = set()     # (master, port) whose LEF pins carry an index ([0] even at width 1): Liberty bus


def lef_pins(path):
    """master -> {port: nbits} from the k=1 abstract LEF (pins 'p[i]' or 'p')."""
    out, cur, pin = defaultdict(dict), None, None
    for ln in Path(path).read_text().splitlines():
        t = ln.split()
        if not t:
            continue
        if t[0] == 'MACRO':
            cur = t[1]
        elif t[0] == 'PIN' and cur:
            m = re.match(r'([^\[]+)(?:\[(\d+)\])?$', t[1])
            pin = (m.group(1), m.group(2))
            p, i = pin
            out[cur][p] = max(out[cur].get(p, 0), (int(i) + 1) if i is not None else 1)
            if i is not None:
                IDX.add((cur, p))
        elif t[0] == 'USE' and pin and t[1].rstrip(';') in ('POWER', 'GROUND'):
            out[cur].pop(pin[0], None)          # supply pins: no Liberty signal pin
    return out


def stub_dirs(path):
    """module -> {port: (dir, width, {out bit set}, clock)} from die_top_lint's stubs."""
    mods, cur = {}, None
    for ln in Path(path).read_text().splitlines():
        m = re.match(r'\s*module (\S+)', ln)
        if m:
            cur = mods.setdefault(m.group(1), {})
            continue
        m = re.match(r'\s*(input|output|inout) wire \[(\d+):0\] (\w+)', ln)
        if m and cur is not None:
            cur[m.group(3)] = [m.group(1), int(m.group(2)) + 1, set()]
            continue
        m = re.search(r'assign (\w+) ?\[(\d+):(\d+)\] = r_', ln)   # main 10-14: die_top_lint writes 'p [h:l]'
        if m and cur is not None and m.group(1) in cur:
            cur[m.group(1)][2].update(range(int(m.group(3)), int(m.group(2)) + 1))
    return mods


def bit_dirs(master, port, n, stubs):
    if master == 'qfd_cdc':
        return ['output' if port in ('ho', 'co') else 'input'] * n, ('hclk' if port in ('ho', 'hi') else 'clk')
    s = stubs.get(master, {}).get(port)
    if s is None:
        return ['input'] * n, None
    d, w, outs = s
    if d == 'inout':
        return ['output' if i in outs else 'input' for i in range(n)], None
    return [d] * n, None


def table(vals_fn, idx1, idx2=None):
    if idx2 is None:
        return ('index_1 ("%s"); values ("%s");' % (', '.join(f'{x:g}' for x in idx1),
                                                     ', '.join(f'{vals_fn(x):.2f}' for x in idx1)))
    rows = ', '.join('"%s"' % ', '.join(f'{vals_fn(a, b):.2f}' for b in idx2) for a in idx1)
    return ('index_1 ("%s"); index_2 ("%s"); values (%s);' % (', '.join(f'{x:g}' for x in idx1),
                                                              ', '.join(f'{x:g}' for x in idx2), rows))


# Q-DIE11-RLY 10-18 (OT_SPLIT_FWD_LANES, rtl/qwen_split/qfd_fwd_lane.sv): forwarded-clock half-cycle lane frames.  The
# die STA propagates each lane's clock from the hop-0 station's root pin through the ck -> ck_o arcs (hop 0: capture on
# the RISING root edge, ck_o = ~(ck gated); station: capture on ckf rising, ck_o = ~ckf), so every station hop is timed
# as the half-cycle hop it is, on routed RC.  The landing is modelled as in the S81-LAND pilot (dv_land_pilot.py): the
# lane's data / epoch pins are checked against the RECEIVING root ck, with case/landing.sdc's MCP -setup E -hold D-1.
FWD_RE = re.compile(r'^qfd_(rlyh0|rlyh|landh0|landh|rlyr0|rlyrl|rlyr)_')   # LANDFIX-SQ: + forwarded reset lanes
FWD_NOT_ROOT = ('ck_o', 'ckf')       # forwarded clock pins: no create_clock (die_sta_libs), propagated through the arcs
FWD_CK_FWD = dict(ss=40.0, tt=40.0, ff=18.0)     # ASSUMED ck -> ck_o cell delay (one INVx2 / ICG + INV class)


def fwd_cell(master, ports, c, pb, cq, trn):
    kind = FWD_RE.match(master).group(1)
    clk = {'rlyh0': 'ck', 'rlyh': 'ckf', 'landh': 'ck', 'landh0': 'ck', 'rlyr0': 'ck', 'rlyr': 'ckf', 'rlyrl': 'ck'}[kind]
    edge = 'rising'                     # Q-DIE11 10-18: hop 0 captures on the rising root edge too
    clocks = {'rlyh0': ('ck',), 'rlyh': ('ckf',), 'landh': ('ckf', 'ck'), 'landh0': ('ck_s', 'ck'),
              'rlyr0': ('ck',), 'rlyr': ('ckf',), 'rlyrl': ('ck',)}[kind]
    data_in = {'rlyh0': ('a', 'en'), 'rlyh': ('a', 'ea'), 'landh': ('a', 'ea', 'rs'), 'landh0': ('a', 'rs'),
               'rlyr0': ('a',), 'rlyr': ('a',), 'rlyrl': ('a',)}[kind]
    data_out = {'rlyh0': ('b', 'eb'), 'rlyh': ('b', 'eb'), 'landh': ('b', 'fault'), 'landh0': ('b', 'fault'),
                'rlyr0': ('b',), 'rlyr': ('b',), 'rlyrl': ('b',)}[kind]
    fd = FWD_CK_FWD.get(next(k for k, v in CORNERS.items() if v is c), 40.0)
    L = [f'  cell ({master}) {{ area : 0; dont_touch : true; dont_use : true;']
    pn = lambda q: q + '[0]' if (master, q) in IDX else q      # noqa: E731  (LEF pins indexed even at width 1)

    def cons(rel):
        out = []
        for tt, v in ((f'setup_{edge}', c['setup'] + pb), (f'hold_{edge}', c['hold'] - pb)):
            f = (lambda a, s_, v=v: v + 0.1 * s_)
            out.append(f'timing () {{ related_pin : "{pn(rel)}"; timing_type : {tt}; '
                       f'rise_constraint (cons2) {{ {table(f, SLEWS, SLEWS)} }} fall_constraint (cons2) {{ {table(f, SLEWS, SLEWS)} }} }}')
        return ' '.join(out)
    launch = (f'timing () {{ related_pin : "{pn(clk)}"; timing_type : {edge}_edge; '
              f'cell_rise (load1) {{ {table(cq, LOADS)} }} cell_fall (load1) {{ {table(cq, LOADS)} }} '
              f'rise_transition (load1) {{ {table(trn, LOADS)} }} fall_transition (load1) {{ {table(trn, LOADS)} }} }}')
    for p, n in sorted(ports.items()):
        bus = n > 1 or (master, p) in IDX
        if p in clocks:
            body = 'direction : input; clock : true; capacitance : 2.0;'
        elif p == 'ck_o':
            src = 'ck' if kind in ('rlyh0', 'rlyr0') else 'ckf'
            sense = 'negative_unate'    # every forward inverts (hop 0: ck_o = ~gated ck)
            dly = (lambda load, fd=fd: fd + c['k'] * load)
            body = (f'direction : output; max_capacitance : 5000; timing () {{ related_pin : "{pn(src)}"; timing_sense : {sense}; '
                    f'timing_type : combinational; cell_rise (load1) {{ {table(dly, LOADS)} }} cell_fall (load1) {{ {table(dly, LOADS)} }} '
                    f'rise_transition (load1) {{ {table(trn, LOADS)} }} fall_transition (load1) {{ {table(trn, LOADS)} }} }}')
        elif p in data_in:
            body = f'direction : input; capacitance : {c["cin"]}; ' + cons(clk)
        elif kind == 'landh0' and p == 'en':
            # QK-LANDEN 10-19: en is registered on ck_s at the face (one flop before the hop-0 gate): a ck_s input
            body = f'direction : input; capacitance : {c["cin"]}; ' + cons('ck_s')
        elif p in data_out:
            body = 'direction : output; max_capacitance : 5000; ' + launch
        elif p in ('tie_hi', 'tie_lo'):
            body = 'direction : output; max_capacitance : 5000;'
        else:                       # k0..k2 straps: no arcs
            body = f'direction : input; capacitance : {c["cin"]};'
        if bus:
            L.append(f'    bus ({p}) {{ bus_type : b{n}; {body} }}')
        else:
            L.append(f'    pin ({p}) {{ {body} }}')
    L.append('  }')
    return L


def write_lib(corner, lef, stubs, path, clock_ports=None, related_pins=None):
    c = CORNERS[corner]
    L = [f'library (qfd_elements_{corner}) {{',
         '  delay_model : table_lookup; time_unit : "1ps"; capacitive_load_unit (1, ff); voltage_unit : "1V";',
         '  current_unit : "1mA"; pulling_resistance_unit : "1kohm"; leakage_power_unit : "1nW";',
         f'  nom_process : 1; nom_voltage : {c["volt"]}; nom_temperature : {c["temp"]};',
         '  slew_lower_threshold_pct_rise : 10; slew_upper_threshold_pct_rise : 90;',
         '  slew_lower_threshold_pct_fall : 10; slew_upper_threshold_pct_fall : 90;',
         '  input_threshold_pct_rise : 50; input_threshold_pct_fall : 50;',
         '  output_threshold_pct_rise : 50; output_threshold_pct_fall : 50;',
         '  lu_table_template (load1) { variable_1 : total_output_net_capacitance; index_1 ("1, 2"); }',
         '  lu_table_template (slew1) { variable_1 : related_pin_transition; index_1 ("1, 2"); }',
         '  lu_table_template (cons2) { variable_1 : related_pin_transition; variable_2 : constrained_pin_transition;'
         ' index_1 ("1, 2"); index_2 ("1, 2"); }']
    widths = sorted({n for m, ps in lef.items() for p, n in ps.items() if n > 1 or (m, p) in IDX})
    for w in widths:
        L.append(f'  type (b{w}) {{ base_type : array; data_type : bit; bit_width : {w}; bit_from : {w - 1};'
                 f' bit_to : 0; downto : true; }}')
    pb = PORT_BUF.get(corner, 0.0)
    cq = lambda load: c['cq'] + pb + c['k'] * load       # noqa: E731
    trn = lambda load: c['tr'] + c['tk'] * load          # noqa: E731
    for master, ports in sorted(lef.items()):
        if master == 'ot_hbm3e_phy':
            continue                                    # real PHY: its own characterised .lib
        if FWD_RE.match(master):
            L += fwd_cell(master, ports, c, pb, cq, trn)
            continue
        clocks = [p for p in ports if p in CLOCKS or p in (clock_ports or {}).get(master, ())]
        L.append(f'  cell ({master}) {{ area : 0; dont_touch : true; dont_use : true;')
        for p, n in sorted(ports.items()):
            dirs, rel = bit_dirs(master, p, n, stubs)
            if p in clocks:
                if (master, p) in IDX:
                    L.append(f'    bus ({p}) {{ bus_type : b{n}; direction : input; clock : true; capacitance : 2.0; }}')
                else:
                    L.append(f'    pin ({p}) {{ direction : input; clock : true; capacitance : 2.0; }}')
                continue
            rel = rel or ('ck' if 'ck' in clocks else (clocks[0] if clocks else None))
            # Q-DIE11-COLL 10-18: source-declared per-bit capture/launch clocks (clock contract related_pins), e.g.
            # the production collective's SerDes words on their face codec root and the UCIe words on fdi(_rx)_ck
            bit_rel = (related_pins or {}).get(master, {}).get(p)
            if bit_rel is not None:
                if len(bit_rel) != n:
                    raise ValueError(f'{master}.{p}: related_pins has {len(bit_rel)} bits, LEF has {n}')
                bit_rel = [r_ if '[' in r_ or (master, r_) not in IDX else r_ + '[0]' for r_ in bit_rel]
            if master in ('qkd_ctrl', 'qkd_ctrl_n') and 'hk_k' in clocks:
                # qwen-split kvsys v1.2: the HBM controller strip has two domains: its CDC / PHY words run on the HBM
                # clock (hk_*), the landing / stream-command words on the core clock (ck_*)
                rel = 'hk_k' if re.fullmatch(r'(c\d+[io]|po\d+|pi\d+|hrst)', p) else 'ck_k'
            if rel is not None and (master, rel) in IDX:
                rel = rel + '[0]'
            arcs = rel is not None and not p.startswith(('fck_', 'pll_'))

            def pin_body(d, rel=rel):
                if d == 'output':
                    b = ['direction : output; max_capacitance : 5000;']
                    if arcs:
                        b.append(f'timing () {{ related_pin : "{rel}"; timing_type : rising_edge; '
                                 f'cell_rise (load1) {{ {table(cq, LOADS)} }} cell_fall (load1) {{ {table(cq, LOADS)} }} '
                                 f'rise_transition (load1) {{ {table(trn, LOADS)} }} '
                                 f'fall_transition (load1) {{ {table(trn, LOADS)} }} }}')
                    return ' '.join(b)
                b = [f'direction : input; capacitance : {c["cin"]};']
                if arcs:
                    for tt, v in (('setup_rising', c['setup'] + pb), ('hold_rising', c['hold'] - pb)):
                        f = (lambda a, s_, v=v: v + 0.1 * s_)
                        b.append(f'timing () {{ related_pin : "{rel}"; timing_type : {tt}; '
                                 f'rise_constraint (cons2) {{ {table(f, SLEWS, SLEWS)} }} '
                                 f'fall_constraint (cons2) {{ {table(f, SLEWS, SLEWS)} }} }}')
                return ' '.join(b)
            if bit_rel is not None and arcs:
                if n == 1 and (master, p) not in IDX:
                    L.append(f'    pin ({p}) {{ {pin_body(dirs[0], bit_rel[0])} }}')
                    continue
                L.append(f'    bus ({p}) {{ bus_type : b{n}; direction : {"inout" if len(set(dirs)) > 1 else dirs[0]};')
                if len(set(bit_rel)) == 1:
                    L.append(f'      {pin_body(dirs[0], bit_rel[0]).replace("direction : " + dirs[0] + ";", "")}')
                else:
                    for i, d in enumerate(dirs):
                        L.append(f'      pin ({p}[{i}]) {{ {pin_body(d, bit_rel[i])} }}')
                L.append('    }')
                continue
            if n == 1 and (master, p) not in IDX:
                L.append(f'    pin ({p}) {{ {pin_body(dirs[0])} }}')
            else:
                mixed = len(set(dirs)) > 1
                L.append(f'    bus ({p}) {{ bus_type : b{n}; direction : {"inout" if mixed else dirs[0]};')
                if mixed:
                    for i, d in enumerate(dirs):
                        L.append(f'      pin ({p}[{i}]) {{ {pin_body(d)} }}')
                else:
                    L.append(f'      {pin_body(dirs[0]).replace("direction : " + dirs[0] + ";", "")}')
                L.append('    }')
        L.append('  }')
    L.append('}')
    Path(path).write_text('\n'.join(L) + '\n')


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--stubs', type=Path, required=True)
    ap.add_argument('--lef', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args(argv)
    a.out.mkdir(parents=True, exist_ok=True)
    lef, stubs = lef_pins(a.lef), stub_dirs(a.stubs)
    for corner in CORNERS:
        write_lib(corner, lef, stubs, a.out / f'qfd_elements_{corner}.lib')
    print(f'{len(lef)} masters -> {a.out}')


if __name__ == '__main__':
    main()
