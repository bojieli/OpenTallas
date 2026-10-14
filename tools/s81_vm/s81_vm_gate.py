#!/usr/bin/env python3
"""Exact gate + throughput bench of the S81 VM master dsfd_sp_vm_m (s81-vm-1011, 2026-10-11).

    python3 tools/s81_vm/s81_vm_gate.py one CASE --out DIR      -> exit 0 iff the case meets its expectation
    python3 tools/s81_vm/s81_vm_gate.py all --out DIR           -> every case, DIR/summary.json

Cases (v2): gold_s{1,2,3} (exact, random all clients), tp (production-shape throughput), burst_* (all 128 roots back to
back at the root rate, > 56 rows a root, every lane), align_neg (misaligned phase must raise the alignment fault) and the
negative controls mut_stale / mut_dropw(_burst) / mut_early(_s2) / neg_early_consumer / mut_noalign / mut_np16 (must FAIL).
Bench rtl/dsrom_sys/s81_ph/test/tb_dsfd_sp_vm.sv (Verilator)."""
import argparse, json, re, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
SRCS = ['rtl/dsrom_sys/s81_ph/relays/dsfd_die_relays.sv', 'rtl/dsrom_sys/s81_ph/test/tb_dsfd_sp_vm.sv', 'rtl/dsrom_sys/s81_ph/vm/dsfd_sp_vm.sv',
        'rtl/dsrom_sys/s81_ph/vm/dsfd_vm_bgq_sys.sv', 'rtl/dsrom_sys/mtp/dsfd_vm_wfc_ep.sv',
        'rtl/dsrom_sys/mtp/ot_dsrom_mtp_link_rtt.sv', 'rtl/dsrom_sys/mtp/ot_dsrom_mtp_link_pair.sv',
        'rtl/dsrom_sys/mtp/rtt/ot_dsrom_mtp_rstsync.sv', 'rtl/dsrom_sys/s81_ctrl/ot_s81_engine_adapter.sv',
        'rtl/lib/ot_async_fifo.sv', 'rtl/lib/ot_reset_sync.sv', 'rtl/common/ot_ratio_cdc_fifo.sv',
        'physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v',
        'physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v']
# v2 (NP 24: 16 capture write-only lanes + 8 client ports, engine adapter, element-count completion counter)
CASES = {
    'gold_s1': dict(params=dict(SEED=1), expect='pass'),
    'gold_s2': dict(params=dict(SEED=2), expect='pass'),
    'gold_s3': dict(params=dict(SEED=3, NCYC=120000), expect='pass'),
    'tp': dict(params=dict(MODE=1, TP_ROWS=56), expect='pass'),
    'burst_r128': dict(params=dict(MODE=2, BROWS=128, BNP=0, BSKEW=3), expect='pass'),
    'burst_r128_np2': dict(params=dict(MODE=2, BROWS=128, BNP=1, BSKEW=3), expect='pass'),
    'burst_r256_skew6': dict(params=dict(MODE=2, BROWS=256, BNP=0, BSKEW=6), expect='pass'),
    'align_neg': dict(params=dict(MODE=3, BROWS=16), expect='pass', regex='ALIGN_FAULT'),
    'mut_stale': dict(params=dict(SEED=1, NCYC=20000), defines=['OT_SPVM_MUT_STALE'], expect='fail'),
    'mut_dropw': dict(params=dict(SEED=1, NCYC=20000), defines=['OT_SPVM_MUT_DROPW'], expect='fail'),
    'mut_dropw_burst': dict(params=dict(MODE=2, BROWS=128), defines=['OT_SPVM_MUT_DROPW'], expect='fail'),
    'mut_early': dict(params=dict(SEED=1, NCYC=20000), defines=['OT_SPVM_MUT_EARLY'], expect='fail'),
    'mut_early_s2': dict(params=dict(SEED=2, NCYC=20000), defines=['OT_SPVM_MUT_EARLY'], expect='fail'),
    'neg_early_consumer': dict(params=dict(SEED=1, NCYC=20000, EARLYC=1), expect='fail', regex='EARLY_READ'),
    'mut_noalign': dict(params=dict(MODE=3, BROWS=16), defines=['OT_SPVM_MUT_NOALIGN'], expect='fail'),
    'land_attn': dict(params=dict(MODE=4), expect='pass'),
    'land_hc': dict(params=dict(MODE=5), expect='pass'),
    'land_bp': dict(params=dict(MODE=4, LBP=1), expect='pass'),     # collective back-pressure: t_cts[0] must drop
    'mut_lsmall': dict(params=dict(MODE=4), defines=['OT_SPVM_MUT_LSMALL'], expect='fail'),
    'mut_np16': dict(params=dict(MODE=2, BROWS=128, BNP=0, BSKEW=3), defines=['OT_SPVM_MUT_NP16'], expect='fail'),
    'mut_rlat': dict(params=dict(SEED=1, NCYC=20000), defines=['OT_SPVM_MUT_RLAT'], expect='fail'),
}
# ---- hierarchy dsfd_vm_fe_h (el1013-s81-vmfe): flat reference at the hierarchy's stage counts (ref_*), lockstep with the
# hierarchy as a shadow (lk_*: every FE output bit-exact every cycle), hierarchy-only mutants (must break lockstep) and
# every case above with the hierarchy SUBSTITUTED for the flat FE (h_*: same expectation; pass cases also need LOCKSTEP_OK)
REF = ['OT_SPVM_REF_FRL']; LK = REF + ['OT_SPVM_FE_H']; SUB = LK + ['OT_SPVM_FE_H_SUBST']
LOCK_SET = ['gold_s1', 'gold_s2', 'tp', 'burst_r128', 'burst_r128_np2', 'land_attn', 'land_hc', 'land_bp', 'align_neg']
_base = dict(CASES)
CASES['ref_gold_s1'] = dict(_base['gold_s1'], defines=REF)
CASES['ref_tp'] = dict(_base['tp'], defines=REF)
CASES['ref_land_attn'] = dict(_base['land_attn'], defines=REF)
CASES['ref_land_bp'] = dict(_base['land_bp'], defines=REF)
for _n in LOCK_SET:
    CASES['lk_' + _n] = dict(_base[_n], defines=LK, regex2='LOCKSTEP_OK')
