#!/usr/bin/env python3
"""Budget the reserved PQ root pin stations using existing project anchors."""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/budgets'))
import common as C
GEOMETRY='results/uarch/dsrom_s81_pq_parent_geometry_20261007/binding.json'


def model():
    geometry=json.loads((ROOT/GEOMETRY).read_text())
    roots=geometry['bindings']['roots']
    if len(roots)!=128 or any(r['clock_source']!=f"cf{r['region']}.co"for r in roots):
        raise ValueError('real column clock binding required')
    max_wire,min_wire=100.,0.
    skew=C.SKEW_INTRA_PS
    ss_in=C.CLKQ_SS_PS+C.DRV_OUT_PS+C.WIRE_SS_PS_PER_UM*max_wire+skew
    ss_out=C.RCV_IN_PS+C.SETUP_SS_PS+C.WIRE_SS_PS_PER_UM*max_wire+skew
    ff_in=C.CLKQ_FF_MIN_PS+C.WIRE_FF_CREDIT_PS_PER_UM*min_wire
    ff_out=C.HOLD_FF_PS-C.WIRE_FF_CREDIT_PS_PER_UM*min_wire
    area=roots[0]['root']['w']*roots[0]['root']['h']
    target=min(C.LINT_A_PS+C.LINT_B_PS_PER_UM*math.sqrt(area),C.LINT_CAP_PS)
    sources=[GEOMETRY,'tools/budgets/common.py','tools/budgets/budget_sheet.py','tools/budgets/make_block_sdc.py','tools/s81/pq_root_budget.py']
    return dict(schema='opentallas.s81.pq-root-io-budget.v1',
        source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()for p in sources},
        scope='New production root reservation; planning budget, not current-die clock signoff',
        outline_um=[roots[0]['root']['w'],roots[0]['root']['h']],replicas=128,
        clocks=dict(root_source='cfN.co',reset_source='cfN.rs',period_ps=C.T_PS,
            SS_setup_uncertainty_ps=C.UNC_SETUP_PS,internal_FF_hold_uncertainty_ps=C.UNC_HOLD_PS,
            effective_interface_FF_hold_uncertainty_ps=C.HOLD_IO_SKEW_PS,
            FF_pairwise_replaces_global=True,FF_pairwise_is_not_global_plus_50=True,
            convention='Exactly make_block_sdc.ff_min: global hold25, pairwise vclki->core/core->vclk hold50. Effective IO50, not75.',
            maximum_intra_column_setup_skew_ps=skew,
            internal_insertion_SS_target_ps=round(target,3),absolute_entry_insertion_ps=None,
            FF_entry_min_max='Populate from actual per-corner CTS calibration; do not reuse old2050pair clock plan'),
        station_wire=dict(maximum_um=max_wire,minimum_um=min_wire,
            min_wire_credit_ps=0,maximum_length_not_used_for_hold_credit=True,
            actual_pin_geometry_and_obstacle_path_required=True),
        input=dict(max_SS_ps=ss_in,min_FF_ps=ff_in,source='Registered S station driven by native raw tree identity/data/error'),
        output=dict(max_SS_ps=ss_out,min_FF_ps=ff_out,destination='Registered N station in same column clock domain'),
        acceptance=dict(SS_setup_slack_ps=15,FF_hold_slack_ps=15,DRC=0),
        calibration_obligations=[
            'Rebuild current column CTS with new root/station capacitances; same-column skew including nonshared5% OCV must fit90ps',
            'Measure root SS/FF insertion mean,min,max; use fresh corner-matched extrema for virtual IO clocks',
            'Verify actual station cell clk-to-Q, slew, output loading and pin routes against shared anchor budget; extra cost must be priced',
            'Actual final pin wires <=100um and finite producer occupancy; no ready fabricated for native root',
            'Pipeline CAM exactness, source-matched hard views and mutable-state protection remain adoption gates'],
        station_latency=dict(new_input_and_output_registers_cycles=2,
            adopted_delta='Charge2 unless replacing explicitly identified existing return registers; legacy transport geometry excludes these new data connections'),
        physical_adopted=False)


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(model(),indent=2)+'\n')
