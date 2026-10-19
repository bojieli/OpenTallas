#!/usr/bin/env python3
"""Generate isolated PVM64x512 SRAM with <=6 pins/um and explicit pin-access RC.

Immutable original macro and compiler defaults are untouched. Core array, repair,
behavior and operation latency are identical. New abstract stretches pin access
and includes a conservative M4 lead from the calibrated core to the furthest pin.
"""
import json
from pathlib import Path
import sram_gen as S
import asap7

ROOT = Path(__file__).resolve().parents[2]
NAME = 'ot_sram_1r1w_64x512_m1_r2c2_p192'
BASE = S.timing_model

def pin_access_timing(spec, area, cal, corner):
    t = BASE(spec, area, cal, corner)
    lead = max(0.0, area['macro_height_um'] - area['core_height_um'])
    r, c = asap7.SETRC['M4']
    cap = lead * c
    wire_ps = 0.38 * r * c * lead * lead
    # Actual output-driver resistance and calibrated inv4 input source bound.
    delay = wire_ps + max(t.out_r_kohm, cal['corners'][corner]['inv4_r_kohm']) * cap
    t.clk_to_q_ps += delay
    t.setup_ps += delay
    t.min_period_ps += 2 * delay
    t.min_pulse_ps = 0.4 * t.min_period_ps
    t.out_slew_intrinsic_ps += delay
    t.pin_cap_ff += cap
    t.clk_cap_ff += cap
    t.read_energy_fj += spec.bits * cap * t.voltage**2
    t.write_energy_fj += spec.bits * cap * t.voltage**2
    t.breakdown.update(pin_access_lead_um=lead, pin_access_cap_ff=cap,
                       pin_access_wire_ps=wire_ps, pin_access_total_ps=delay)
    return t

def main():
    asap7.METAL['pin_pitch_um'] = 0.192
    S.timing_model = pin_access_timing
    sheet = S.compile_macro(S.SramSpec(NAME, 64, 512, 1, 1, '1r1w', 2, 2), ROOT/'physical/asap7_memory_macros')
    sheet['pin_access_contract'] = dict(pitch_um=0.192, max_density_per_um=1/0.192,
        timing='All M4 lead length macroheight-coreheight; Elmore0.38RC plus worst calibrated inv4/output driver; clktoq/setup add lead delay; minperiod adds2lead delays; minhold unchanged conservative',
        immutable_original='ot_sram_1r1w_64x512_m1_r2c2', generator='tools/mem_compiler/build_pvm_safe_pins_1019.py',
        claim='Calibrated analytical abstract, not transistor layout or silicon')
    path=ROOT/'physical/asap7_memory_macros'/NAME/(NAME+'.json')
    path.write_text(json.dumps(sheet,indent=2,sort_keys=True)+'\n')
    print(json.dumps(dict(area=sheet['area'],timing=sheet['timing']),indent=1))

if __name__ == '__main__':
    main()
