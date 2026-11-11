#!/usr/bin/env python3
"""S81 plan event T51-NETSRC-1110 (DIE-S81-85 sub-lane; proposed by the sub-lane, accepted by DIE-S81-85 on technical
grounds 11-10): the soft station type slice_station__t51 (T51-SPLIT-1109 native split, hard children
s81p_slice_station__t51_ot_s81_station_t51_native_w / _native_e) is kitted from its split parent netlist.

Why: the two children exist only as cuts of the mapped t51 netlist (station_split_1106, yosys submod of the B51 mapped
design + clean_abi pNNNNN ports; the signed E view and the W v3 form are built on that ABI).  The bound RTL of the type
is the unsplit station (no native instance), so the kit placed both children by names its netlist did not have
(KIT_PREFLIGHT macro_instances FAIL, kw43-wave-1109n attempt_6 / attempt_7).  In the split parent netlist each child
instance is named after its module, so the hard_cores inst values (= module names) are the true instance paths there;
they stay unchanged.

Edit (one key, text in place, asserted json-equal to the object edit):
  partition_types.slice_station__t51.kit_source = {parent_netlist: station_split_1106/t51_parent_split.v.gz,
      sha256: content sha256 of the netlist text (pinned; gen.py phys and kit_preflight refuse any other content),
      lec_receipt: the function proof (today's bound t51 RTL == parent + child_w + child_e, tools/die_plan/lec.py)}
  Nothing else changes: ports (137 = 137, names / directions / widths equal to the type wrapper), pins, clocks, taps,
  resets, hard_cores, cycles (0 added).  Types without kit_source are untouched (gen_phys.stage_kit_source opt-in).
    python3 -I physical/die_plan/s81/delta_t51_netsrc_1110.py PLAN REPORT [LEC_RECEIPT]      (cwd = repo root)
"""
import copy
import gzip
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path[:0] = ["physical/die_plan/s81"]
from delta_romq_split_1106 import spans  # noqa: E402

EV = "T51-NETSRC-1110 DIE-S81-85 sub-lane"
TN = "slice_station__t51"
TM = "s81p_slice_station__t51"
NET = "physical/die_plan/s81/station_split_1106/t51_parent_split.v.gz"
NET_SHA = "1ab8a4717eb33279788cef6bc8a5f2d8cdf171a3ba77214a7c297fbf97d907a8"
KIDS = [TM + "_ot_s81_station_t51_native_w", TM + "_ot_s81_station_t51_native_e"]


def ports(text):
    text = re.sub(r"//[^\n]*", "", text)
    out = {}
    for d, w, n in re.findall(r"^\s*(input|output|inout)\s+(?:wire\s+)?(\[\d+:\d+\]\s*)?\\?(\w+)\s*[;,)]?\s*$", text, re.M):
        w = (w or "").strip()
        out[n] = (d, "" if w == "[0:0]" else w)
    return out


def main():
    plan_p, rep_p = map(Path, sys.argv[1:3])
    lec = sys.argv[3] if len(sys.argv) > 3 else None
    text = plan_p.read_text()
    P = json.loads(text)
    t = P["partition_types"][TN]
    assert t["module"] == TM and not t.get("kit_source"), "event applied already / wrong type"
    assert [c["inst"] for c in t["hard_cores"]] == KIDS and all(c["inst"] == c["module"] for c in t["hard_cores"])
    net = gzip.open(NET, "rt").read()
    assert hashlib.sha256(net.encode()).hexdigest() == NET_SHA, "parent netlist content"
    mods = re.findall(r"^\s*module\s+\\?(\w+)", net, re.M)
    assert mods == [TM], mods
    for k in KIDS:
        assert re.search(r"^\s*" + k + r"\s+" + k + r"\s*\(", net, re.M), ("child instance", k)
    rec = dict(parent_netlist=NET, sha256=NET_SHA,
               lec_receipt=lec or "PENDING: tools/die_plan/lec.py bound t51 RTL vs parent + child_w + child_e",
               note=(f"{EV}: the kit synthesises this hash-pinned split parent netlist (T51-SPLIT-1109 children are "
                     "cuts of the mapped t51 netlist, station_split_1106); child instances are named after their "
                     "modules, so hard_cores inst = module is the netlist path; children = LEF / liberty black boxes"))
    sp = spans(text)
    a, b = sp[("partition_types", TN, "hard_cores")]
    line0 = text.rfind("\n", 0, a) + 1
    key0 = text.rfind('"hard_cores"', 0, a)
    ind = text[line0:key0]
    out = text[:b] + ",\n" + ind + '"kit_source": ' + json.dumps(rec) + text[b:]
    Q = json.loads(out)
    want = copy.deepcopy(P)
    want["partition_types"][TN]["kit_source"] = rec
    assert Q == want, "text edit != object edit"
    plan_p.write_text(out)
    report = dict(event=EV, type=TN, kit_source=rec, netlist_modules=mods, child_instances=KIDS,
                  netlist_ports=len(ports(net)),
                  plan_sha256_before=hashlib.sha256(text.encode()).hexdigest(),
                  plan_sha256_after=hashlib.sha256(out.encode()).hexdigest())
    rep_p.write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps(dict(type=TN, before=report["plan_sha256_before"][:16], after=report["plan_sha256_after"][:16])))


if __name__ == "__main__":
    main()
