"""mtp-lead 2026-10-09: exact gate of the MX1 registered MTP boundary (hfd_cmdproc_s_mtp_native_mx1 REGB=1).

R. System bench tb_hbm_native_mtp_mx1_regb_system: the physical top (AR + registered MTP boundary + join + finite-8
   queue) between the generic-die master hgi_mtp_native (PRL 4) and the typed operation backend; two drained-reset
   jobs, 4 tokens each.  Positive must PASS; these mutants must FAIL: MUT=2 host done not held behind the
   host-record FIFO, PRL=2 (controller read wait without the 2 boundary cycles), and the backend wrong-completion-job
   mutant (as in the hgi_mtp_native / MX1 gates).
D. Directed pin bench tb_hfd_cmdproc_s_mtp_native_mx1_regb (REGB=1): AM pulses during an in-flight command on the
   identity lines, 10 tokens with the host stalled + native done right after, owned ACK, drained reset, wrong job.
   Positive must PASS; MUT=1 (native done not held behind the emit FIFO) and MUT=2 must FAIL.  (The system
   scenario never backs the emit FIFO up, so MUT 1 is only exercised here.)
L. The original cycle-exact top bench (tb_hfd_cmdproc_s_mtp_native_mx1, 6adb6c001) on REGB=0: the unregistered
   wiring is unchanged by the refactor (the MTP side moved into hfd_cmdproc_s_mtp_native_mx1_mtp).
Usage: python3 tools/hbm_mx1_regb_gate.py --work DIR --out results/.../gate.json   (iverilog; run off localhost)
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NATIVE = json.loads((ROOT / 'results/rtl/hbm_token_fifo_reservation_20261009/native_mtp_sources.json').read_text())['sources']
NATIVE = [x.replace('ot_dshbm_dspark_top_stop.sv', 'ot_dshbm_dspark_top_cp_stop.sv')
          .replace('ot_hfd_mtp_core_stop.sv', 'ot_hfd_mtp_core_cp_stop.sv').replace('hfd_mtp_x_stop.sv', 'hfd_mtp_x_cp_stop.sv')
          for x in NATIVE]
FACADE = ['physical/hbm_mtp/rtl/hfd_mtp_native_cp_stop.sv', 'rtl/hbm_accel/generic/hgi_mtp_native.sv']
TOP = ['physical/hbm_cp_mtp_native/rtl/hfd_cmdproc_s_mtp_native_mx1.sv', 'rtl/common/ot_sc_pfifo.sv',
       'rtl/hbm_accel/control/ot_hbm_native_mtp_transaction_cp_join_mx1.sv',
       'rtl/hbm_accel/control/ot_hbm_native_mtp_emit_queue_mx1.sv',
       'physical/hbm_accel_die_views/cmdproc/rtl/hfd_cmdproc_s.sv',
       'physical/hbm_accel_die_views/cmdproc/rtl/ot_hfd_cmdproc20_m.sv',
       'physical/hbm_accel_die_views/common/ot_hfd_oreg1.sv',
       'physical/asap7_memory_macros/ot_sram_2rw_512x64_m4_r2c2/ot_sram_2rw_512x64_m4_r2c2.v',
       'rtl/common/ot_fwd_link_stage.sv']
BACKEND = 'rtl/hbm_accel/control/ot_hbm_native_mtp_operation_backend_mx1.sv'
CMDPROC20 = 'rtl/gpu_sys/ds_hbm_full20/ot_ds_hbm_cmdproc20.sv'
TB_R = 'rtl/test/hbm_accel/tb_hbm_native_mtp_mx1_regb_system.sv'
TB_L = 'physical/hbm_cp_mtp_native/rtl/tb_hfd_cmdproc_s_mtp_native_mx1.sv'
TB_D = 'physical/hbm_cp_mtp_native/rtl/tb_hfd_cmdproc_s_mtp_native_mx1_regb.sv'
L_OLD = 'hfd_cmdproc_s_mtp_native_mx1 #(.ENABLE_MTP(1)) dut('
L_NEW = 'hfd_cmdproc_s_mtp_native_mx1 #(.ENABLE_MTP(1),.REGB(0)) dut('
MUT_NEEDLE = 'cpl_job=raw[232:201]'


def run(work, name, top, srcs, params=()):
    exe = work / f'{name}.vvp'
    b = subprocess.run(['iverilog', '-g2012', '-s', top, *[f'-P{top}.{p}' for p in params], '-o', str(exe),
                        *[str(s) for s in srcs]], capture_output=True, text=True)
    if b.returncode:
        return dict(case=name, phase='compile', returncode=b.returncode, output=b.stderr[-4000:])
    r = subprocess.run(['vvp', '-n', str(exe)], capture_output=True, text=True)
    return dict(case=name, returncode=r.returncode, output=r.stdout[-3000:])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--work', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--single', help='run one system case (e.g. R_mutant_done_not_held) and exit with its raw simulation '
                                     'rc (closure-loop expect=fail bench); --out is then the case log')
    a = ap.parse_args()
    if a.single:
        a.work.mkdir(parents=True, exist_ok=True)
        sysb = [ROOT / s for s in NATIVE + FACADE + TOP + [CMDPROC20, BACKEND, TB_R]]
        dirb = [ROOT / s for s in TOP + [TB_D]]
        top, srcs, params = {'R_system_positive': ('tb_hbm_native_mtp_mx1_regb_system', sysb, ()),
                             'R_mutant_hostdone_not_held': ('tb_hbm_native_mtp_mx1_regb_system', sysb, ('MUT=2',)),
                             'R_mutant_prl2': ('tb_hbm_native_mtp_mx1_regb_system', sysb, ('PRL=2',)),
                             'D_pins_positive': ('tb_hfd_cmdproc_s_mtp_native_mx1_regb', dirb, ()),
                             'D_mutant_done_not_held': ('tb_hfd_cmdproc_s_mtp_native_mx1_regb', dirb, ('MUT=1',)),
                             'D_mutant_hostdone_not_held': ('tb_hfd_cmdproc_s_mtp_native_mx1_regb', dirb, ('MUT=2',))}[a.single]
        c = run(a.work, a.single, top, srcs, params)
        a.out.write_text(json.dumps(c, indent=2) + '\n')
        print(c['output'][-1500:])
        if c.get('phase') == 'compile':
            raise SystemExit('compile error (not a functional failure)')   # a compile error must not pass a fail bench
        print(f"MX1_REGB_CASE {a.single} rc={c['returncode']}")
        raise SystemExit(c['returncode'])
    if a.out.exists():
        raise SystemExit('immutable output exists')
    a.work.mkdir(parents=True, exist_ok=True)
    be = (ROOT / BACKEND).read_text()
    assert MUT_NEEDLE in be
    be_mut = a.work / 'backend_wrong_job.sv'
    be_mut.write_text(be.replace(MUT_NEEDLE, "cpl_job=raw[232:201]^32'd1"))
    tl = (ROOT / TB_L).read_text()
    assert L_OLD in tl, 'legacy bench instance changed'
    tb_l = a.work / 'tb_legacy_regb0.sv'
    tb_l.write_text(tl.replace(L_OLD, L_NEW))
    base = [ROOT / s for s in NATIVE + FACADE + TOP + [CMDPROC20]]
    sysb = base + [ROOT / BACKEND, ROOT / TB_R]
    top = 'tb_hbm_native_mtp_mx1_regb_system'
    dirb = [ROOT / s for s in TOP + [TB_D]]
    dtop = 'tb_hfd_cmdproc_s_mtp_native_mx1_regb'
    cases = [run(a.work, 'R_system_positive', top, sysb),
             run(a.work, 'R_mutant_hostdone_not_held', top, sysb, ('MUT=2',)),
             run(a.work, 'R_mutant_prl2', top, sysb, ('PRL=2',)),
             run(a.work, 'D_pins_positive', dtop, dirb),
             run(a.work, 'D_mutant_done_not_held', dtop, dirb, ('MUT=1',)),
             run(a.work, 'D_mutant_hostdone_not_held', dtop, dirb, ('MUT=2',)),
             run(a.work, 'R_mutant_wrong_job', top, base + [be_mut, ROOT / TB_R]),
             run(a.work, 'L_legacy_regb0_positive', 'tb_hfd_cmdproc_s_mtp_native_mx1', [ROOT / s for s in TOP] + [tb_l])]
    want = {c['case']: (c['returncode'] != 0 and c.get('phase') != 'compile') if 'mutant' in c['case']
            else (c['returncode'] == 0) for c in cases}
    ok = all(want.values())
    srcs = NATIVE + FACADE + TOP + [CMDPROC20, BACKEND, TB_R, TB_L, TB_D]
    rec = dict(schema='opentallas.hbm.mx1_regb.gate.v1', verdict='PASS' if ok else 'FAIL', expectations=want, cases=cases,
               source_sha256={s: hashlib.sha256((ROOT / s).read_bytes()).hexdigest() for s in srcs},
               scope='MX1 registered MTP boundary in the connected native closed control (real controller hgi_mtp_native PRL 4 '
                     '+ physical top incl. AR + typed backend + finite queue; synthetic SM arithmetic / kernel PCs); legacy '
                     'cycle-exact top bench on REGB=0')
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=2) + '\n')
    print(rec['verdict'], {c['case']: c['returncode'] for c in cases})
    for c in cases:
        print('==', c['case'], c['returncode'], c['output'].strip().splitlines()[-1:] if c['output'].strip() else '')
    raise SystemExit(0 if ok else 1)


if __name__ == '__main__':
    main()
