#!/usr/bin/env python3
"""pinreg_credit_check.py (hbm-phys vm8 2026-10-10): per-port proof behind the io_min clk->Q hold credit of the VM8 halves.

Lead ruling (REVIEW_20261009.md, 2026-10-10): an input bit of a vcut8 half gets the 32.2 ps sender clk->Q hold credit ONLY if
  (a) its sender is a VM8 half output bit driven DIRECTLY by a flop Q (no logic / feed-through between Q and the pin; the flop
      clocked by a tap leaf ck<f><i> = the pin-anchored PINREG), and
  (b) on the receiving half the input bit feeds only flop D pins (the pin capture register).
Any other input bit (die-face inputs from non-VM views are not verifiable here, unconnected or logic-fed bits) gets no credit.

Method: yosys elaborates the 8 halves joined as in the bench (tb_vm_vcut8.sv vm_joined, `VCUT8), keep_hierarchy on every
half, flatten the rest, proc + opt_clean only (no logic optimisation), write_json.  Per half, per port bit: output bit ->
driver cell; input bit -> loads.  Then every vm_joined net bit joining half A output -> half B input is judged.
Writes:  --out-json  per-half per-port pass/fail counts + every failing bit (evidence)
         --sdc-dir   io_min_<master>.sdc per half: set_input_delay -min 32.2 on the credited bits only (FF session only)

    pinreg_credit_check.py --yosys <yosys bin or 'docker'> --out-json F --sdc-dir D        (run from the repo root)
"""
import argparse, json, re, subprocess, sys, tempfile
from collections import Counter, defaultdict
from pathlib import Path

V = 'physical/hbm_accel_die_views'
S = f'{V}/vm/vcut8'
T = f'{V}/vm/tiles'
SRAM = 'physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v'
HALVES = [f'hfd_vm_{q}_{h}' for q in ('sw', 'nw', 'se', 'ne') for h in ('w', 'e')]
CLKQ = 32.2
TAP = re.compile(r'^ck[wens][0-9]+$')
FF_TYPES = ('$dff', '$adff', '$sdff', '$dffe', '$adffe', '$sdffe', '$sdffce', '$aldff', '$dffsr')


def vm_joined_text():
    s = Path(f'{S}/tb_vm_vcut8.sv').read_text()
    m = re.search(r'^module vm_joined\b.*?^endmodule', s, re.S | re.M)
    return '`define VCUT8\n`define VMQ(q) hfd_vm_``q``_jv\n' + m.group(0) + '\n'


def run_yosys(ybin, td):
    Path(td, 'vm_joined.sv').write_text(vm_joined_text())
    srcs = [f'{V}/common/ot_hfd_oreg1.sv', f'{S}/ot_hfd_oreg_fc.sv', 'rtl/common/ot_fwd_link_stage.sv',
            f'{T}/ot_hfd_vm_slice.sv', f'{T}/ot_hfd_vm_root_x.sv'] + [f'{S}/{h}.sv' for h in HALVES] + \
           [f'{S}/hfd_vm_{q}_jv.sv' for q in ('sw', 'nw', 'se', 'ne')]
    ys = [f'read_verilog -lib /src/{SRAM}'] + [f'read_verilog -sv -DVCUT8 /src/{f}' for f in srcs] + \
         ['read_verilog -sv /t/vm_joined.sv', 'hierarchy -top vm_joined', 'proc', 'opt_clean',
          'setattr -mod -set keep_hierarchy 1 ' + ' '.join(HALVES), 'flatten', 'opt_clean', 'write_json /t/vm.json']
    Path(td, 'r.ys').write_text('\n'.join(ys) + '\n')
    if ybin == 'docker':
        cmd = ['docker', 'run', '--rm', '-v', f'{Path.cwd()}:/src:ro', '-v', f'{td}:/t', 'openroad/orfs:latest', 'bash', '-lc',
               '/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys -q -s /t/r.ys > /t/yosys.log 2>&1']
    else:
        Path(td, 'r.ys').write_text(Path(td, 'r.ys').read_text().replace('/src/', str(Path.cwd()) + '/').replace('/t/', td + '/'))
        cmd = ['bash', '-lc', f'{ybin} -q -s {td}/r.ys > {td}/yosys.log 2>&1']
    r = subprocess.run(cmd)
    if r.returncode:
        sys.exit(f'yosys failed rc={r.returncode}: ' + Path(td, 'yosys.log').read_text()[-3000:])
    return json.loads(Path(td, 'vm.json').read_text())


