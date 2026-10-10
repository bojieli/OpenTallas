"""mtp-lead 2026-10-09: exact gate of hgi_mtp_native, the generic HBM die (R25G) MTP master.

A. Connected closed control (the MX1 composition: native controller + MX1 transaction join + typed operation backend +
   finite-8 host emit queue; tb_hbm_native_mtp_cp_closed_control_mx1, Codex 9e6e2b20e) with the controller instance
   replaced by hgi_mtp_native (no su_red group: the bench already drove it with 523'b0).  Positive must PASS; the
   wrong-completion-job backend mutant must FAIL.
B. The controller's checked CP-result cases (tb_hfd_mtp_x_cp_stop: EOS / ngen / maxpos stop x reset-first), unchanged.
Usage: python3 tools/hgi_mtp_native_gate.py --work DIR --out results/.../gate.json   (iverilog; run off localhost)
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
MX1 = ['rtl/gpu_sys/ds_hbm_full20/ot_ds_hbm_cmdproc20.sv', 'rtl/hbm_accel/control/ot_hbm_native_mtp_operation_backend_mx1.sv',
       'rtl/hbm_accel/control/ot_hbm_native_mtp_transaction_cp_join_mx1.sv',
       'rtl/hbm_accel/control/ot_hbm_native_mtp_emit_queue_mx1.sv']
TB_A = 'rtl/test/hbm_accel/tb_hbm_native_mtp_cp_closed_control_mx1.sv'
TB_B = 'rtl/test/hbm_accel/tb_hfd_mtp_x_cp_stop.sv'
OLD_INST = ("hfd_mtp_native_cp_stop #(.ENABLE(1)) native(.clk(clk),.rst_n(rst_n),.f_cmdproc(tm),.t_cmdproc(fm),"
            ".f_su_red(523'b0),.f_router(59'b0),.f_coll(1'b1));")
NEW_INST = ("hgi_mtp_native native(.clk(clk),.rst_n(rst_n),.f_cmdproc(tm),.t_cmdproc(fm),"
            ".f_router(59'b0),.t_router(),.t_coll(),.f_coll(1'b1));")
MUT_NEEDLE = 'cpl_job=raw[232:201]'


def run(work, name, top, srcs, params=()):
    exe = work / f'{name}.vvp'
    b = subprocess.run(['iverilog', '-g2012', '-s', top, *[f'-P{top}.{p}' for p in params], '-o', str(exe),
                        *[str(s) for s in srcs]], capture_output=True, text=True)
    if b.returncode:
        return dict(case=name, phase='compile', returncode=b.returncode, output=b.stderr[-4000:])
    r = subprocess.run(['vvp', str(exe)], capture_output=True, text=True)
    return dict(case=name, returncode=r.returncode, output=r.stdout[-4000:])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--work', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    if a.out.exists():
        raise SystemExit('immutable output exists')
    a.work.mkdir(parents=True, exist_ok=True)
    tb = (ROOT / TB_A).read_text()
    assert OLD_INST in tb, 'connected bench instance changed'
    tb_a = a.work / 'tb_closed_control_hgi_mtp_native.sv'
    tb_a.write_text(tb.replace(OLD_INST, NEW_INST))
    be = (ROOT / MX1[1]).read_text()
    assert MUT_NEEDLE in be
    be_mut = a.work / 'backend_wrong_job.sv'
    be_mut.write_text(be.replace(MUT_NEEDLE, "cpl_job=raw[232:201]^32'd1"))
    base = [ROOT / s for s in NATIVE + FACADE]
    cases = [run(a.work, 'A_connected_positive', 'tb_hbm_native_mtp_cp_closed_control_mx1', base + [ROOT / s for s in MX1] + [tb_a]),
             run(a.work, 'A_connected_mutant_wrong_job', 'tb_hbm_native_mtp_cp_closed_control_mx1',
                 base + [ROOT / MX1[0], be_mut] + [ROOT / s for s in MX1[2:]] + [tb_a])]
    for k in (0, 1, 2):
        for r in (0, 1):
            cases.append(run(a.work, f'B_cp_result_k{k}_r{r}', 'tb_hfd_mtp_x_cp_stop', base + [ROOT / TB_B],
                             (f'KIND={k}', f'RESET_FIRST={r}')))
    want = {c['case']: (c['returncode'] != 0) if 'mutant' in c['case'] else (c['returncode'] == 0) for c in cases}
    ok = all(want.values()) and all(c.get('phase') != 'compile' for c in cases)
    srcs = NATIVE + FACADE + MX1 + [TB_A, TB_B]
    rec = dict(schema='opentallas.hgi_mtp_native.gate.v1', verdict='PASS' if ok else 'FAIL', expectations=want, cases=cases,
               source_sha256={s: hashlib.sha256((ROOT / s).read_bytes()).hexdigest() for s in srcs},
               scope='generic-die MTP master facade in the MX1 connected closed control (synthetic SM arithmetic / kernel '
                     'PCs, real controller + join + backend + queue) and the controller CP-result stop cases; no '
                     'generic-sequencer backend, no full-tensor arithmetic claim')
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=2) + '\n')
    print(rec['verdict'], {c['case']: c['returncode'] for c in cases})
    raise SystemExit(0 if ok else 1)


if __name__ == '__main__':
    main()
