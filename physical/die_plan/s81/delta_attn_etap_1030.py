#!/usr/bin/env python3
"""DIE-S81-36/ATTNTAP one-block clock-entry fix (COORD 14:40 GEOM-80 PASS-COND attn rt22, DIE-S81-36 ruling (a)):
the attn_hcore rt22 view (S81-CORES-KITS-5, regional taps 2x2, epyc2 s81ck5/kits/ot_s81c_attn_hcore_rt22) measures a
clk pin->register latency of 351-356 ps (tap means; all 28022 sinks mean 354.2, min 346.6, max 364.5; CTS-only,
placement RC) against the 250+-20 common band.  METHODOLOGY 12.3 v5.0: the parent balances it with an EARLY core tap.
For each of the 16 svc_* types holding ot_s81c_attn_hcore (64 instances each, all R0, clock.taps == [] today):
  clock.core_taps = "early" and clock.taps = one kind 'core' row per instance, name '<inst>.clk',
  xy = origin + pins_file clk (78.828, 0.24) (R0; the rt22 view keeps this S-face pin, = plan LEF RECT),
  insertion_ps 354.2 / insertion_ff_ps 286.9 (= gen_phys FF_TT_INSERTION_RATIO 0.81 x TT; no FF view yet),
  budget_owner 'parent_budget ...' (the existing early-tap form, e.g. leaf__t1 u_lf.u_ve.u_m.clk).
Only those two clock fields of those 16 types change (textual insert, rest of the plan byte-identical).
usage (repo root): delta_attn_etap_1030.py PLAN   (rewrites PLAN in place; a second run refuses)"""
import json
import re
import sys

LEF = "physical/die_plan/s81/cores/svc/ot_s81c_attn_hcore.lef"
PIN = (78.828, 0.24)
TT, FF = 354.2, 286.9
OWNER = ("parent_budget pin_register_mean OpenSTA placement-RC on CTS-only rt22 probe epyc2 "
         "s81ck5/kits/ot_s81c_attn_hcore_rt22 ot_rt_ck_cts_tt.tsv (NOT SIGNED, not extracted; all 28022 sinks, "
         "tap means 351-356); FF 286.9 = 0.81 x TT DERIVED, UNCHECKED (no FF view); DIE-S81-36/ATTNTAP 2026-10-30; replace with the "
         "SIGNED routed means at attn sign-off (GEOM-81 routed recheck)")
NOTE = ("early core tap (12.3 v5.0) for attn_hcore rt22 (COORD 14:40 GEOM-80 PASS-COND, DIE-S81-36 ruling (a)); "
        "xy = pins_file clock pin clk transformed (R0)")


def main():
    pp = sys.argv[1]
    text = open(pp).read()
    plan = json.loads(text)
    pt = plan["partition_types"]
    want = json.loads(json.dumps(plan))
    types = [tn for tn in pt if any(c["lef"] == LEF for c in pt[tn].get("hard_cores", []))]
    assert len(types) == 16, types
    lef = open(LEF).read()
    assert "RECT 78.804 0.000 78.852 0.480 ;" in lef.split("PIN clk", 1)[1].split("END clk", 1)[0]
    n = 0
    for tn in types:
        ck = want["partition_types"][tn]["clock"]
        assert ck["taps"] == [] and "core_taps" not in ck, (tn, "already has taps")
        rows = []
        for c in pt[tn]["hard_cores"]:
            if c["lef"] != LEF:
                continue
            assert c["orient"] == "R0", (tn, c["inst"], c["orient"])
            x = round(c["origin_um"][0] + PIN[0], 4)
            y = round(c["origin_um"][1] + PIN[1], 4)
            rows.append(dict(name=c["inst"] + ".clk", kind="core", xy=[x, y], insertion_ps=TT, insertion_ff_ps=FF,
                             budget_owner=OWNER, note=NOTE))
        assert len(rows) == 64, (tn, len(rows))
        n += len(rows)
        # rebuild the clock dict with core_taps placed right before taps (same key order as e.g. col_h10_r0_p4__t1)
        new = {}
        for k, v in ck.items():
            if k == "taps":
                new["core_taps"] = "early"
                new["taps"] = rows
            else:
                new[k] = v
        want["partition_types"][tn]["clock"] = new
        m = re.search(r'^  "' + re.escape(tn) + r'": ', text, re.M)
        _, end = json.JSONDecoder().raw_decode(text, m.end())
        i = text.find('"clock": ', m.end(), end)
        j = text.find('"taps": []', i, end)
        assert i > 0 and j > 0, tn
        ls = text.rfind("\n", 0, j) + 1
        ind = text[ls:j]
        assert ind.strip() == "", tn
        body = json.dumps(rows, indent=1).replace("\n", "\n" + ind)
        text = text[:j] + '"core_taps": "early",\n' + ind + '"taps": ' + body + text[j + len('"taps": []'):]
    assert json.loads(text) == want, "unexpected plan edit"
    open(pp, "w").write(text)
    print(len(types), "types,", n, "core tap rows")


if __name__ == "__main__":
    main()
