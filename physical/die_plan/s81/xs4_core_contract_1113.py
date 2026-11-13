#!/usr/bin/env python3
"""HARD-S81-DSDV-1 11-13 (R-CAP-3 point 3): pin contract of the ONE x-streamer hard core ot_s81sl_xs4 (u_c.u_xg.u_s in
the 16 dsdv_slice_*_C types).  Writes, from the constants below (cwd = repo root):

    physical/ref_tile/s81sl_xs4h/views/ot_s81sl_xs4/ot_s81sl_xs4.lef         LEF pin contract (kit io.tcl exact pins)
    physical/die_plan/s81/cores/views/xs4_prov_1113/ot_s81sl_xs4/            same LEF + PROVISIONAL tt/ff libs +
                                                                             insertion_provisional.json
    physical/die_plan/s81/inputs/core_pins/ot_s81sl_xs4.json                 plan pin table (core_pins_gen.table)

Outline 648.0 x 518.4 (4.32 lattice).  ONE pin face (N in the core frame; the plan places the core MX so the face looks
at the ring band), M5, one pin every third track (0.144 um), 4,365 pins.  Order along the face follows the macro map of
physical/ref_tile/s81sl_xs4h/spec.json (bank columns b1 | b0 | ROMs | b2), so every g_d slice lands over its own bank:
    g_d[2047:1024] | g_v g_fam g_idx is_v is_d | g_d[1023:0] | clk rst_n | xw_v xw_d fault | g_d[3071:2048]
The libs are PROVISIONAL (boundary flops at the stated insertion; inputs land in the K=1 capture flops, outputs leave
flops) and are replaced by the signed kit views.
"""
import json, sys
from pathlib import Path
sys.path[:0] = ["physical/die_plan/s81", "tools/die_plan"]
MOD = "ot_s81sl_xs4"
W, H = 648.0, 518.4
PITCH, OFF, STEP = 0.048, 0.012, 3          # M5 track pitch / offset, tracks per pin
PW, PH = 0.024, 0.084                       # pin shape (norm_finish contract form)
GAP = 12                                    # empty pin slots between groups
INS = dict(tt=330.0, ff=259.0)              # PROVISIONAL insertion (xrt1 RF-J signed view: 329.78 / 258.88)
GROUPS = [
    [("g_d", i, "in") for i in range(1024, 2048)],
    [("g_v", i, "in") for i in range(3)] + [("g_fam", i, "in") for i in range(3)] + [("g_idx", i, "in") for i in range(21)]
    + [("is_v", None, "in")] + [("is_d", i, "in") for i in range(160)],
    [("g_d", i, "in") for i in range(0, 1024)],
    [("clk", None, "in"), ("rst_n", None, "in")],
    [("xw_v", None, "out")] + [("xw_d", i, "out") for i in range(1101)] + [("fault", None, "out")],
    [("g_d", i, "in") for i in range(2048, 3072)],
]
BUS = dict(g_d=3072, g_v=3, g_fam=3, g_idx=21, is_d=160, xw_d=1101)


def pins():
    n = sum(len(g) for g in GROUPS) + GAP * (len(GROUPS) - 1) + 4      # 2 extra slots each side of clk
    k0 = round((W / 2 - OFF) / PITCH) - (n * STEP) // 2
    out, k = [], k0
    for gi, g in enumerate(GROUPS):
        for name, bit, d in g:
            if name == "clk":
                k += 2 * STEP
            x = round(OFF + k * PITCH, 4)
            out.append((name if bit is None else "%s[%d]" % (name, bit), d, x))
            k += STEP
            if name == "rst_n":
                k += 2 * STEP
        k += GAP * STEP
    assert out[0][2] >= 4.32 and out[-1][2] <= W - 4.32, (out[0], out[-1])
    return out


def lef(P):
    o = ['VERSION 5.8 ;', 'BUSBITCHARS "[]" ;', 'DIVIDERCHAR "/" ;', 'UNITS', '    DATABASE MICRONS 1000 ;', 'END UNITS', '',
         'MACRO %s' % MOD, '  FOREIGN %s 0 0 ;' % MOD, '  CLASS BLOCK ;', '  SIZE %g BY %g ;' % (W, H)]
    for name, d, x in P:
        w, h = (0.048, 0.48) if name == "clk" else (PW, PH)
        o += ['  PIN %s' % name, '    DIRECTION %s ;' % ("INPUT" if d == "in" else "OUTPUT"), '    USE SIGNAL ;', '    PORT',
              '      LAYER M5 ;', '        RECT %.4f %.4f %.4f %.4f ;' % (x - w / 2, H - h, x + w / 2, H), '    END', '  END %s' % name]
    return "\n".join(o + ['END %s' % MOD, 'END LIBRARY', ''])


IDX = "1.44000,  2.88000,  5.76000,  11.52000,  23.04000,  46.08000,  92.16000"
LOADS = [1.44, 2.88, 5.76, 11.52, 23.04, 46.08, 92.16]


