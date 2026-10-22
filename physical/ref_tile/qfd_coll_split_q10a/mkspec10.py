# SQ-C2-COLL 10-21: q10a MAIN / q10b FALLBACK from q9a / q9b (PD-AUDIT C3 MUST-DO): W/E buses spread over the full faces
# (<= 2 signal pins/um), ordered so every pin-flop -> pin-flop hop is <= 405 um by construction. Outline/macros unchanged.
import json, os, shutil, sys
R = sys.argv[1] + "/physical/ref_tile"
M = 5.4   # corner margin (um) off the N/S corners
# bottom -> top. W: outputs sx2, sx1 low (fed from internal pf/hi/lo regs, near S face sx0); SerDes inputs sr2, sr1 high
# (their od_q capture-path flops sit on the N face). E: ur (from the xr ring, flexible), dp (-> lo/hi, flexible),
# dr (-> od_q on N), up (<- ir_q on N) at the top.
ORDER = {"W": ["sx2_data", "sx1_data", "sr2_data", "sr1_data"], "E": ["ur_data", "dp_data", "dr_data", "up_data"]}
def mk(base, tag, why):
    s = json.load(open(f"{R}/qfd_coll_split_{base}/spec.json"))
    H = s["outline"]["h"]; L = (H - 2 * M) / 4
    rng = {}
    for f, ports in ORDER.items():
        for i, p in enumerate(ports):
            rng[p] = [round(M + i * L, 2), round(M + (i + 1) * L, 2)]
    name = f"qfd_coll_split_{tag}"
    s["name"] = name; s["pin_ranges"] = rng
    s["pin_hook_before_flops"] = [f"physical/ref_tile/{name}/native_release_tie.tcl"]
    j = s["job"]; j["tag"] = tag; j["owner"] = "SQ-C2-COLL"; j["branch"] = "claude/sq-c2-coll-1021"
    j["purpose"] = f"SQ-C2-COLL Q leaf {tag}: {why}"
    s["structural_change"] = (f"PD-AUDIT C3 (owner 10-21): {base} W/E faces carried 512 bus pins (558 counted) in 127.7 um (4.4/um, 46% of "
        f"the face). Fix: {why}")
    os.makedirs(f"{R}/{name}", exist_ok=True)
    for f in os.listdir(f"{R}/qfd_coll_split_{base}"):
        if f in ("gate_result.json", "gate_layout", "source_binding_history", "README.md", "spec.json", "mkspec9.py"): continue
        p = f"{R}/qfd_coll_split_{base}/{f}"
        if os.path.isfile(p): shutil.copy(p, f"{R}/{name}/{f}")
    json.dump(s, open(f"{R}/{name}/spec.json", "w"), indent=1)
    print(name, s["outline"], "L", round(L, 2), "pins/um", round(128 / L, 2)); print("  ", rng)
mk("q9a", "q10a", "q10a MAIN = q9a outline 248.40x276.48 + the same 3 free-standing SRAM columns / >=20-um channels; W/E 128-bit "
   "buses spread over the full face 5.4..271.08 um (66.4 um each, 1.93 signal pins/um), ordered bottom->top W sx2,sx1,sr2,sr1 / "
   "E ur,dp,dr,up so the face-anchored pin flops reach their N-face partners (od_q, ir_q) in <= 387 um (q9 order: up_data 451 um, "
   "sr1 419 um). RTL/pins/clock/reset/N-S faces unchanged; zero cycles.")
mk("q9b", "q10b", "q10b FALLBACK = q9b taller outline 239.76x285.12 (central 30-um W-E band, halo 8.64) + 3 free-standing SRAM "
   "columns; W/E buses spread over 5.4..279.72 um (68.6 um each, 1.87 signal pins/um), same N-facing order (worst pin-flop hop "
   "382 um). RTL/pins/clock/reset unchanged; zero cycles.")