CASES['lk_mut_fxr1'] = dict(params=dict(SEED=1, NCYC=20000), defines=LK + ['OT_VMFE_MUT_FXR1'], expect='fail', regex='LOCKSTEP_BAD')
CASES['lk_mut_gbyp'] = dict(params=dict(MODE=4), defines=LK + ['OT_VMFE_MUT_GBYP'], expect='fail', regex='LOCKSTEP_BAD')
CASES['lk_mut_kqskip'] = dict(params=dict(SEED=1, NCYC=20000), defines=LK + ['OT_VMFE_MUT_KQSKIP'], expect='fail', regex='LOCKSTEP_BAD')
CASES['lk_mut_avbyp'] = dict(params=dict(MODE=4), defines=LK + ['OT_VMFE_MUT_AVBYP'], expect='fail', regex='LOCKSTEP_BAD')
CASES['lk_mut_wnqdrop'] = dict(params=dict(SEED=1, NCYC=20000), defines=LK + ['OT_VMFE_MUT_WNQDROP'], expect='fail', regex='LOCKSTEP_BAD')
for _n, _c in _base.items():
    CASES['h_' + _n] = dict(_c, defines=_c.get('defines', []) + SUB, **({'regex2': 'LOCKSTEP_OK'} if _c['expect'] == 'pass' else {}))
FEH_SRC = 'rtl/dsrom_sys/s81_ph/vm/dsfd_vm_fe_h.sv'
COVER = ['rd', 'wr', 'drain', 'cap', 'cts_low', 'cw_stall', 'rdy', 'dv', 'ks']   # every bin must be hit over the lockstep set


for _n in ('gold_s1','tp','mut_stale','h_gold_s1','h_tp','h_mut_stale'):
    _c=CASES[_n]
    CASES['be_hard_'+_n]=dict(_c,defines=_c.get('defines',[])+['OT_SPVM_BE_HARD_RELAYS'])

# Verilator >= 5.050 is REQUIRED (el1011-ds-vm 2026-10-11): 5.032 (Debian /usr/bin) miscompiles an automatic task that
# push_back()s into an element of an unpacked array of queues when the task is called for two different indices (the
# second call starts from a copy of the first queue: tb xrd() -> xs_row[0] gets xs_row[1]'s rows; minimal repro in the
# commit message).  The bench uses that construct throughout (xs_row / ex_l / ex_q / ex_t), so a 5.032 run is not
# evidence either way.  Resolution: $VERILATOR, else the fleet's pinned 5.050, else PATH; anything older is refused.
MIN_VERILATOR = (5, 50)


def verilator_bin():
    import os, shutil
    cands = [os.environ.get('VERILATOR'), str(Path.home() / '.local/opentallas-tools/verilator-5.050/bin/verilator'),
             shutil.which('verilator')]
    for b in cands:
        if not b or not Path(b).exists():
            continue
        v = subprocess.run([b, '--version'], capture_output=True, text=True).stdout
        m = re.search(r'Verilator (\d+)\.(\d+)', v)
        if m and (int(m.group(1)), int(m.group(2))) >= MIN_VERILATOR:
            return b, v.strip()
    return None, ' / '.join(str(b) for b in cands if b)


# Status-only relay candidate; source/sink assignment and physical closure remain open.
for _n in ('be_hard_h_gold_s1', 'be_hard_h_tp'):
    _c = CASES[_n]
    CASES['fault6_' + _n] = dict(_c, params=dict(_c['params'], BE_FAULT_STAGES=6))

