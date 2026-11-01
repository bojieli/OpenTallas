#!/usr/bin/env python3
"""DIE-S81-47 11-01 (COORD 08:2x): parent receipt of Codex S81 QBS20 (dsfd_qbank_S cqS20, LOCAL SIGNED, post-route
LEC EQ 1813/1813, io_hold NEEDS_PARENT) and CFG7 (ot_s81_cfg7_seq cs7, SIGNED, post-route LEC EQ 648/648) views.

Lib-only plan event on the 104 + 104 hard_cores entries (26 col types): hard_cores[].lib -> the pinned actual views
under cores/views/<module>_{prov,signed}_1101/ (Codex pinned files codex/s81-parent1-1101@2dcebbf3db1: ETM TT/FF, signoff.json,
lec_routed.json, clock_contract.json).  dsfd_qbank_S also takes the routed abstract LEF of the same run (60.48 x 25.92 =
the plan outline_um; the legacy LEF it replaces is 60.48 x 17.28; pin set identical 1212/1212).  Exact port-bit match
of each new lib vs the plan pin table is asserted (VDD/VSS excl).  Nothing else changes (asserted).
usage (repo root): delta_rcpt_qbs_cfg7_1101.py PLAN_IN PLAN_OUT REPORT.json"""
import copy
import json
import re
import sys
from pathlib import Path
import importlib.util

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / "tools" / "die_plan"))
import compact_plan as CP  # noqa: E402

spec = importlib.util.spec_from_file_location("d", "physical/die_plan/s81/delta_child_lib_1030.py")
D = importlib.util.module_from_spec(spec); spec.loader.exec_module(D)

V = "physical/die_plan/s81/cores/views"
NEW = {
    "dsfd_qbank_S": dict(lib=f"{V}/dsfd_qbank_S_prov_1101/dsfd_qbank_S_tt.lib",
                         lef=f"{V}/dsfd_qbank_S_prov_1101/dsfd_qbank_S.lef"),
    "ot_s81_cfg7_seq": dict(lib=f"{V}/ot_s81_cfg7_seq_signed_1101/ot_s81_cfg7_seq_tt.lib"),
}


def main():
    src, dst, rp = sys.argv[1:4]
    text = Path(src).read_text()
    raw = json.loads(text)
    orig = copy.deepcopy(raw)
    rep = {}
    changed = set()
    for m, new in NEW.items():
        got = D.lib_bits(new["lib"])
        ents = [(tn, h) for tn, t in raw["partition_types"].items() for h in (t.get("hard_cores") or [])
                if h.get("module") == m]
        tables = {json.dumps(sorted(D.plan_bits(h) or [])) for _, h in ents}
        assert len(tables) == 1, (m, len(tables))
        want = set(json.loads(tables.pop()))
        assert got == want, (m, len(got), len(want))
        old = sorted({(h.get("lib"), h.get("lef")) for _, h in ents})
        for tn, h in ents:
            h.update(new)
            changed.add(tn)
        rep[m] = dict(entries=len(ents), types=len({tn for tn, _ in ents}), bits=len(got), match="EXACT",
                      old=old, new=new)
    for k in raw:
        if k != "partition_types":
            assert raw[k] == orig[k], k
    for tn, t in raw["partition_types"].items():
        a, b = copy.deepcopy(t), orig["partition_types"][tn]
        for h in a.get("hard_cores") or []:
            if h.get("module") in NEW:
                h.pop("lib", None); h.pop("lef", None)
        bb = copy.deepcopy(b)
        for h in bb.get("hard_cores") or []:
            if h.get("module") in NEW:
                h.pop("lib", None); h.pop("lef", None)
        assert a == bb, tn
    for tn in sorted(changed):
        mm = re.search(r'^  "' + re.escape(tn) + r'": ', text, re.M)
        _, j = json.JSONDecoder().raw_decode(text, mm.end())
        text = text[:mm.end()] + CP._d(raw["partition_types"][tn], 2) + text[j:]
    assert json.loads(text) == raw
    Path(dst).write_text(text)
    rep["_summary"] = dict(types_changed=len(changed), types=sorted(changed))
    Path(rp).write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps(rep)[:1500])


if __name__ == "__main__":
    main()
