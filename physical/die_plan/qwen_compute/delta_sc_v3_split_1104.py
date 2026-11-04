#!/usr/bin/env python3
"""DIE-QC-68/FORMS 11-04: SC HARD1 event form on sle_sc_v3 only (623k cells flat). Same delta as delta_sc_hard1_1102.py /
delta_sc_ft_1102.py (chain-end leaf qfd_dv_s5_sc2_leaf_dn0 as a hard core, source unchanged, ft stations off the core);
one pilot before the other eight SC types. usage: delta_sc_v3_split_1104.py PLAN_IN PLAN_OUT REPORT.json"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import delta_sc_hard1_1102 as H  # noqa: E402
import delta_sc_ft_1102 as F  # noqa: E402

T = "sle_sc_v3"


def main():
    pin, pout, prep = sys.argv[1:4]
    raw = json.load(open(pin))
    t = raw["partition_types"][T]
    assert not t.get("hard_cores")
    hc = H.core(H.CE[T], None)
    t["hard_cores"] = [hc]
    ck = t["clock"]
    ck["core_taps"] = "early"
    xy = H.pin_xy(Path(pout).resolve().parent, hc, "ck")
    ck.setdefault("taps", []).append(dict(
        kind="core", name="u_core.ck", xy=xy, insertion_ps=H.TT, insertion_ff_ps=H.FF,
        budget_owner=f"parent_budget early tap {round(H.TT - 250.0, 1)} ps TT: ESTIMATE = {H.SRC}; re-measure from own kit view (12.28b)",
        note="sle_sc_v3 split pilot: early core tap at the SC core ck pin"))
    open(pout + ".s1", "w").write(json.dumps(raw) + "\n")
    F.SC = [T]
    sys.argv = [sys.argv[0], pout + ".s1", pout, prep]
    F.main()


if __name__ == "__main__":
    main()
