#!/usr/bin/env python3
"""S81 layer vehicle, sub-agent B (el1011-s81lv/B, 2026-10-12): gate of the vehicle VM s81lv_vm_m
(rtl/dsrom_sys/s81_lv/vm_svc/) = dsfd_sp_vm_m with ONE real bank group (dsfd_vm_bgq28-equivalent tiles, all 4 bit
slices) and the other three groups as the address-checked TLM s81lv_vm_bgq_tlm.

    python3 tools/s81_lv/vm_svc_gate.py one CASE --out DIR
    python3 tools/s81_lv/vm_svc_gate.py all --out DIR [--cases a,b]    -> DIR/summary.json
    python3 tools/s81_lv/vm_svc_gate.py check-sync                     -> s81lv_vm_m body == dsfd_sp_vm_m body (bar the tile generate)

Cases:
  eq_g{0..3}        tb_s81lv_bgq_tlm_eq: TLM vs the real tile in lockstep (every pin, every cycle), group 0..3
  mut_eq_bgaddr     same with +define+S81LV_MUT_BGADDR (TLM group decode on row[5:4]) -> must FAIL
  vm_gold_g*        tb_dsfd_sp_vm (the closed VM gate, unchanged, DUT swapped to s81lv_vm_m) MODE 0 random, all clients
  vm_land_attn      MODE 4: HBM scan-service landing (f_svc two rows a cycle, LARM) + every other landing producer
  vm_land_hc        MODE 5
  mut_vm_bgaddr     vm_gold with the bank-group address mutant -> must FAIL
The tb is copied into the output dir with ONE edit: `dsfd_sp_vm_m #(` -> `s81lv_vm_m #(.GREAL(G), `."""
import argparse, json, re, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/s81_vm'))
import s81_vm_gate as G   # noqa: E402  (SRCS, verilator_bin: the closed VM gate's exact source list and tool pin)

D = 'rtl/dsrom_sys/s81_lv/vm_svc'
OWN = [f'{D}/s81lv_vm_bgq_tlm.sv', f'{D}/s81lv_vm_m.sv']
TILE = ['rtl/dsrom_sys/s81_ph/vm/dsfd_vm_bgq_sys.sv',
        'physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v']
CASES = {
    **{f'eq_g{g}': dict(kind='eq', params=dict(GRP=g, SEED=g + 1), expect='pass') for g in range(4)},
    'mut_eq_bgaddr': dict(kind='eq', params=dict(GRP=1, SEED=7), defines=['S81LV_MUT_BGADDR'], expect='fail'),
    'vm_gold_g0': dict(kind='vm', greal=0, params=dict(SEED=1), expect='pass'),
    'vm_gold_g2': dict(kind='vm', greal=2, params=dict(SEED=2), expect='pass'),
    'vm_land_attn': dict(kind='vm', greal=1, params=dict(MODE=4), expect='pass'),
    'vm_land_hc': dict(kind='vm', greal=3, params=dict(MODE=5), expect='pass'),
    'mut_vm_bgaddr': dict(kind='vm', greal=0, params=dict(SEED=1, NCYC=20000), defines=['S81LV_MUT_BGADDR'], expect='fail'),
}


def check_sync():
    a = (ROOT / 'rtl/dsrom_sys/s81_ph/vm/dsfd_sp_vm.sv').read_text()
    a = a[a.index('module dsfd_sp_vm_m #('):]
    b = (ROOT / f'{D}/s81lv_vm_m.sv').read_text()
    b = b[b.index('module s81lv_vm_m #('):]
    cut = lambda s: re.sub(r'            (if \(GREAL.*?end else begin : g_tlm.*?\n            end\n|// = dsfd_vm_bgq28.*?\.o_o\(coo\[t\+1\]\)\);\n)', '', s, flags=re.S)
    a2 = cut(a).replace('module dsfd_sp_vm_m #(', 'M'); b2 = cut(b).replace('module s81lv_vm_m #(\n    parameter integer GREAL = 0,', 'M')
    ok = a2 == b2
    print('CHECK_SYNC', 'OK' if ok else 'DRIFT (dsfd_sp_vm_m changed: regenerate s81lv_vm_m)')
    return ok


