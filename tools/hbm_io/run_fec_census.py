#!/usr/bin/env python3
"""Admitted-host entry point: measure the actual opt-in rooted FEC state.

Run through ot-run. This does not create a physical view or substitute the
old HOST/SerDes abstract. All clocks remain actual RTL ports.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from fec_clock_census import census

ROOT = Path(__file__).resolve().parents[2]
FEC = 'rtl/hbm_accel/io_native_20261014/'
SOURCES = [FEC + n + '.sv' for n in (
    'ot_hbm_kp4_enc_rooted', 'ot_hbm_kp4_dec_rooted',
    'ot_hbm_kp4_encode52_map', 'ot_hbm_kp4_syndrome55_map',
    'hfd_serdes487_rooted')]
SOURCES += ['rtl/dsrom_sys/s81_link/ot_pdie_serdes.sv']
CLOCKS = ['clk', 'clk_collect', 'clk_encode', 'clk_codeword', 'pma_rck',
          'rclk_syndrome', 'rclk_bm0', 'rclk_bm1', 'rclk_bm2', 'rclk_bm3',
          'rclk_chien', 'rclk_emit']


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', required=True, type=Path)
    ap.add_argument('--yosys', default=str(Path.home()/'.local/opentallas-tools/yosys-0.68/bin/yosys'))
    a = ap.parse_args()
    out = a.out.resolve(); out.mkdir(parents=True, exist_ok=False)
    inputs = SOURCES + ['rtl/dsrom_sys/s81_link/ot_s81_gf1024.svh']
    hashes = {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in inputs}
    (out/'source.json').write_text(json.dumps(hashes, indent=2)+'\n')
    script = ('read_verilog -sv -D SYNTHESIS -Irtl/dsrom_sys/s81_link '
              + ' '.join(SOURCES) + '\n'
              'hierarchy -check -top hfd_serdes487_rooted\n'
              'proc\nflatten\nopt\nmemory_map\nopt\ncheck -assert\n'
              f'write_json {out}/netlist.json\nstat\n')
    (out/'census.ys').write_text(script)
    with (out/'yosys.log').open('w') as log:
        cp = subprocess.run([a.yosys, '-s', str(out/'census.ys')], cwd=ROOT,
                            stdout=log, stderr=subprocess.STDOUT)
    if cp.returncode:
        return cp.returncode
    result = census(json.loads((out/'netlist.json').read_text()),
                    'hfd_serdes487_rooted', CLOCKS)
    result['source_sha256'] = hashes
    result['checker_sha256'] = {
        name: hashlib.sha256((Path(__file__).parent/name).read_bytes()).hexdigest()
        for name in ('fec_clock_census.py', 'run_fec_census.py')}
    result['netlist_sha256'] = hashlib.sha256((out/'netlist.json').read_bytes()).hexdigest()
    result['open'] = ['Actual mapped area and leaf partition',
                      'Assigned die slots, pin registration, TT/FF/DRC closure',
                      'Delivered local/recovered clock phases and CDC qualification',
                      'Static complete link/HOST composition and production calendar']
    (out/'receipt.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k: result[k] for k in ('total_flop_bits', 'maximum_root_bits',
                                           'measured_cts_exception_required')}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