def half_bits(mod):
    """per port: list of (bit status) -- outputs: 'pinreg' | reason; inputs: 'capture' | reason."""
    drv, loads = {}, defaultdict(list)
    for cn, c in mod['cells'].items():
        dirs = c.get('port_directions', {})
        for p, bits in c['connections'].items():
            for i, b in enumerate(bits):
                if not isinstance(b, int):
                    continue
                if dirs.get(p) == 'output':
                    drv[b] = (cn, c['type'], p, c)
                else:
                    loads[b].append((cn, c['type'], p, c))
    pbits = {}
    for p, d in mod['ports'].items():
        pbits[p] = (d['direction'], d['bits'])
    inbits = {b for p, (dr, bits) in pbits.items() if dr == 'input' for b in bits}
    tapbits = {b: p for p, (dr, bits) in pbits.items() if TAP.match(p) for b in bits}
    res = {}
    for p, (dr, bits) in pbits.items():
        if p in ('ck', 'rst') or TAP.match(p):
            continue
        st = []
        for b in bits:
            if not isinstance(b, int):
                st.append('const'); continue
            if dr == 'output':
                if b not in drv:
                    st.append('feedthrough' if b in inbits else 'undriven')
                    continue
                cn, ty, pp, c = drv[b]
                if ty not in FF_TYPES or pp != 'Q':
                    st.append(f'logic:{ty}'); continue
                clk = c['connections'].get('CLK', [None])[0]
                pol = c.get('parameters', {}).get('CLK_POLARITY', '1')
                if clk not in tapbits:
                    st.append('flop_not_on_tap'); continue
                if int(str(pol), 2) != 1:
                    st.append('negedge'); continue
                st.append('pinreg')
            else:
                ld = loads.get(b, [])
                if not ld:
                    st.append('unloaded'); continue
                if all(ty in FF_TYPES and pp == 'D' for _, ty, pp, _ in ld):
                    st.append('capture')
                else:
                    st.append('logic:' + ','.join(sorted({ty for _, ty, pp, _ in ld if not (ty in FF_TYPES and pp == 'D')})))
        res[p] = (dr, bits, st)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--yosys', default='docker')
    ap.add_argument('--out-json', required=True)
    ap.add_argument('--sdc-dir', required=True)
    a = ap.parse_args()
    with tempfile.TemporaryDirectory() as td:
        y = run_yosys(a.yosys, td)
    mods = y['modules']
    halves = {h: half_bits(mods[h]) for h in HALVES}
    top = mods['vm_joined']
    # top net bit -> (half, port, index, dir)
    ends = defaultdict(list)
    for cn, c in top['cells'].items():
        if c['type'] not in halves:
            continue
        h = c['type']
        for p, bits in c['connections'].items():
            if p not in halves[h]:
                continue
            dr = halves[h][p][0]
            for i, b in enumerate(bits):
                if isinstance(b, int):
                    ends[b].append((h, p, i, dr))
    credit = defaultdict(lambda: defaultdict(list))
    summ = {h: defaultdict(lambda: defaultdict(int)) for h in HALVES}
    fails = defaultdict(list)
    for b, es in ends.items():
        outs = [e for e in es if e[3] == 'output']
        for h, p, i, dr in es:
            if dr != 'input':
                continue
            rx = halves[h][p][2][i]
            if not outs:
                why = 'die_face_or_top (sender not a VM8 half: unverified)'
            elif len(outs) != 1:
                why = f'multi_driver {outs}'
            else:
                sh, sp, si, _ = outs[0]
                tx = halves[sh][sp][2][si]
                why = '' if (tx == 'pinreg' and rx == 'capture') else f'sender {sh}.{sp}[{si}]={tx} receiver={rx}'
            if why:
                summ[h][p]['no_credit'] += 1
                if not why.startswith('die_face'):
                    fails[h].append(f'{p}[{i}]: {why}')
            else:
                summ[h][p]['credit'] += 1
                credit[h][p].append(i)
    # inputs of a half with no top connection at all (tied) are no-credit by construction
    out = dict(rule='credit iff VM8-half sender output bit = tap-clocked posedge flop Q direct to pin AND receiver input bit '
                    'feeds only flop D', clkq_ps=CLKQ,
               halves={h: {p: dict(v) for p, v in summ[h].items()} for h in HALVES},
               totals={h: dict(credit=sum(v.get('credit', 0) for v in summ[h].values()),
                               no_credit=sum(v.get('no_credit', 0) for v in summ[h].values()),
                               vm_vm_fail=len(fails[h])) for h in HALVES},
               vm_vm_failure_classes={h: dict(Counter(re.sub(r'\[\d+\]', '[*]', x) for x in fails[h])) for h in HALVES},
               vm_vm_failures={h: fails[h][:500] for h in HALVES})
    Path(a.out_json).write_text(json.dumps(out, indent=1) + '\n')
    sd = Path(a.sdc_dir); sd.mkdir(parents=True, exist_ok=True)
    for h in HALVES:
        L = [f'# generated by vm/vcut8/pinreg_credit_check.py: FF die-path hold credit (sender PINREG clk->Q {CLKQ} ps, wire 0)',
             '# ONLY on input bits proven fed by a tap-clocked flop Q direct to a VM8 half pin and captured by flops only',
             '# (lead ruling 2026-10-10, REVIEW_20261009.md).  Read after vclk_corner_true.sdc; FF session only.',
             'if {[llength [get_libs -quiet *_FF_*]] && [llength [get_clocks -quiet vclk]]} {', '  set ot_iom_n 0']
        for p, idx in sorted(credit[h].items()):
            width = len(halves[h][p][1])
            if len(idx) == width:
                L.append(f'  set ot_q [get_ports -quiet {{{p} {p}[*]}}]; set_input_delay -min {CLKQ} -clock vclk $ot_q; incr ot_iom_n [llength $ot_q]')
            else:
                for k in range(0, len(idx), 64):
                    names = ' '.join(f'{p}[{i}]' for i in sorted(idx)[k:k + 64])
                    L.append(f'  set ot_q [get_ports -quiet {{{names}}}]; set_input_delay -min {CLKQ} -clock vclk $ot_q; incr ot_iom_n [llength $ot_q]')
        L += ['  puts "OT_IOMIN vcut8 ' + h + ': PINREG-proven clk->Q credit on $ot_iom_n input bits"', '}', '']
        (sd / f'io_min_{h}.sdc').write_text('\n'.join(L))
    print(json.dumps(out['totals'], indent=1))


if __name__ == '__main__':
    main()
