#!/usr/bin/env python3
"""PHY RE-FORM bench: build the NEW wrapper RTL exactly as the bind does after the plan event, from the CURRENT bound RTL.

bind.py order per type: (landing/localisation already in the bound text) -> reset.port_relays (reset_port_relays.apply)
-> write -> native_istations.materialize (kit_istations --apply inserts the planned OUT source stations before
u_bout_<bus>).  This script runs the same two library calls on the bound file, so the bench simulates the real RTL form.

usage: make_rtl.py PLAN TYPE BOUND.sv OUTDIR [--mutant d3_depth2|relay_on_bout]
  d3_depth2     : o_phy_Q__sN_piN_d3 gets 2 stations instead of 3 (one pi word split over lanes with unequal depth)
  relay_on_bout : a depth-6 reset relay drives u_bout_o_phy_Q__sN_fhN (an OBSERVED epoch released after it arrives;
                  depth <= 3 there is hidden by the station chain, which the bench also shows as equal)
Writes OUTDIR/<module>.sv (module renamed <module>_new) and OUTDIR/make_rtl.json.
"""
import copy
import json
import re
import sys
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[6] / "tools/die_plan"))
import native_istations  # noqa: E402
import reset_port_relays  # noqa: E402


def main(argv):
    mutant = None
    if "--mutant" in argv:
        i = argv.index("--mutant")
        mutant = argv[i + 1]
        del argv[i:i + 2]
    planf, tn, bound, outdir = argv
    out = Path(outdir).resolve()
    (out / "rtl").mkdir(parents=True, exist_ok=True)
    plan = json.loads(Path(planf).read_text())
    t = copy.deepcopy(plan["partition_types"][tn])
    if mutant == "d3_depth2":
        e = next(e for e in t["internal_stations"] if e.get("conn") == "bus:o_phy_Q__sN_piN_d3")
        e["regs_um"] = e["regs_um"][1:]
    elif mutant == "relay_on_bout":
        # an epoch released AFTER its stations deliver it (depth 6 > the 3 source stations + face register): observable
        t["reset"]["port_relays"].append(dict(name="mut", depth=6, sinks=["u_bout_o_phy_Q__sN_fhN"]))
    elif mutant is not None:
        raise SystemExit(f"unknown mutant {mutant}")
    txt = Path(bound).read_text()
    mod = re.search(r"^module\s+(\w+)", txt, re.M)[1]
    rec = []
    if t.get("reset", {}).get("port_relays"):
        txt, rec = reset_port_relays.apply(txt, t["reset"]["port_relays"])
    f = out / "rtl" / f"{mod}.sv"
    f.write_text(txt)
    lanes = [dict(oname=m[2], width=int(m[1]))
             for m in re.finditer(r"\bot_dp_ste?\s+#\(\.W\((\d+)\)\)\s+u_bout_(\w+)\s*\(", txt)]
    b = SimpleNamespace(types={tn: t}, ab={"internal_stations_types": [tn]}, by_type={tn: ["p"]},
                        out_bus={"p": lanes})
    native_istations.materialize(b, tn, f)
    new = f.read_text()
    new = re.sub(rf"^module\s+{mod}\b", f"module {mod}_new", new, count=1, flags=re.M)
    (out / f"{mod}.sv").write_text(new)
    receipt = json.loads((out / "native_internal_stations" / tn / "receipt.json").read_text())
    (out / "make_rtl.json").write_text(json.dumps(dict(type=tn, module=mod, mutant=mutant, port_relays=rec,
                                                       stations=receipt["entries"]), indent=1) + "\n")
    print(json.dumps(dict(type=tn, mutant=mutant, port_relays=len(rec),
                          stations={e["conn"]: e["planned"] for e in receipt["entries"]})))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
