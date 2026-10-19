#!/usr/bin/env python3
"""Generate isolated COLL128x256 SRAM with <=6 pins/um and explicit pin-access RC.

Immutable original macro and compiler defaults are untouched. Core array, repair,
behavior and operation latency are identical. New abstract stretches pin access
and includes a conservative M4 lead from the calibrated core to the furthest pin.
"""
import json,math
from pathlib import Path
import sram_gen as S
import asap7

ROOT = Path(__file__).resolve().parents[2]
NAME = 'ot_sram_1r1w_128x256_m1_r2c2_p192_mir'
BASE = S.timing_model
BASE_OUTLINE = S.macro_outline

def mirror_outline(cw,ch,pins):
    w,h,info=BASE_OUTLINE(cw,ch,pins)
    hn=math.ceil((round(h*1000)-24)/48)*48+24
    info.update(mirror_height_added_um=round(hn/1000-h,3),height_rule_nm="H=24mod48: M4centres stay12mod48 underR180")
    return w,hn/1000,info


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
    S.macro_outline = mirror_outline
    for name, words, bits, sr, sc in [('ot_sram_1r1w_128x256_m1_r2c2_p192_mir',128,256,2,2),('ot_sram_1r1w_32x128_m1_p192_rc',32,128,0,0)]:
        sheet = S.compile_macro(S.SramSpec(name,words,bits,1,1,'1r1w',sr,sc),ROOT/'physical/asap7_memory_macros')
        sheet['pin_access_contract'] = dict(pitch_um=0.192, max_density_per_um=1/0.192,
            exact_lead_um=sheet['area']['macro_height_um']-sheet['area']['core_height_um'],
            timing='Complete M4 terminal-to-core longest physical lead macroheight-coreheight. Elmore0.38RC+worst calibrated inv4/output driverR*C; clktoq/setup add actual lead delay, minperiod adds2lead delays; inputpin andclockcap,outputslew,read/writeenergy allrecomputed. Conservative minhold unchanged',
            immutable_original='ot_sram_1r1w_128x256_m1_r2c2' if words==128 else '7a2ff3761:ot_sram_1r1w_32x128_m1_p192',
            generator='tools/mem_compiler/build_coll_safe_pins_1019.py',
            claim='Calibrated analytical abstract; complete boundary/PG/contact/Lib/behavior. No transistor layout or silicon; no route-access qualification')
        path=ROOT/'physical/asap7_memory_macros'/name/(name+'.json')
        path.write_text(json.dumps(sheet,indent=2,sort_keys=True)+'\n')
        print(json.dumps(dict(macro=name,area=sheet['area'],timing=sheet['timing']),indent=1))

if __name__ == '__main__':
    main()