def build(out, tag, defines, params):
    obj = out / f'obj_{tag}'
    vbin, vver = verilator_bin()
    if vbin is None:
        msg = f'TOOL_VERSION: Verilator >= {MIN_VERILATOR[0]}.{MIN_VERILATOR[1]:03d} required, none found ({vver})'
        (out / f'build_{tag}.log').write_text(msg + '\n')
        return 2, None, '%Error ' + msg
    cmd = [vbin, '--binary', '--timing', '-O1', '-Wno-UNOPTFLAT', '-Wno-fatal', '-Wno-lint', '-Wno-style', '-j', '8',
           '--top-module', 'tb_dsfd_sp_vm', '--Mdir', str(obj), *[f'+define+{d}' for d in defines],
           *[f'-G{k}={v}' for k, v in params.items()], '-I' + str(ROOT / 'rtl/dsrom_sys/s81_ph/vm'),
           *[str(ROOT / s) for s in SRCS + ([FEH_SRC] if 'OT_SPVM_FE_H' in defines else [])]]
    b = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    (out / f'build_{tag}.log').write_text(vver + '\n' + ' '.join(cmd) + '\n' + b.stdout + b.stderr)
    return b.returncode, obj / 'Vtb_dsfd_sp_vm', b.stdout + b.stderr


def one(name, out):
    c = CASES[name]
    out.mkdir(parents=True, exist_ok=True)
    rc, exe, blog = build(out, name, c.get('defines', []), c['params'])
    if rc:
        print(f'SPVM_{name}: BUILD_FAIL'); print('\n'.join([l for l in blog.splitlines() if 'rror' in l][:20]))
        return dict(case=name, ok=False, build_fail=True)
    r = subprocess.run([str(exe)], capture_output=True, text=True)
    log = r.stdout + r.stderr
    (out / f'run_{name}.log').write_text(log)
    keep = [l for l in log.splitlines() if l.startswith(('RESULT', 'THROUGHPUT', 'PASS', 'FAIL', 'MISMATCH', 'FAULT', 'MIRROR', '%Error', 'ALIGN', 'LOCKSTEP'))
            or 'EARLY_READ' in l]
    passed = any(l.strip() == 'PASS' for l in log.splitlines())
    ok = (passed and (not c.get('regex') or re.search(c['regex'], log) is not None)) if c['expect'] == 'pass' else (not passed and (not c.get('regex') or re.search(c['regex'], log) is not None))
    if c.get('regex2') and re.search(c['regex2'], log) is None:
        ok = False
    res = dict(case=name, expect=c['expect'], passed=passed, ok=ok, tail=keep[-12:])
    m = re.search(r'LOCKSTEP cycles.*', log)
    if m:
        res['lockstep'] = m.group(0)
    m = re.search(r'THROUGHPUT .*', log)
    if m:
        res['throughput'] = m.group(0)
    print('\n'.join(keep[-12:]))
    print(f'SPVM_{name}: {"PASS" if passed else "FAIL"} (expect {c["expect"]}) -> {"OK" if ok else "BAD"}')
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', choices=['one', 'all', 'set', 'cover']); ap.add_argument('case', nargs='?'); ap.add_argument('--out', required=True)
    a = ap.parse_args()
    out = Path(a.out)
    if a.mode == 'one':
        r = one(a.case, out)
        sys.exit(0 if r['ok'] else 1)
    if a.mode == 'cover':
        # coverage refusal over finished lk_* runs under --out (each DIR/<case>/run_<case>.log)
        tot = {k: 0 for k in COVER}; ports = 0; bad = []
        for n in ['lk_' + x for x in LOCK_SET]:
            f = out / n / f'run_{n}.log'
            log = f.read_text() if f.exists() else ''
            m = re.search(r'LOCKSTEP cycles=(\d+) mismatches=(\d+) pre=(\d+) ports=([0-9a-f]+) (.*)', log)
            if not m or 'LOCKSTEP_OK' not in log:
                bad.append(n); continue
            ports |= int(m.group(4), 16)
            for k, v in re.findall(r'(\w+)=(\d+)', m.group(5)):
                if k in tot:
                    tot[k] += int(v)
        miss = [k for k in COVER if tot[k] == 0] + ([f'ports {ports:07x}'] if ports != (1 << 28) - 1 else [])
        print('LOCKSTEP_COVER', json.dumps(tot), f'ports={ports:07x}', 'not_ok_cases=', bad)
        ok = not bad and not miss
        print('LOCKSTEP_SET', 'PASS' if ok else f'REFUSED (bins never exercised: {miss}; cases: {bad})')
        sys.exit(0 if ok else 1)
    if a.mode == 'set':     # comma-separated case list or prefix* in CASE
        names = [n for n in CASES if any(n == p or (p.endswith('*') and n.startswith(p[:-1])) for p in a.case.split(','))]
        res = [one(n, out / n) for n in names]
        (out / f'summary_{names[0]}_{len(names)}.json').write_text(json.dumps(res, indent=1))
        print('SPVM_SET', 'PASS' if all(r['ok'] for r in res) else 'FAIL', [r['case'] for r in res if not r['ok']])
        sys.exit(0 if all(r['ok'] for r in res) else 1)
    res = [one(n, out / n) for n in CASES]
    (out / 'summary.json').write_text(json.dumps(res, indent=1))
    ok = all(r['ok'] for r in res)
    print('SPVM_GATE', 'PASS' if ok else 'FAIL')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
