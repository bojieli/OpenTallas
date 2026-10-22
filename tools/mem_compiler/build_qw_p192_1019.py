#!/usr/bin/env python3
"""QW-SRAM3 (10-19): <=5.21 pins/um (0.192 um pitch) successors of the dense SRAM
masters the Qwen compute-die kits bind (64x512 10.2/um, 128x256 9.99/um,
512x128 ~7.3/um).

Same recipe as build_coll_safe_pins_1019.py (bb61ae67c, HBM COLL 128x256): core
array, spare rows/columns, behaviour, ports and operation latency unchanged; the
pin faces stretch to the 0.192 um pitch (H = 24 mod 48 so M4 centres stay on the
track phase under R180/MX), and the Liberty adds the conservative M4 lead
(macro height - core height) RC to clk->q, setup, min period, slew, pin/clock cap
and energy.  Originals are immutable; names are distinct (_p192_mir).
Analytical abstract only (no transistor layout); route access is qualified by the
consuming parent's gate/route, not by this file.
"""
import json, math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import sram_gen as S
import asap7

ROOT = Path(__file__).resolve().parents[2]
BASE = S.timing_model
BASE_OUTLINE = S.macro_outline
MACROS = [  # name, words, bits, mux, spare rows, spare cols, original
    ('ot_sram_1r1w_64x512_m1_r2c2_p192_mir', 64, 512, 1, 2, 2, 'ot_sram_1r1w_64x512_m1_r2c2'),
    ('ot_sram_1r1w_128x256_m1_r2c2_p192_mir', 128, 256, 1, 2, 2, 'ot_sram_1r1w_128x256_m1_r2c2'),
    ('ot_sram_1r1w_512x128_m4_r2c2_p192_mir', 512, 128, 4, 2, 2, 'ot_sram_1r1w_512x128_m4_r2c2'),
]


DATA = ('rd_out', 'wd_in', 'w_mask_in')


def bit_sliced(pins):
    """_p192_bs pin plan: each face carries COMPLETE bit slices (rd/wd/mask of bit b side by side) -- W = bits
    [0, W/2) with the control pins (clk/ce/addr) in the middle, E = bits [W/2, W) -- so per-bit logic never crosses
    the macro (M1-M4 are obstructed and the leaf layer cap is M5).  Spare/repair pins fill the faces to balance."""
    V = S.Pin
    data = {p.name: p for p in pins if p.name in DATA}
    W = data['rd_out'].width
    ctrl = [p for p in pins if p.name not in DATA and p.name in ('clk', 'wclk', 'rclk', 'r_ce_in', 'r_addr_in', 'w_ce_in', 'w_addr_in')]
    spare = [p for p in pins if p.name not in DATA and p not in ctrl]
    one = lambda p, b: V(b, 1, p.direction, p.kind, p.related)
    sl = lambda lo, hi: [one(data[n], f'{n}[{i}]') for i in range(lo, hi) for n in DATA]
    cbits = [one(p, b) for p in ctrl for b in p.bits()]
    sbits = [one(p, b) for p in spare for b in p.bits()]
    w_data, e_data = sl(0, W // 2), sl(W // 2, W)
    total = len(w_data) + len(e_data) + len(cbits) + len(sbits)
    per_edge = math.ceil(total / 2)
    k = max(0, per_edge - len(w_data) - len(cbits))
    mid = len(w_data) // 2
    west = sbits[:k // 2] + w_data[:mid] + cbits + w_data[mid:] + sbits[k // 2:k]
    east = e_data + sbits[k:]
    assert len(west) == per_edge and len(west) + len(east) == total, (len(west), len(east), per_edge)
    return west + east


def mirror_outline(cw, ch, pins):
    w, h, info = BASE_OUTLINE(cw, ch, pins)
    hn = math.ceil((round(h * 1000) - 24) / 48) * 48 + 24
    info.update(mirror_height_added_um=round(hn / 1000 - h, 3),
                height_rule_nm="H=24mod48: M4centres stay12mod48 underR180")
    return w, hn / 1000, info


def pin_access_timing(spec, area, cal, corner):
    t = BASE(spec, area, cal, corner)
    lead = max(0.0, area['macro_height_um'] - area['core_height_um'])
    r, c = asap7.SETRC['M4']
    cap = lead * c
    wire_ps = 0.38 * r * c * lead * lead
    delay = wire_ps + max(t.out_r_kohm, cal['corners'][corner]['inv4_r_kohm']) * cap
    t.clk_to_q_ps += delay
    t.setup_ps += delay
    t.min_period_ps += 2 * delay
    t.min_pulse_ps = 0.4 * t.min_period_ps
    t.out_slew_intrinsic_ps += delay
    t.pin_cap_ff += cap
    t.clk_cap_ff += cap
    t.read_energy_fj += spec.bits * cap * t.voltage ** 2
    t.write_energy_fj += spec.bits * cap * t.voltage ** 2
    t.breakdown.update(pin_access_lead_um=lead, pin_access_cap_ff=cap,
                       pin_access_wire_ps=wire_ps, pin_access_total_ps=delay)
    return t


def main():
    args = sys.argv[1:]
    bs = '--bit-sliced' in args
    only = set(a for a in args if not a.startswith('--'))
    if bs:
        base_write_lef = S.write_lef
        S.write_lef = lambda name, w, h, pins, props: base_write_lef(name, w, h, bit_sliced(pins), props)
    asap7.METAL['pin_pitch_um'] = 0.192
    S.timing_model = pin_access_timing
    S.macro_outline = mirror_outline
    out = ROOT / 'physical/asap7_memory_macros'
    for name, words, bits, mux, sr, sc, orig in MACROS:
        if bs:
            name = name.replace('_p192_mir', '_p192_bs')
        if only and name not in only:
            continue
        sheet = S.compile_macro(S.SramSpec(name, words, bits, mux, 1, '1r1w', sr, sc), out)
        sheet['pin_access_contract'] = dict(
            pitch_um=0.192, max_density_per_um=1 / 0.192,
            exact_lead_um=sheet['area']['macro_height_um'] - sheet['area']['core_height_um'],
            timing='M4 terminal-to-core longest lead = macro height - core height; Elmore 0.38RC + worst '
                   'calibrated inv4/output-driver R*C added to clk->q/setup/slew, 2x to min period; pin/clock '
                   'cap and read/write energy recomputed; min hold unchanged (conservative)',
            immutable_original=orig, generator='tools/mem_compiler/build_qw_p192_1019.py',
            recipe='bb61ae67c build_coll_safe_pins_1019.py' + (' + bit-sliced faces (W bits [0,W/2) + ctl, E bits [W/2,W))' if bs else ''),
            claim='Calibrated analytical abstract; no transistor layout or silicon; route access is '
                  'qualified only by the consuming parent gate/route')
        (out / name / (name + '.json')).write_text(json.dumps(sheet, indent=2, sort_keys=True) + '\n')
        a = sheet['area']
        print(name, 'W', a['macro_width_um'], 'H', a['macro_height_um'], 'core_h', round(a['core_height_um'], 3),
              'area', round(a['macro_area_um2'], 1), 'pins/edge', a['outline']['pins_per_edge'],
              'tt cq', round(sheet['timing']['tt']['clk_to_q_ps'], 1), 'tt minper',
              round(sheet['timing']['tt']['min_period_ps'], 1))


if __name__ == '__main__':
    main()
