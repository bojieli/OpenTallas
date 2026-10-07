#!/usr/bin/env python3
"""Map successor leaf storage to ASAP7 FFs; reject merged/missing FIFO mutants.
This is sequential cell mapping, not ORFS combinational mapping or P&R.
"""
import argparse
import copy
import hashlib
import json
import subprocess
from pathlib import Path
from check_embedding_metadata_cells import check_module

ROOT = Path(__file__).resolve().parents[1]
LIB = 'results/uarch/topk_station_SSFF_cell_model_20261002/inputs/asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib'
ROM = 'physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8_bb.v'


def run(out, yosys):
    out.mkdir(parents=True, exist_ok=True)
    records = []
    hashes = {}
    for kind in ('scale', 'code'):
        top = f'ot_qwen_embed_{kind}_bank_retained'
        rtl = f'rtl/physical/{top}.sv'
        dest = out / f'{kind}.json'
        for path in (rtl, LIB, ROM):
            hashes[path] = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
        parameter = f'chparam -set BANK_ID 2 {top}; ' if kind == 'scale' else ''
        commands = f'read_verilog -sv "{ROOT/ROM}" "{ROOT/rtl}"; {parameter}synth -top {top}; dfflibmap -liberty "{ROOT/LIB}"; opt_clean; write_json "{dest}"'
        result = subprocess.run([yosys, '-Q', '-T', '-p', commands], capture_output=True, text=True)
        (out / f'{kind}.log').write_text(result.stdout + result.stderr)
        result.check_returncode()
        module = json.loads(dest.read_text())['modules'][top]
        checks = check_module(module, top)
        records.append(dict(kind=kind, case='mapped_successor', passed=True, checks=checks))
        for mutant in ('merged_fifo', 'missing_fifo', 'short_fifo'):
            bad = copy.deepcopy(module)
            key = 'g_metadata_fifo[0].shadow'
            if mutant == 'merged_fifo':
                bad['netnames'][key]['bits'] = bad['netnames']['g_metadata_fifo[0].primary']['bits']
            elif mutant == 'missing_fifo':
                for name in (key, 'fifo_n[0]'):
                    bad['netnames'].pop(name, None)
            else:
                bad['netnames'][key]['bits'] = bad['netnames'][key]['bits'][:-1]
            try:
                check_module(bad, top)
            except (AssertionError, KeyError) as error:
                records.append(dict(kind=kind, case=mutant, rejected=True, reason=str(error)))
            else:
                raise AssertionError(f'{kind}: {mutant} unexpectedly passed')
    result = dict(scope='ASAP7 sequential cell mapping only; final ORFS mapped retention and physical timing remain mandatory',
                  source_sha256=hashes, yosys_version=subprocess.check_output([yosys, '-V'], text=True).strip(), cases=records, adoption=False)
    (out / 'result.json').write_text(json.dumps(result, indent=2)+'\n')
    print('PASS embedding sequential mapping: 2 full leaves and 6 rejected mapped mutants')


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--yosys', required=True)
    args=parser.parse_args()
    run(args.out.resolve(), args.yosys)
