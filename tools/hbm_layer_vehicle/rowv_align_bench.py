#!/usr/bin/env python3
"""HBMc/TOKEN2 (10-22): PHY row command alignment on a GEN die netlist (gen_die_func.py output).

Cuts every ctl_<q>_pNN that feeds a phy_<q> plus hb_ckgen plus the relay trees on the phy row_v pins, pulses
ctl row_v at the ctl outputs and reports, per PC, the hbm-clock cycle offset of row_v at the phy pin relative to
row_op (row_op/row_bank/row_row reach the phy direct in r18f/g; any relay on row_v shows as a positive offset).
Pass = offset 0 on every PC.   rowv_align_bench.py --die die_func.v --contract C.json --out DIR ; then run_collar_bench.sh
"""
import argparse, json, re, subprocess, sys
from pathlib import Path
T = Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--die', required=True); ap.add_argument('--contract', required=True); ap.add_argument('--out', required=True)
    a = ap.parse_args(); out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    t = Path(a.die).read_text()
    phys = re.findall(r"\n  ot_hbm3e_phy_rc_e8p5 (phy_\w+) \(", t)
    rowv, trees = {}, set()
    for ph in phys:
        seg = t[t.index(f' {ph} (\n'):][:40000]
        els = [e.strip() for e in re.search(r"\.row_v\(\{(.*?)\}\)", seg, re.S).group(1).split(',')][::-1]
        rowv[ph] = els
        trees |= {e.split('_')[0] for e in els if re.match(r'rf\d+_', e)}
    qs = sorted({ph[4:] for ph in phys})
    inc = '^(ctl_(' + '|'.join(qs) + r')_p\d\d|hb_ckgen)$'
    rel = '^(' + '|'.join(sorted(trees)) + ')_' if trees else '^$'
    r = subprocess.run([sys.executable, str(T / 'cut_slice.py'), '--die', a.die, '--contract', a.contract, '--include', inc,
                        '--with-relays', rel, '--relays-out', '--out', str(out / 'slice')], capture_output=True, text=True)
    (out / 'cut.log').write_text(r.stdout + r.stderr)
    if r.returncode:
        sys.exit('rowv_align_bench: cut failed ' + r.stderr[-300:])
    b = json.load(open(out / 'slice' / 'boundary.json')); ins = {x['name']: x['width'] for x in b['inputs']}
    h = lambda e: re.sub(r"\b([A-Za-z_]\w*)\b", lambda m: 'u.' + m.group(1), e)
    L = ['`timescale 1ns/1ps', 'module tb_collar;', '  reg refclk = 0, por_n = 0;', '  always #5 refclk = ~refclk;']
    for n, w in ins.items():
        if n not in ('hb_ckgen__refclk', 'hb_ckgen__por_n'):
            L.append(f'  reg [{w - 1}:0] {n} = 0;')
    L.append(f"  {b['slice_top']} u (" + ', '.join(f".{n}({'refclk' if n == 'hb_ckgen__refclk' else 'por_n' if n == 'hb_ckgen__por_n' else n})" for n in ins) + ');')
    L += ['  wire ck = u.hb_ckgen__pll_hbm[0];', '  integer cyc = 0, t_drv = -1, bad = 0;', '  always @(posedge ck) cyc <= cyc + 1;']
    pcs = []
    for ph, els in rowv.items():
        q = ph[4:]
        for p, e in enumerate(els):
            k = f'{q}{p:02d}'; pcs.append((q, p, k))
            L += [f'  wire v_{k} = {h(e)};', f'  integer a_{k} = -1;',
                  f'  always @(posedge ck) if (t_drv >= 0 && v_{k} && a_{k} < 0) a_{k} = cyc;']
    L.append('  initial begin')
    L += [f'    force u.ctl_{q}_p{p:02d}__row_v = 0;' for q, p, k in pcs]
    L.append('    #100 por_n = 1;')
    L += [f"    {n} = '1;" for n in ins if n.endswith('__pc_rst_n')]
    L.append('    #20000; @(negedge ck); t_drv = cyc + 1;')
    L += [f'    force u.ctl_{q}_p{p:02d}__row_v = 1;' for q, p, k in pcs]
    L.append('    @(negedge ck);')
    L += [f'    force u.ctl_{q}_p{p:02d}__row_v = 0;' for q, p, k in pcs]
    L.append('    repeat (80) @(posedge ck);')
    # calibration: a direct pin (row_op) is seen at t_drv-1 on this timing basis -> offset vs row_op = arrival - t_drv + 1
    for q, p, k in pcs:
        L += [f'    if (a_{k} < 0 || a_{k} - t_drv + 1 != 0) bad = bad + 1;',
              f'    $display("ROWV_OFFSET phy_{q}.row_v[{p}] %0d", a_{k} < 0 ? -999 : a_{k} - t_drv + 1);']
    L += [f'    if (bad == 0) $display("ROWV_ALIGN PASS {len(pcs)} PCs offset 0"); else $display("ROWV_ALIGN FAIL %0d of {len(pcs)} PCs misaligned", bad);',
          '    $finish; end', 'endmodule']
    (out / 'tb_collar.sv').write_text('\n'.join(L) + '\n')
    print(f'ROWV_BENCH_GEN phys={phys} pcs={len(pcs)} relay_trees={len(trees)} -> {out}')


if __name__ == '__main__':
    main()
