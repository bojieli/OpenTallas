#!/usr/bin/env python3
"""Run the exact board application-credit helper against native W528 TX/RX."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    root = here.parents[2]
    args.out.mkdir(parents=True, exist_ok=False)
    native = here / 'tb_kvslice_native.sv'
    text = native.read_text()
    # Use the deployed helper body verbatim; never maintain a second model.
    marker = 'module qwen_kv_board_class_credit('
    assert text.count(marker) == 1
    helper = text[text.index(marker):]
    assert helper.count('endmodule') == 1
    (args.out / 'board.sv').write_text(helper)
    inputs = [here / 'tb_host_class_credit.sv',
              root / 'rtl/qwen_sys/host_20261013/qkd_host_tx_class.sv',
              root / 'rtl/qwen_sys/host_20261013/qkd_host_rx_class.sv']
    for path in inputs:
        shutil.copy2(path, args.out / path.name)
    build = ['verilator', '--binary', '--timing', '-j', '2', '--top-module',
             'tb_host_class_credit', '-Wno-fatal', '--Mdir', str(args.out / 'obj'),
             *(str(args.out / path.name) for path in inputs), str(args.out / 'board.sv')]
    with (args.out / 'build.log').open('w') as log:
        subprocess.run(build, stdout=log, stderr=subprocess.STDOUT, check=True)
    exe = str(args.out / 'obj/Vtb_host_class_credit')
    results = {}
    for name, extra in [('base', []), ('drop_ctrl', ['+DROP_CTRL_CREDIT'])]:
        run = subprocess.run([exe, *extra], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        (args.out / (name + '.log')).write_text(run.stdout)
        results[name] = {'returncode': run.returncode}
        if name == 'base':
            assert run.returncode == 0 and 'PASS_CLASS_CREDIT' in run.stdout, run.stdout
        else:
            assert run.returncode != 0 and 'class credit did not resume' in run.stdout, run.stdout
    receipt = {'status': 'PASS_TRANSPORT_COMPONENT_ONLY', 'results': results,
               'native_bench_sha256': hashlib.sha256(native.read_bytes()).hexdigest(),
               'helper_sha256': hashlib.sha256(helper.encode()).hexdigest(),
               'exact_payloads': 18, 'physical_only_delivered': 12,
               'class_windows': {'HOST': 4, 'CTRL': 4, 'DONE': 4},
               'production_rtl_changes': 0, 'added_arithmetic_cycles': 0,
               'whole_die_execution': 'NOT_RUN'}
    (args.out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
