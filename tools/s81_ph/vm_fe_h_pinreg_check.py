#!/usr/bin/env python3
"""Pin-register check of the dsfd_vm_fe_h leaves (el1013-s81-vmfe).

Rule: every leaf input bit is consumed ONLY by flip-flop pins (D / sync reset / enable) and every output bit is driven
directly by a flip-flop Q (or a constant).  Kit children that own their pin registers are black boxes; a leaf pin wired
straight to such a child, a strap, a clock or an async reset is legal only if it is in EXEMPT below (the same list as the
header of dsfd_vm_fe_h.sv).  The parent, with the leaves black-boxed, must hold 0 cells besides leaf instances.

    python3 tools/s81_ph/vm_fe_h_pinreg_check.py [--out DIR] [--leaf NAME ...]     exit 0 iff every leaf and the parent pass
"""
import argparse, json, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
SRCS = ['rtl/dsrom_sys/s81_ph/vm/dsfd_vm_fe_h.sv', 'rtl/dsrom_sys/s81_ph/vm/dsfd_sp_vm.sv', 'rtl/dsrom_sys/mtp/dsfd_vm_wfc_ep.sv',
        'rtl/dsrom_sys/mtp/ot_dsrom_mtp_link_rtt.sv', 'rtl/dsrom_sys/mtp/ot_dsrom_mtp_link_pair.sv',
        'rtl/dsrom_sys/mtp/rtt/ot_dsrom_mtp_rstsync.sv', 'rtl/dsrom_sys/s81_ctrl/ot_s81_engine_adapter.sv',
        'rtl/lib/ot_async_fifo.sv', 'rtl/lib/ot_reset_sync.sv', 'rtl/common/ot_ratio_cdc_fifo.sv']
# the SRAM macro is a black box: its behavioural model (64 x 512 registers) is never read
STUB = """(* blackbox *) module ot_sram_1r1w_64x512_m1_r2c2 (input clk, input r_ce_in, input [5:0] r_addr_in, output [511:0] rd_out,
    input w_ce_in, input [5:0] w_addr_in, input [511:0] wd_in, input [511:0] w_mask_in, input [1:0] rr_en, input [11:0] rr_addr,
    input [1:0] cr_en, input [17:0] cr_sel); endmodule
"""
LEAVES = ['dsfd_vm_fxs', 'dsfd_vm_fxr', 'dsfd_vm_fxa', 'dsfd_vm_fxb', 'dsfd_vm_frm', 'dsfd_vm_flt', 'dsfd_vm_fld', 'dsfd_vm_fcc', 'dsfd_vm_fcw', 'dsfd_vm_fcn', 'dsfd_vm_fsr', 'dsfd_vm_clt']
KIT = ['dsfd_vm_wfc_ep', 'ot_dsrom_mtp_rstsync', 'ot_s81_engine_adapter', 'ot_sram_1r1w_64x512_m1_r2c2']
CLK = {'ck', 'cks'}
EXEMPT = {   # leaf -> ports legally unregistered at the pin (reason in the dsfd_vm_fe_h.sv header)
    'dsfd_vm_flt': {'stride', 'off'},       # straps: registered (st_q / of_q) anyway; listed for the parent ties
    'dsfd_vm_fcw': {'rst', 'f_swv', 'f_swd', 'f_srv', 'f_srd', 't_swg', 't_srg', 't_ks'},   # dsfd_vm_wfc_ep owns the pin registers
    'dsfd_vm_fcc': {'rss', 'rst'},   # both only into the crossing's reset synchronisers
    'dsfd_vm_fcn': {'rst', 'rss', 'cv', 'cd', 'c_wr'},   # rstsync / cv, cd pin flops in the cks domain (checked: flop sinks only) / ready of a held output
    'dsfd_vm_clt': {'gid'},
}
FF_OK = {'D', 'SRST', 'EN', 'ARST', 'SET', 'CLR'}


def run(leaf, out, parent=False):
    js = out / f'{leaf}.json'
    bb = (LEAVES if parent else KIT)
    (out / 'sram_stub.v').write_text(STUB)
    # -defer: only the modules under the leaf are elaborated (a plain read elaborates every module of dsfd_sp_vm.sv at
    # its defaults, the bgq memories included: the first run sat in yosys for 40 min); the black boxes are therefore
    # made AFTER hierarchy, by name pattern (parameterised kit children are $paramod\\<name>\\...)
    ys = f'read_verilog -sv {out}/sram_stub.v\n' + ''.join(f'read_verilog -sv -defer -DSYNTHESIS -I{ROOT}/rtl/dsrom_sys/s81_ph/vm {ROOT}/{s}\n' for s in SRCS)
    ys += f'hierarchy -top {leaf}\n'
    ys += ''.join(f'blackbox {m} $paramod*{m}*\n' for m in bb if m != leaf and not m.startswith('ot_sram'))
    ys += f'setattr -mod -unset keep_hierarchy *\nproc\nflatten\nopt_expr\nopt_clean\nopt_dff\nopt_expr\nopt_clean\nmemory_collect\nopt_clean\nwrite_json {js}\n'
    (out / f'{leaf}.ys').write_text(ys)
    r = subprocess.run(['yosys', '-q', '-l', str(out / f'{leaf}.log'), str(out / f'{leaf}.ys')], capture_output=True, text=True)
    if r.returncode:
        return None, (r.stderr or r.stdout)[-400:]
    return json.loads(js.read_text())['modules'][leaf], ''


