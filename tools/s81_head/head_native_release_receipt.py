#!/usr/bin/env python3
"""Build a candidate receipt from the actual minimum HEAD native-reset proof.

Does not edit a plan, select a provider, or change any checker's default.
"""
import argparse
import gzip
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/die_plan'))
import schema as S
import head_native_release as H


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--plan', required=True)
    ap.add_argument('--proof-dir', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    plan = Path(a.plan)
    raw = json.loads(gzip.decompress(plan.read_bytes())) if plan.suffix == '.gz' else S.load(plan)
    P = S.Plan(raw, Path(a.plan))
    proof_dir, out = Path(a.proof_dir).resolve(), Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    sources = ['rtl/dsrom_sys/s81_head/ot_s81hd_serdes_link_ls.sv',
               'rtl/dsrom_sys/s81_head/ot_s81hd_serdes_link.sv']
    sources += ['rtl/dsrom_sys/s81_link/' + n + '.sv' for n in
        ['ot_pdie_serdes_locksafe', 'ot_pdie_serdes', 'ot_s81_kp4_common', 'ot_s81_kp4_enc',
         'ot_s81_kp4_dec', 'ot_s81_kp4_bm', 'ot_s81_kp4_dchn', 'ot_s81_kp4_ddly',
         'ot_s81_kp4_dout', 'ot_s81_kp4_dsyn']]
    sources += ['rtl/dsrom_sys/s81_link/ot_s81_gf1024.svh']
    sources += ['physical/asap7_memory_macros/' + n + '/' + n + '.v' for n in
                ['ot_sram_1r1w2c_64x546_m1', 'ot_sram_1r1w_32x546_m1']]
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    files = {os.path.relpath(ROOT / n, out): sha(ROOT / n) for n in sources}
    runs = {}
    for name in ['positive', 'early_hold', 'ignore_lock', 'leaf_reset', 'leaf_clock']:
        prefix = 'single_v2_' if name in ('positive', 'leaf_clock') else 'single_'
        rc = int((proof_dir / (prefix + name + '.rc')).read_text())
        src = proof_dir / (prefix + name + '.log')
        dst = out / src.name
        shutil.copyfile(src, dst)
        files[dst.name] = sha(dst)
        runs[name] = dict(log=dst.name, returncode=rc,
                         bench='native_single_v2_tb.sv' if name in ('positive', 'leaf_clock') else 'native_single_tb.sv')
    for name in ['native_single_tb.sv', 'native_single_v2_tb.sv', 'run_single.sh', 'run_single_v2.sh', 'leaf_reset.sv', 'leaf_clock.sv']:
        shutil.copyfile(proof_dir / name, out / name)
        files[name] = sha(out / name)
    bindings = [dict(part=n, target='u_phy.u_link.u_dec.u_chn.rst_n', native_clock_root='pma_rck')
                for n, p in P.parts.items() if p['type'] == 'hd_serdes']
    receipt = dict(schema='opentallas.head_native_release.v1', plan_sha256=H.digest(raw),
        cost=dict(rtl_state_bits_per_link=11, links=len(bindings), rtl_state_bits_total=11 * len(bindings),
                  mission_PIN_cycles=0, guard_native_boot_edges=66, hard_leaf_native_boot_edges=68,
                  core_cycle_deadline=None,
                  note='two 2-bit authority synchronizers + 6-bit counter + ready; legacy nine-FF comments predate split authority synchronizers'),
        bindings=bindings, files=files, proof=dict(verdict='PASS', guard_edges=66, leaf_edges=68,
            actual_codec_and_fifo=True, actual_leaf_binding=True,
            epochs=['cold', 'stopped_clock_lock_loss', 'stopped_clock_warm_reset'],
            mutants={n: 'DETECTED' for n in runs if n != 'positive'}, runs=runs,
            production_sources={n: sha(ROOT / n) for n in sources}),
        limits=['conditional local PHY release only', 'no finite core-cycle deadline with a stopped PMA clock',
                'no CDC or clock-period exception', 'zero mission cycles; 66 guard and 68 native reset boot edges'])
    # Fail before writing any acceptance artifact on failed or incomplete runs.
    for n, run in runs.items():
        if (run['returncode'] == 0) != (n == 'positive'):
            raise ValueError('unexpected proof return code: ' + n)
    path = out / 'native_release_receipt.json'
    path.write_text(json.dumps(receipt, indent=1) + '\n')
    print(path)


if __name__ == '__main__':
    main()
