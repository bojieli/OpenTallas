#!/usr/bin/env python3
"""STEWARD-HBMe/HC 10-23: qhub kit hbme_hcqh_m1 (plan lanes/STEWARD-HBM.md [STEWARD-HBMe/HC] PLAN ot_hbm_hc_qhub_static).
Base = TILE-FLOW hbm_hcq_hub_tf1 (c12b RTL SAFE 2 + LAND 7, hooks, face fence).  Changes: faces = the release die r18h5
(die_qhub.lef) per bundle owner, re-spread to <= 5/um (die notice: lg_rr E -> N-east, as the c12 die; cfg/desc all W);
qtree16 column centred on the s_i span; programme SRAM MY so rd_out faces the hc_q band."""
import copy, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RT = ROOT / "physical/ref_tile"
W = H = 734.4

# (port, width) packed proportionally into [a, b] on a face (S->N on W/E, W->E on N/S)
FACES = {
    "W": [((("bd_v", 1), ("bd_ss", 1), ("bd_nv", 7), ("bd_wa", 10), ("bd_xa", 10), ("wc_w", 13), ("rstb_w", 1),
            ("wf_w", 1), ("tgt", 8)), 112.0, 138.0),
          ((("rst_n", 1),), 140.0, 141.0),
          ((("clk_t", 4),), 142.0, 147.0),
          ((("s_i", 2049),), 150.0, 600.0),
          ((("xb_v", 1), ("xb_beat", 2), ("xb_d0", 256)), 604.0, 658.0),
          ((("cfg_v", 1), ("cfg_target", 8), ("cfg_addr", 12), ("cfg_data", 256), ("desc_v", 1), ("desc_base", 12),
            ("desc_limit", 13), ("desc_loops", 16), ("launch_v", 1), ("configured", 1), ("hcq_fault", 1),
            ("program_active", 1)), 660.0, 731.0)],
    "N": [((("xb_v_n", 1), ("xb_beat_n", 2), ("xb_d1", 256), ("xb_d2", 256), ("xb_d3", 256), ("wc_n", 13),
            ("rstb_n", 3), ("wf_n", 3)), 40.0, 285.0),
          ((("lg_rr", 2056), ("lg_w_done", 8)), 290.0, 731.0)],
    "E": [((("lg_wq", 2248),), 3.0, 470.0),
          ((("lg_rq", 136), ("result_position", 3), ("gather_done", 1), ("program_done", 1), ("residual_done", 1)),
           474.0, 508.0),
          ((("xb_v_e", 1), ("xb_beat_e", 2), ("xb_d4", 256), ("wc_e", 13), ("rstb_e", 1), ("wf_e", 1)), 560.0, 640.0)],
    "S": [((("xb_v_s", 1), ("xb_beat_s", 2), ("xb_d5", 256), ("xb_d6", 256), ("xb_d7", 256), ("wc_s", 13),
            ("rstb_s", 3), ("wf_s", 3)), 40.0, 300.0),
          ((("clk", 1),), 330.0, 331.0),
          ((("d_v", 1), ("d_ss", 1), ("d_nv", 7), ("d_wa", 10), ("d_xa", 10), ("i_v", 1), ("i_kind", 1), ("i_slot", 2),
            ("i_lo", 5), ("i_w", 5), ("i_cnt", 12), ("i_word", 10), ("ps_v", 1), ("ps", 32), ("ps_f", 1),
            ("eng_fault", 1), ("gathered_mix_v", 1), ("gathered_mix_row", 5), ("gathered_mix_pos", 3),
            ("gathered_mix_data", 32), ("result_v", 1)), 340.0, 425.0),
          ((("result", 768),), 430.0, 731.0)],
}


def pins_ranges():
    pins, pr, dens = {}, {}, {}
    for f, groups in FACES.items():
        pins[f] = []
        for ports, a, b in groups:
            tot = sum(w for _, w in ports)
            x = a
            for p, w in ports:
                e = x + (b - a) * w / tot
                pins[f].append(p)
                pr[p] = [round(x, 3), round(e, 3)]
                x = e
            dens[f"{f}:{ports[0][0]}"] = round(tot / (b - a), 2)
    return pins, pr, dens


def m1():
    s = copy.deepcopy(json.loads((RT / "hbm_hcq_hub_tf1/spec.json").read_text()))
    tf_ports = {p for v in s["pins"].values() for p in v}
    pins, pr, dens = pins_ranges()
    mine = {p for v in pins.values() for p in v}
    assert mine == tf_ports, (sorted(tf_ports - mine), sorted(mine - tf_ports))
    s["name"] = "hbme_hcqh_m1"
    s["pins"], s["pin_ranges"] = pins, pr
    s.pop("slot_change_request", None)
    L = 43.2
    s["children"] = [{"view": "physical/ref_tile/hbm_hcq_tree16_c1/views/ot_hbm_hc_qtree16_static", "count": 1,
                      "inst": f"*g_qt?{c}?.u_t", "at": [L, round(3 * L + c * 3 * L, 3)], "orient": "R0"}
                     for c in range(4)]
    s["macros"] = [{"view": "physical/asap7_memory_macros_v2/ot_sram_1r1w_1024x256_m2_r2c2", "count": 1,
                    "at": [259.2, 332.64], "at_exact": True, "orient": "MY", "inst": "u_q.g_qcal.programme.u_program"}]
    s["fill_reason"] = {"pin_bound": "9.9k face pins on the die-fixed 734.4 hole of the HC bank ring (r18h5); content "
                        "10.6k um2 std + 4 x 12.6k qtree16 + 12.3k SRAM; pins re-spread to <= 4.8/um per bundle"}
    s["die_notice"] = ("STEWARD-HBMe/HC 10-23: faces = r18h5 die_qhub.lef bundle faces except lg_rr (+lg_w_done) E -> N "
                       "x 290-731 (E face 4.7k bits = 6.6/um over the cap; as the c12 die) and cfg_v/cfg_target/desc_v/"
                       "result_position etc. joined their bundles; every bundle spread <= 4.8/um: " + json.dumps(dens))
    s["structural_change"] = ("STEWARD-HBMe/HC 10-23 connectivity split of the hub on the release die faces: W = qtree16 "
                              "column centred on s_i (pins facing their W bundle) + b0 beat/cfg pin registers; N/S/E = "
                              "LAND bank-face beat registers at their bank spans; E = lg_wq/lg_rq pin registers, N-east = "
                              "lg_rr; centre = hc_q + x_wave register + programme SRAM (MY, rd_out toward hc_q); S = "
                              "result pin registers + qcen ctrl/ps beside their pins.  RTL = c12b SAFE 2 + LAND 7 (contract "
                              "change C-QHUB-HC1, named in the plan).")
    s["purpose"] = s["structural_change"][:400]
    s["description"] = s["structural_change"]
    s["outline_reason"] = "die-fixed: exact 734.4 um hole of the HC bank ring (r18h5); faces re-spread (die notice)"
    s["job"] = dict(s["job"], owner="STEWARD-HBMe/HC", branch="claude/hbme-hc-1023", tag="m1",
                    purpose=s["purpose"])
    kd = RT / s["name"]
    kd.mkdir(exist_ok=True)
    (kd / "spec.json").write_text(json.dumps(s, indent=1) + "\n")
    print(kd.name, dens)


if __name__ == "__main__":
    m1()