def is_ff(t):
    return t.startswith(('$dff', '$sdff', '$adff', '$dffe', '$sdffe', '$sdffce', '$adffe', '$aldff', '$dffsr', '$_DFF', '$_SDFF', '$ff'))


def check_leaf(leaf, out):
    m, err = run(leaf, out)
    if m is None:
        return dict(leaf=leaf, ok=False, error=err)
    sinks, drv = {}, {}
    for cn, c in m['cells'].items():
        for pn, bits in c['connections'].items():
            d = c.get('port_directions', {}).get(pn, 'input')
            for b in bits:
                if isinstance(b, int):
                    if d == 'output':
                        drv[b] = (c['type'], pn, cn)
                    else:
                        sinks.setdefault(b, []).append((c['type'], pn, cn))
    ex = EXEMPT.get(leaf, set()); bad_in, bad_out, exempt, nin, nout = {}, {}, {}, 0, 0
    for pn, p in m['ports'].items():
        for b in p['bits']:
            if p['direction'] == 'input':
                nin += 1
                if pn in CLK:
                    continue
                v = [s for s in sinks.get(b, []) if not (is_ff(s[0]) and s[1] in FF_OK)] if isinstance(b, int) else []
                if v:
                    (exempt if pn in ex else bad_in).setdefault(pn, set()).add(f'{v[0][0]}.{v[0][1]}')
            else:
                nout += 1
                d = drv.get(b) if isinstance(b, int) else ('const', 'Q', '')
                if d is None or not ((is_ff(d[0]) and d[1] == 'Q') or d[0] == 'const'):
                    (exempt if pn in ex else bad_out).setdefault(pn, set()).add('undriven' if d is None else f'{d[0]}.{d[1]}')
    ffb = sum(len(c['connections'].get('Q', [])) for c in m['cells'].values() if is_ff(c['type']))
    return dict(leaf=leaf, ok=not bad_in and not bad_out, in_bits=nin, out_bits=nout, ff_bits=ffb,
                bad_in={k: sorted(v) for k, v in bad_in.items()}, bad_out={k: sorted(v) for k, v in bad_out.items()},
                exempt={k: sorted(v) for k, v in exempt.items()})


def check_parent(out):
    m, err = run('dsfd_vm_fe_h', out, parent=True)
    if m is None:
        return dict(leaf='dsfd_vm_fe_h', ok=False, error=err)
    other = {}
    for c in m['cells'].values():
        if c['type'] not in LEAVES:
            other[c['type']] = other.get(c['type'], 0) + 1
    # no parent input may reach a parent output without a leaf in between (wires-only AND no feed-through)
    ins = {b for p in m['ports'].values() if p['direction'] == 'input' for b in p['bits'] if isinstance(b, int)}
    thru = sorted(pn for pn, p in m['ports'].items() if p['direction'] == 'output' and any(b in ins for b in p['bits']))
    if thru:
        other['feedthrough:' + ','.join(thru)] = len(thru)
    inst = {}
    for c in m['cells'].values():
        if c['type'] in LEAVES:
            inst[c['type']] = inst.get(c['type'], 0) + 1
    return dict(leaf='dsfd_vm_fe_h', ok=not other, instances=inst, non_leaf_cells=other)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--out', default='/tmp/vm_fe_h_pinreg'); ap.add_argument('--leaf', nargs='*')
    a = ap.parse_args(); out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    res = [check_leaf(l, out) for l in (a.leaf or LEAVES)] + ([] if a.leaf else [check_parent(out)])
    (out / 'summary.json').write_text(json.dumps(res, indent=1))
    for r in res:
        print('PINREG', r['leaf'], 'PASS' if r['ok'] else 'FAIL', json.dumps({k: v for k, v in r.items() if k not in ('leaf', 'ok')}))
    ok = all(r['ok'] for r in res)
    print('PINREG_ALL', 'PASS' if ok else 'FAIL')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
