#!/usr/bin/env python3
"""Prepare closure on Erdos's literal parity successor; no RTL or validation replay."""
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
ENGINE = 'rtl/rom/ot_w15_rom_oneshot_px_headreg.sv'
FILES = (ENGINE, 'rtl/hdc/ot_hdc_fastfp.sv',
         'rtl/hdc/ot_hdc_fp32_add_lat.sv', 'rtl/proto/ot_fp32_add_rne_pipe.sv')
OWNER_SHA = 'bca6652c3647dfa8885e1688ef69952ba61cc501'
ENGINE_SHA = '94395dc350d2cecee72d5e921a8597bc9eb353ac208f89ed4a3ce13b12c16a51'


def prepare(parent_die, owner_result, *, full_shape, clock_hz, command_ids=None):
    raw = parent_die.read_bytes()
    source = raw.decode()
    # Literal current parent parameters, not a made-up small closure instance.
    expected = {
        'N_TP': '4', 'PKG_DIES': '2', 'CL_LANES': '16',
        'CL_DEPTH': 'FULL_SHAPE ? 256 : 16',
        'CL_RELAY': '1', 'CL_ADD_LAT': '3', 'CL_TAGW': '32',
    }
    for name, value in expected.items():
        match = re.search(r'parameter\s+integer\s+' + name + r'\s*=\s*([^,\n]+)', source)
        if not match or ' '.join(match[1].split()) != value:
            raise ValueError('actual enclosing collective parameter changed: ' + name)
    if 'localparam integer CL_GW = FULL_SHAPE ? 4 : 1;' not in source:
        raise ValueError('actual gather width changed')
    if '.PAIRWISE(FULL_SHAPE)' not in source or '.OUT_BP(FULL_SHAPE)' not in source:
        raise ValueError('actual pairwise/backpressure source changed')
    pins = {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in FILES}
    if pins[ENGINE] != ENGINE_SHA:
        raise ValueError('Erdos successor source changed: consume his next exact source explicitly')
    ids = None if command_ids is None else json.loads(command_ids.read_text())
    if ids is not None and (not isinstance(ids, list) or not ids):
        raise ValueError('actual unique accepted command IDs must be a nonempty list')
    if clock_hz <= 0 or (ids is not None and len(set(ids)) != len(ids)):
        raise ValueError('positive actual clock and unique command IDs required')
    # Reuse Erdos's committed geometry/area price directly. No model-import
    # side effects or duplicate census; its 210-command example is replaced
    # only when Archimedes supplies actual unique accepted command identities.
    model_path = ROOT/'results/uarch/dsrom_collective_headreg_20261003/model.json'
    price = json.loads(model_path.read_text())
    price.update(collective_ids=ids, clock_hz=clock_hz,
        added_cycles=None if ids is None else len(ids),
        added_seconds=None if ids is None else len(ids)/clock_hz,
        scope='Existing owner geometry price; total startup cost requires actual source command IDs')
    price['per_actual_unique_command_cycles'] = 1
    price['per_actual_unique_command_seconds'] = 1 / clock_hz
    params = dict(REGISTER_HEAD=1, N=4, RANK=0, LANES=16, TAGW=32,
                  DEPTH=256 if full_shape else 16, PKG_DIES=2, RELAY=1,
                  ADD_LAT=3, PAIRWISE=int(full_shape), GW=4 if full_shape else 1,
                  OUT_BP=int(full_shape), FIFO_SRAM=0)
    receipt = json.loads(owner_result.read_text())
    # Original terminated receipt is preserved. A new functional result and
    # actual-context latency are owned by Erdos/Archimedes, never replayed here.
    functional_pass = bool(receipt.get('pass', False))
    args = ['python3', 'tools/run_abi3_physical.py', '--view', 'asap7',
            '--top', 'ot_w15_rom_oneshot_die_px_headreg', '--stages', 'pnr',
            '--clock-period-ns', format(1e9 / clock_hz, '.15g'),
            '--clock-uncertainty-ns', '0.060',
            '--clock-uncertainty-hold-ns', '0.025',
            '--orfs-corner', 'WC', '--hold-corners', 'WC,BC',
            '--keep-heavy-artifacts']
    for f in FILES: args.extend(['--source', f])
    for k,v in params.items(): args.extend(['--param', f'{k}={v}'])
    record = dict(schema='opentallas.dsrom.parity_head.physical_inputs.v1',
        owner_source_commit=OWNER_SHA, source_sha256=pins,
        owner_model_sha256=hashlib.sha256(model_path.read_bytes()).hexdigest(),
        enclosing_source=str(parent_die.resolve()),
        enclosing_sha256=hashlib.sha256(raw).hexdigest(),
        full_shape=full_shape, selected_parameters=params,
        clock_status="Selected timing target; seconds are MODEL-only until actual clock/context qualification",
        price=price, owner_receipt=str(owner_result.resolve()),
        owner_receipt_sha256=hashlib.sha256(owner_result.read_bytes()).hexdigest(),
        owner_functional_pass=functional_pass,
        owner_run_summary=receipt.get('runs'),
        actual_context_latency=None, actual_unique_command_count=None if ids is None else len(ids),
        input_output_delays_and_loads=None,
        closure=dict(SS_setup_ps=60, FF_hold_ps=25, target_clock_hz=clock_hz,
                     placed_miss_under150ps='route before any failure verdict',
                     run_count=0, SS_WNS=None, FF_WNS=None, adopt=False),
        area_and_routing=dict(new_head_state_bits_per_die=price['extra_state_bits_per_die'],
                     cell_floor_mm2=price['cell_area_floor_mm2'],
                     FIFO_depth=params['DEPTH'], FIFO_capacity_change=0,
                     relay_parity_external_boundary_delta=0,
                     loaded_area=None, channel_capacity=None, slot_fit=None),
        physical_command_prefix=args,
        physical_command_is_NOT_launch_ready=True,
        remaining_inputs=['Erdos functional qualification for selected source',
                          'Archimedes measured context latency and command IDs',
                          'parent input/output delays, loads and clock-domain context',
                          'measured host admission/headroom; NUM_CORES16..24',
                          'use uncapped runner facade; preserve completed objects'],
        restrictions=['do not replay Qwen or parity numerical gates',
                      'do not modify successor relay/parity/credits/reduction order',
                      'do not harden or replicate qelement in this scope',
                      'SS/FF of this element does not qualify whole-token gain'])
    return record


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--parent-die',required=True,type=Path)
    p.add_argument('--owner-result',required=True,type=Path)
    p.add_argument('--full-shape',action='store_true')
    p.add_argument('--clock-hz',required=True,type=float)
    p.add_argument('--actual-command-ids',type=Path)
    p.add_argument('--out',required=True,type=Path)
    a=p.parse_args()
    result=prepare(a.parent_die,a.owner_result,full_shape=a.full_shape,
                   clock_hz=a.clock_hz,command_ids=a.actual_command_ids)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(dict(parameters=result['selected_parameters'],
        added_cycles=result['price']['added_cycles'], per_command_cycles=1,
        new_head_state_bits=result['price']['extra_state_bits_per_die'],
        owner_functional_pass=result['owner_functional_pass'],physical_runs=0)))


if __name__=='__main__':main()
