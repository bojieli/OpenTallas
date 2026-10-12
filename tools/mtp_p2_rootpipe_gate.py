#!/usr/bin/env python3
"""Run transaction and saturated-output gates for opt-in P2 rb4."""
import argparse
import json
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    out = parser.parse_args().out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    root = Path(__file__).resolve().parents[1]
    subprocess.run(['python3', str(root/'tools/mtp_p2_prefix_fixture.py')], cwd=out, check=True)
    d = 'rtl/experimental/mtp_p2_ordered_20261009/'
    common = ['rtl/v41rom/ot_v41_fadd.sv', 'rtl/common/ot_prefix.sv', 'rtl/common/ot_secded.sv',
              'rtl/common/ot_sc_pfifo.sv', 'rtl/model/hbm_pc40_native_sim_20261003/ot_sram_1r1w_128x256_m1_r2c2_sim.sv']
    path = [d+x+'.sv' for x in ['ot_mtp_p2_ordered_rows', 'ot_mtp_p2_prefix', 'ot_mtp_p2_prefix_native', 'ot_mtp_p2_prefix_path']]
    cases = [
        ('path', 'tb_mtp_p2_prefix_path', dict(ROOTPIPE=1), path+common, True, 'PATH PASS'),
        ('order', 'tb_mtp_p2_prefix_path', dict(ROOTPIPE=1, MUT=2), path+common, False, 'PATH unexpected fault'),
        ('prefix', 'tb_mtp_p2_prefix', dict(ROOTPIPE=1, DSTAGE=1), [d+'ot_mtp_p2_prefix.sv']+common, True, 'PREFIX PASS'),
        ('copy', 'tb_mtp_p2_prefix', dict(ROOTPIPE=1, DSTAGE=1, MUT_COPY_FIRST=1), [d+'ot_mtp_p2_prefix.sv']+common, False, 'PREFIX +0/-0 first-round mutant detected'),
        ('ue', 'tb_mtp_p2_prefix', dict(ROOTPIPE=1, DSTAGE=1, ERROR_MODE=1), [d+'ot_mtp_p2_prefix.sv']+common, True, 'PREFIX NEGATIVE PASS'),
        ('native', 'tb_mtp_p2_prefix', dict(ROOTPIPE=1, DSTAGE=1, ERROR_MODE=2), [d+'ot_mtp_p2_prefix.sv']+common, True, 'PREFIX NEGATIVE PASS'),
        ('pin', 'tb_mtp_p2_pin_output', {}, [d+'ot_mtp_p2_prefix_path.sv', 'rtl/common/ot_sc_pfifo.sv'], True, 'PIN PASS'),
        ('overwrite', 'tb_mtp_p2_pin_output', dict(MUT=1), [d+'ot_mtp_p2_prefix_path.sv', 'rtl/common/ot_sc_pfifo.sv'], False, 'PIN stalled output changed')]
    verdict = {}
    for name, top, params, sources, positive, marker in cases:
        binary = out/(name+'.vvp')
        cmd = ['iverilog', '-g2012', '-Irtl/common', '-s', top, '-o', str(binary)]
        subprocess.run(cmd+[f'-P{top}.{k}={v}' for k,v in params.items()]+sources+[d+top+'.sv'], cwd=root, check=True)
        log = out/(name+'.log')
        with log.open('w') as stream:
            run = subprocess.run(['vvp', '-n', str(binary)], cwd=out, stdout=stream, stderr=subprocess.STDOUT)
        ok = (run.returncode == 0 and marker in log.read_text()) if positive else (run.returncode != 0 and marker in log.read_text())
        verdict[name] = dict(rc=run.returncode, expected='pass' if positive else 'fail', ok=ok)
        print(name, 'OK' if ok else 'FAIL', flush=True)
    (out/'gate.json').write_text(json.dumps(verdict, indent=2)+'\n')
    if not all(v['ok'] for v in verdict.values()):
        raise SystemExit(1)
    print('ROOTPIPE GATE PASS 8 cases')


if __name__ == '__main__':
    main()
