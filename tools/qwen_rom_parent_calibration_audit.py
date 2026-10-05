"""Read-only historical Qwen calibration audit; no model or hardware adoption."""
import argparse
import hashlib
import json
from pathlib import Path

import uarch_model as U

ROOT = Path(__file__).resolve().parents[1]


def audit():
    rows = {}
    for extra in (55, 112, 166, 167):
        point = U.qwen_tp_point(4, 6144, 'ucie_measured', clock_hz=1200000000,
                               me_lat_extra=extra, ctx=1, su_width=64)
        rows[str(extra)] = {key: point[key] for key in
                            ('cycles', 'layer_chain_cycles', 'tokens_s_b1')}
    attribution = U.qwen_l0_rtl_vs_model()
    body = attribution['model_layer_chain_cycles']
    measured = attribution['rtl']['cycles']
    collective = attribution['attribution']['allreduce_cycles']
    paths = (
        'tools/qwen_rom_parent_calibration_audit.py', 'tools/uarch_model.py',
        'tools/arch_budget_qwen3.py', 'tools/hdc_timing.py',
        'tools/uarch_model_qwen_kv_credit17.py',
        'tools/uarch_model_qwen_kv_bank_groups.py',
        'tools/uarch_model_qwen_kv_rate_risk.py',
        'results/rtl/qwen_rom_TP4_terminal_20261002/original_terminal.json',
        'results/uarch/qwen_rom_L0_terminal_source_20261003/terminal-review-r1.json',
    )
    return {
        'scope': 'model_only_position0_nohardwareadoption',
        'override_semantics': 'full_extras_not_increment', 'rows': rows,
        'existing_112plus54_product': U.QWEN_SS['me_lat_extra'],
        'L0_attribution': attribution,
        'source_sha256': {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
                          for p in paths},
        'verified_historical_cycle_reconciliation': {
            'measured_body_cycles': U.QWEN_L0_ATTR['body_cycles'],
            'model_body_cycles': body, 'measured_full_allreduce_cycles': collective,
            'allreduces': 2,
            'correct_model_body_plus_measured_collectives': body + 2 * collective,
            'remaining_body_gap_cycles': measured - (body + 2 * collective),
            'incorrect_existing_at_rtl_collective_formula_uses':
                attribution['rtl']['collective_lat_cycles'],
            'explanation': 'LAT339 is link/engine parameter, not complete serialized '
                           'allreduce991. Existing helper model_layer_cycles_at_rtl_collective '
                           'incorrectly substitutes LAT339.',
        },
        'adoption': False,
        'configuration_caveat': 'All extra sweep rows usectx1/UCIeMeasured/1.2GHz; '
                                'historicalcomparison helperusesboard/ctx1. Not claimedphysically'
                                'closedcurrentTP4orctx8191 performance.',
        'required_next': 'Reprice same selectedsource using fullwire+actualarithmeticextra '
                         'and matching fullcollective service; resolve per-regionbodygap before G4.',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = audit()
    with args.out.open('x') as destination:
        destination.write(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    main()
