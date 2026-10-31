"""DIE-QC-51 last QC event item (8): bind the SIGNED BTAB P8eco form (qfd_dv_s8x_btab) in sle_su_c + slw_su_c__*.

COORD 18:54 option (a) (QC-RP1-1 ASK 18:47 / DIE-QC-50 DECISION 18:48): the plan_qc49/50 core is the unqualified
aspect1713 form (354.24x259.2, pincmp 0/1318 vs the signed DB); the signed P8eco DB (DIE-QC-50 18:46, epyc2
die-qc-50/btab/P8eco: TT setup +306.81, FF hold +7.44, DRC 0, LEC EQUIVALENT 7251/7251) is 293.76x155.52 with the
f3b pins (1317/1318 identical) and ck at its routed DEF location (146.892, 77.76, centre pin).
Changes per type: hard core outline_um + pins_file + note; origin_um KEPT (the smaller core fits inside the old
footprint at the same lower-left corner); dependents re-derived from the new pins:
  * clock.taps[u_suvm_u_vm8q_u_bt.ck].xy = origin + ck pin + track offset (same rule as the stored value:
    old xy 842.424,380.214 == 665.28+177.132+0.012, 380.16+0.042+0.012), insertion_ps / insertion_ff_ps = the signed
    DB's own pin_flop_mean clock latency (signoff TT 283.55 / FF 230.45 ps; 12.5 early tap from the core's own view);
  * clock.landing_contract.collector_tree.core_resets[u_suvm_u_vm8q_u_bt].pin_um/xy follow the rst_n pin
    (xy keeps the stored 4.374-um drop below the pin); tap index kept (re-derived by the collector tree tools).
apply(raw, root) edits raw in place and returns a JSON-serialisable report."""
import json
from pathlib import Path

INST, MOD = "u_suvm_u_vm8q_u_bt", "qfd_dv_s8x_btab"
PINS = "cores/su/qfd_dv_s8x_btab_pins_p8eco.json"
OUTLINE = [293.76, 155.52]
INS_TT, INS_FF = 283.6, 230.4
NOTE = ("su_c leaf hard core = SIGNED BTAB P8eco form (DIE-QC-50 18:46: TT +306.81 / FF hold +7.44 / DRC 0 / LEC EQ 7251; "
        "epyc2 die-qc-50/btab/P8eco 6_final.def pins); bound by COORD 18:54 option (a) in the last QC event (DIE-QC-51); "
        "re-sign at the f-qc tag before count")
PR = "physical/die_plan/qwen_compute/plan_of_record"


def apply(raw, root):
    pins = {p["name"]: p for p in json.loads((Path(root) / PR / PINS).read_text())["pins"]}
    rep = dict(pins_file=PINS, n_pins=len(pins), outline_um=OUTLINE, types={})
    for tn, t in raw["partition_types"].items():
        hc = [h for h in t.get("hard_cores", []) if h.get("inst") == INST and h.get("module") == MOD]
        if not hc:
            continue
        h = hc[0]
        ox, oy = h["origin_um"]
        tx, ty = h.get("track_offset_um", [0.0, 0.0])
        ch = []
        ch.append(dict(key="hard_cores.outline_um", old=h["outline_um"], new=OUTLINE))
        ch.append(dict(key="hard_cores.pins_file", old=h["pins_file"], new=PINS))
        h["outline_um"], h["pins_file"], h["note"] = list(OUTLINE), PINS, NOTE
        ck = pins["ck"]
        for tap in t.get("clock", {}).get("taps", []):
            if tap.get("name") == f"{INST}.ck":
                new = [round(ox + ck["x"] + tx, 3), round(oy + ck["y"] + ty, 3)]
                ch.append(dict(key="clock.taps[ck].xy", old=tap["xy"], new=new))
                ch.append(dict(key="clock.taps[ck].insertion_ps/ff", old=[tap.get("insertion_ps"), tap.get("insertion_ff_ps")],
                               new=[INS_TT, INS_FF]))
                tap["xy"], tap["insertion_ps"], tap["insertion_ff_ps"] = new, INS_TT, INS_FF
                tap["budget_owner"] = ("DIE-QC-51 EARLY TAP: own signed view P8eco pin_flop_mean clock latency "
                                       "(signoff.json TT 283.55 / FF 230.45 ps, routed SPEF)")
        rs = pins["rst_n"]
        lc = t.get("clock", {}).get("landing_contract", {})
        for cr in (lc.get("collector_tree") or {}).get("core_resets", []):
            if cr.get("inst") == INST and cr.get("pin") == "rst_n":
                drop = round(cr["pin_um"][1] - cr["xy"][1], 3)
                pin_um = [round(ox + rs["x"] + tx, 3), round(oy + rs["y"] + ty, 3)]
                xy = [pin_um[0], round(pin_um[1] - drop, 3)]
                ch.append(dict(key="landing_contract.collector_tree.core_resets[rst_n]", old=[cr["pin_um"], cr["xy"]], new=[pin_um, xy]))
                cr["pin_um"], cr["xy"] = pin_um, xy
        rep["types"][tn] = ch
    return rep


if __name__ == "__main__":
    import argparse, hashlib
    ap = argparse.ArgumentParser(); ap.add_argument("plan"); ap.add_argument("--out", required=True); ap.add_argument("--report", required=True)
    a = ap.parse_args()
    root = Path(__file__).resolve().parents[3]
    P = json.load(open(a.plan)); r = apply(P, root)
    open(a.out, "w").write(json.dumps(P, indent=1) + "\n")
    r["dst_sha256"] = hashlib.sha256(open(a.out, "rb").read()).hexdigest()
    open(a.report, "w").write(json.dumps(r, indent=1) + "\n")
    print(json.dumps(r, indent=1))
