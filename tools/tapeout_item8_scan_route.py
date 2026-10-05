#!/usr/bin/env python3
"""Execute handoff scan recipe 1 without changing element RTL or the driver.

Only the explicit frame/pin recipes 1 and 3 are selected. Source hashes and slot pricing
are written before execution; historic pre-row-fix ATPG is never its verdict.
The admitted owner controls resources; synthesis and routing have no deadline.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import run_abi3_physical as driver

BASE = 'results/dft/tapeout_20261004/dsrom_q_element/noscan/physical.json'
ROWFIX = {'rtl/v41rom/ot_v41_rom_elem_qp_w10.sv',
          'rtl/v41rom/ot_v41_rom_elem_w10.sv'}


def prepare(output, recipe=1, frame_growth_percent=None):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    baseline = json.loads((ROOT / BASE).read_text())
    pins = []
    changed = []
    for source in baseline['design']['sources']:
        path = source['path']
        digest = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
        pins.append(dict(path=path, sha256=digest,
                         historical_sha256=source['sha256']))
        if digest != source['sha256']:
            changed.append(path)
    if set(changed) != ROWFIX:
        raise ValueError(f'expected only adopted row-decode fix, got {changed}')
    # In the existing S81 model, q and BF elements share this reserved slot.
    # Growth fills existing padding: no slot pitch, hop, replica or cycle change.
    model_source = ROOT / 'tools/dsrom_s81_fulldie.py'
    model_text = model_source.read_text()
    for literal in ('SLOT_H = 239.76', 'ELEM_DY = 4.32, 77.76',
                    'PAIRS, BF_PAIRS, ROOTS = 2417, 519, 128'):
        if literal not in model_text:
            raise ValueError('S81 slot changed; reprice before routing')
    # Fanout grows frame AREA by growing height only: the current S81 lane
    # width, macro offsets, pin span and die-level horizontal hops stay fixed.
    height = (126.9 * (1 + frame_growth_percent / 100)
              if frame_growth_percent is not None else 140.4)
    variant = (f'fanout_frame_plus{frame_growth_percent}'
               if frame_growth_percent is not None else f'recipe{recipe}')
    available = 239.76 - 77.76 - 4.32
    if height > available:
        raise ValueError('scan frame exceeds existing element slot')
    argv = baseline['runner']['argv'][1:]
    def replace(option, values):
        i = argv.index(option)
        argv[i + 1:i + 1 + len(values)] = values
    replace('--die-area', ['0', '0', '510.84', str(height)])
    replace('--core-area', ['0', '0.27', '510.84', str(height - 0.27)])
    replace('--nickname-tag', [f'item8_q_scan_{variant}'])
    if recipe == 3 or frame_growth_percent is not None:
        replace('--place-density', ['0.55'])
    replace('--keep-workdir', [str(output / 'work')])
    replace('--output', [str(output / 'physical.json')])
    argv += ['--dft', 'scan', '--scan-max-length', '1024', '--dft-bound-macros',
             '--pin-region', '^(scan_|test_mode).*=bottom:136.08-374.76']
    record = dict(
        variant=f'scan_{variant}_pinned_ports', adopted=False,
        frame_growth_percent=frame_growth_percent,
        frame_growth_axis='height_only_fixed_lane_width',
        place_density=0.55 if recipe == 3 or frame_growth_percent is not None else 0.6,
        baseline_record=BASE,
        baseline_record_sha256=hashlib.sha256((ROOT / BASE).read_bytes()).hexdigest(),
        source_pins=pins, changed_since_historical_baseline=changed,
        source_change='adopted b9e873649 second-macro row-decode fix; no new RTL',
        historical_atpg_reusable_as_verdict=False,
        model=dict(source=str(model_source.relative_to(ROOT)),
                   sha256=hashlib.sha256(model_source.read_bytes()).hexdigest(),
                   q_replicas_per_layer_die=1898, frame_width_um=510.84,
                   old_height_um=126.9, new_height_um=height,
                   reserved_element_height_um=available,
                   replicated_abstract_area_delta_mm2=1898*510.84*(height-126.9)/1e6,
                   slot_pitch_delta_um=0, die_outline_delta_um=0,
                   functional_cycles_delta=0, functional_bytes_delta=0,
                   functional_boundary_bits_delta=0, functional_replicas_delta=0,
                   functional_mux_fanout_delta=0, hop_length_delta_um=0,
                   modeled_per_user_rate_cost_percent=0,
                   route_clock_fit_qualified=False),
        route_argv=argv, threads=16, expected_peak_GB=48,
        synth_timeout_seconds=None, flow_timeout_seconds=None,
        required_after_route=['SS/FF 60ps/25ps corner STA',
                              'DRC/antenna/slew/cap/fanout zero',
                              'routed-netlist ATPG FC>=95 TC>=99.5',
                              'scan-off equivalence', 'gate-level replay'],
        status='prepared_not_launched')
    (output / 'recipe.json').write_text(json.dumps(record, indent=2) + '\n')
    return argv


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--recipe', type=int, choices=(1, 3), default=1)
    parser.add_argument('--frame-growth-percent', type=int, choices=(8, 15))
    parser.add_argument('--prepare-only', action='store_true')
    args = parser.parse_args()
    argv = prepare(args.output, args.recipe, args.frame_growth_percent)
    if args.prepare_only:
        return 0
    os.environ['OT_ORFS_NUM_CORES'] = '16'
    os.environ['MAKEFLAGS'] = '-j16'
    # New jobs use Bacon's shared explicit API. Never omit these arguments:
    # omission intentionally selects the driver's legacy numeric defaults.
    return driver.main(argv, synth_timeout=None, flow_timeout=None)


if __name__ == '__main__':
    sys.exit(main())
