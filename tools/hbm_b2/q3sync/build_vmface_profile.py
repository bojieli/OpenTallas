#!/usr/bin/env python3
"""Generate the qualified VM face2/assembly2 five-core profile and fresh clock adapters.

Run through ot-run with yosys/iverilog/vvp on PATH. This does source/clock
mechanism qualification only; physical floorplan review and routing are separate.
"""
import argparse
import importlib.util
import json
from pathlib import Path

from q3_common_clock import emit, qualify

ROOT = Path(__file__).resolve().parents[3]
NATIVE = 'rtl/hbm_accel/cores_split/ot_hfd_coll_q3_vmface2/ot_hbm_q3_producer_native.sv'
BENCH = 'tools/hbm_b2/q3stageb/tb_q3stageb.sv'


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', required=True, type=Path)
    args = ap.parse_args()
    out = args.out.resolve()
    if out.exists() and any(out.iterdir()):
        ap.error('output must be new or empty; existing source/clock results are retained')
    out.mkdir(parents=True, exist_ok=True)
    builder = ROOT / 'physical/die_plan/hbm/q3sync_kits/build_kit.py'
    spec = importlib.util.spec_from_file_location('vmface_physical_builder', builder)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    profile = out / 'profile'
    _, _, receipt = mod.materialize('body', profile, vm_face_contract=True)
    (profile / 'source_profile.json').write_text(json.dumps(receipt, indent=2) + '\n')
    census_path = profile / 'census.json'
    census = json.loads(census_path.read_text())
    roles = dict(cores={k: dict(clocks=v['clocks']['top_clock_ports'])
                       for k, v in census['totals_per_core'].items()})
    roles_path = out / 'clock_roles.json'
    roles_path.write_text(json.dumps(roles, indent=2) + '\n')
    clock = out / 'clock'
    emit(profile / 'rtl', roles_path, ROOT / NATIVE, ROOT / BENCH, clock, census_path)
    result = qualify(clock)
    print('Q3_VMFACE_PROFILE_PASS', census['modules_in_closure'], 'modules;',
          result['native']['clock_bits'], 'clock bits;', result['nonclock_bits'], 'nonclock bits')


if __name__ == '__main__':
    main()