def lib(P, corner):
    ins = INS[corner]
    k = 1.0 if corner == "tt" else 0.78
    su, ho = -(ins - 70.0 * k), ins - 20.0 * k          # capture flop one buffer behind the pin
    cq = ins + 60.0 * k
    o = ['library (%s) {' % MOD, '  comment : "PROVISIONAL HARD-S81-DSDV-1 11-13: boundary flops at insertion %g ps (%s); replaced by the signed kit view";' % (ins, corner),
         '  delay_model : table_lookup;', '  simulation : false;', '  capacitive_load_unit (1,fF);', '  leakage_power_unit : 1pW;',
         '  current_unit : "1mA";', '  pulling_resistance_unit : "1kohm";', '  time_unit : "1ps";', '  voltage_unit : "1v";',
         '  library_features(report_delay_calculation);', '  input_threshold_pct_rise : 50;', '  input_threshold_pct_fall : 50;',
         '  output_threshold_pct_rise : 50;', '  output_threshold_pct_fall : 50;', '  slew_lower_threshold_pct_rise : 10;',
         '  slew_lower_threshold_pct_fall : 10;', '  slew_upper_threshold_pct_rise : 90;', '  slew_upper_threshold_pct_fall : 90;',
         '  slew_derate_from_library : 1.0;', '  nom_process : 1.0;', '  nom_temperature : %s;' % ("25.0" if corner == "tt" else "0.0"),
         '  nom_voltage : %s;' % ("0.70" if corner == "tt" else "0.77"),
         '  lu_table_template(template_1) {', '    variable_1 : total_output_net_capacitance;', '    index_1("%s");' % IDX, '  }']
    for b, n in sorted(BUS.items()):
        o += ['  type ("%s") {' % b, '    base_type : array;', '    data_type : bit;', '    bit_width : %d;' % n, '    bit_from : %d;' % (n - 1), '    bit_to : 0;', '  }']
    o += ['  cell ("%s") {' % MOD, '    area : %.3f ;' % (W * H), '    is_macro_cell : true;']

    def one(name, d, ind):
        s = ind
        if name == "clk":
            r = [s + 'pin("clk") {', s + '  direction : input;', s + '  clock : true;', s + '  capacitance : 3.0;']
            for tt in ("min_clock_tree_path", "max_clock_tree_path"):
                v = ins - 20 * k if tt.startswith("min") else ins + 20 * k
                r += [s + '  timing() {', s + '    timing_sense : positive_unate;', s + '    timing_type : %s;' % tt,
                      s + '    cell_rise(scalar) { values("%.3f"); }' % v, s + '    cell_fall(scalar) { values("%.3f"); }' % v, s + '  }']
            return r + [s + '}']
        if d == "in":
            return [s + 'pin("%s") {' % name, s + '  direction : input;', s + '  capacitance : 1.2;',
                    s + '  timing() {', s + '    related_pin : "clk";', s + '    timing_type : hold_rising;',
                    s + '    rise_constraint(scalar) { values("%.3f"); }' % ho, s + '    fall_constraint(scalar) { values("%.3f"); }' % ho, s + '  }',
                    s + '  timing() {', s + '    related_pin : "clk";', s + '    timing_type : setup_rising;',
                    s + '    rise_constraint(scalar) { values("%.3f"); }' % su, s + '    fall_constraint(scalar) { values("%.3f"); }' % su, s + '  }', s + '}']
        dl = ",".join("%.3f" % (cq + 2.0 * k * c) for c in LOADS)
        tr = ",".join("%.3f" % (8.0 * k + 4.3 * k * c) for c in LOADS)
        r = [s + 'pin("%s") {' % name, s + '  direction : output;', s + '  capacitance : 0.5;', s + '  timing() {',
             s + '    related_pin : "clk";', s + '    timing_type : rising_edge;']
        for t, v in (("cell_rise", dl), ("rise_transition", tr), ("cell_fall", dl), ("fall_transition", tr)):
            r += [s + '    %s(template_1) {' % t, s + '      index_1("%s");' % IDX, s + '      values("%s");' % v, s + '    }']
        return r + [s + '  }', s + '}']

    by = {}
    for name, d, x in P:
        by.setdefault(name.split("[")[0], []).append((name, d))
    for base in sorted(by):
        if base in BUS:
            o += ['    bus("%s") {' % base, '      bus_type : %s;' % base, '      direction : %s;' % ("input" if by[base][0][1] == "in" else "output"), '      capacitance : 0.0000;']
            for name, d in sorted(by[base], key=lambda t: -int(t[0].split("[")[1][:-1])):
                o += one(name, d, "      ")
            o += ['    }']
        else:
            o += one(by[base][0][0], by[base][0][1], "    ")
    return "\n".join(o + ['  }', '}', ''])


def main():
    P = pins()
    L = lef(P)
    rt = Path("physical/ref_tile/s81sl_xs4h/views/%s" % MOD); rt.mkdir(parents=True, exist_ok=True)
    vw = Path("physical/die_plan/s81/cores/views/xs4_prov_1113/%s" % MOD); vw.mkdir(parents=True, exist_ok=True)
    (rt / (MOD + ".lef")).write_text(L)
    (vw / (MOD + ".lef")).write_text(L)
    for c in ("tt", "ff"):
        (vw / ("%s_%s.lib" % (MOD, c))).write_text(lib(P, c))
    n = len([p for p in P if p[0] not in ("clk", "rst_n")])
    (vw / "insertion_provisional.json").write_text(json.dumps({c: {"boundary": {"n": n, "min": INS[c] - 20, "mean": INS[c], "max": INS[c] + 20, "spread": 40.0}} for c in INS}
        | {"source": "PROVISIONAL HARD-S81-DSDV-1 11-13: xrt1 RF-J signed insertion (329.78 / 258.88) as the stand-in; replaced by the signed xs4 kit"}))
    import core_pins_gen as CP
    j, size = CP.table(MOD, str(vw / (MOD + ".lef")))
    assert size == (W, H) and len(j["pins"]) == len(P) == 4365, (size, len(j["pins"]))
    j["source"] = "HARD-S81-DSDV-1 11-13: xs4 hard-core LEF contract (kit io.tcl exact pins), xs4_core_contract_1113.py"
    json.dump(j, open("physical/die_plan/s81/inputs/core_pins/%s.json" % MOD, "w"), indent=0)
    print("pins", len(P), "span", P[0][2], P[-1][2], "pinhash", j["pinhash"])


if __name__ == "__main__":
    main()