def build(out, tag, c):
    vbin, vver = G.verilator_bin()
    obj = out / f'obj_{tag}'
    defs = [f'+define+{d}' for d in c.get('defines', [])]
    gp = [f'-G{k}={v}' for k, v in c['params'].items()]
    if c['kind'] == 'eq':
        top, srcs = 'tb_s81lv_bgq_tlm_eq', [f'{D}/tb_s81lv_bgq_tlm_eq.sv', OWN[0], *TILE]
        srcs = [str(ROOT / s) for s in srcs]
    else:
        tb = (ROOT / G.SRCS[0]).read_text()
        assert tb.count('dsfd_sp_vm_m #(') == 1
        tbp = out / f'tb_dsfd_sp_vm_{tag}.sv'
        tbp.write_text(tb.replace('dsfd_sp_vm_m #(', f's81lv_vm_m #(.GREAL({c["greal"]}), '))
        top = 'tb_dsfd_sp_vm'
        srcs = [str(tbp), *[str(ROOT / s) for s in G.SRCS[1:]], *[str(ROOT / s) for s in OWN]]
    cmd = [vbin, '--binary', '--timing', '-O1', '-Wno-UNOPTFLAT', '-Wno-fatal', '-Wno-lint', '-Wno-style', '-j', '8',
           '--top-module', top, '--Mdir', str(obj), *defs, *gp, *srcs]
    b = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    (out / f'build_{tag}.log').write_text(vver + '\n' + ' '.join(cmd) + '\n' + b.stdout + b.stderr)
    return b.returncode, obj / f'V{top}', b.stdout + b.stderr


def one(name, out):
    c = CASES[name]
    out.mkdir(parents=True, exist_ok=True)
    rc, exe, blog = build(out, name, c)
    if rc:
        print(f'S81LV_VM_{name}: BUILD_FAIL'); print('\n'.join([l for l in blog.splitlines() if 'rror' in l][:20]))
        return dict(case=name, ok=False, build_fail=True)
    r = subprocess.run([str(exe)], capture_output=True, text=True)
    log = r.stdout + r.stderr
    (out / f'run_{name}.log').write_text(log)
    keep = [l for l in log.splitlines() if l.startswith(('RESULT', 'THROUGHPUT', 'PASS', 'FAIL', 'MISMATCH', 'FAULT', '%Error', 'LAND'))]
    passed = any(l.strip() == 'PASS' for l in log.splitlines())
    ok = passed if c['expect'] == 'pass' else not passed
    res = dict(case=name, kind=c['kind'], greal=c.get('greal'), params=c['params'], defines=c.get('defines', []),
               expect=c['expect'], passed=passed, ok=ok, tail=keep[-8:])
    print('\n'.join(keep[-8:]))
    print(f'S81LV_VM_{name}: {"PASS" if passed else "FAIL"} (expect {c["expect"]}) -> {"OK" if ok else "BAD"}')
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', choices=['one', 'all', 'check-sync']); ap.add_argument('case', nargs='?')
    ap.add_argument('--out'); ap.add_argument('--cases')
    a = ap.parse_args()
    if a.mode == 'check-sync':
        sys.exit(0 if check_sync() else 1)
    out = Path(a.out)
    if a.mode == 'one':
        sys.exit(0 if one(a.case, out)['ok'] else 1)
    names = a.cases.split(',') if a.cases else list(CASES)
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(len(names)) as ex:
        res = list(ex.map(lambda n: one(n, out / n), names))
    (out / 'summary.json').write_text(json.dumps(dict(sync=check_sync(), cases=res), indent=1))
    ok = all(r['ok'] for r in res)
    print('S81LV_VM_GATE', 'PASS' if ok else 'FAIL')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
