#!/usr/bin/env python3
"""DIE-HEAD-47 plan event l47k (COORD 03:0x ruling, ASK option A APPROVED): count-aligned K re-plan on the RECORD die clock.

Root cause: the HEAD count-aligned bind (codex-head-start-0828/hk5_leaf2, K planned 08-28 on the hk5 leaf clock) was never
re-planned on the record die clock l46aa405; HEAD die STA (12.25, nominal, routed deltas) found 11 crossings below the
100-ps ring need (sp1->sp2 slot_read -53.5 TT).  count_align_plan --sta-proof on the record proof (caplan/plan.json, same
tool/flags as hk5_leaf2 but nominal 12.24b + FF 342) gives lat_cycles 3 -> 4 on exactly those 11 ports and keeps every other
port's lat_cycles.  Its start tree is NOT adopted (the record clock carries no START loads; START tree stays hk5_leaf2), so
the change is expressed in the hk5_leaf2 frame (unchanged n0 / start offsets): K_rtl += 1 (= +1 latency cycle, accepted by
COORD), bind L_lo/L_hi += T, sched_lat += 1.  RTL = parent strap tie strap_ca_k_<dst bus> on the dst instance only.

  make_l47k.py SRC_DIR(head_source_l47) BIND(hk5_leaf2 bind.json) NEWPLAN(caplan/plan.json) OUT_DIR TOOLS(main tools/)
The bind K is the logical K; the tie = (K - R + W) mod 64 (count_align_bind.strap_ties).  The sidecar count_aligned
table of head_source_l47 is updated with the same K/sched_lat (its K equals the hk5_leaf2 bind on all 427 ports, checked).
"""
import json, re, shutil, sys
from pathlib import Path

src, bindf, newf, out, tools = map(Path, sys.argv[1:6])
sys.path.insert(0, str(tools / "die_plan"))
import count_align_bind as CAB  # strap = K - reader_start_depth(dst type) + writer_start_depth(src type, bus)
bind = json.loads(bindf.read_text()); new = {r["port"]: r for r in json.loads(newf.read_text())["crossings"]}
T = float(bind["period_ps"])
plan = json.loads((src / "source_plan.json").read_text()); link = {p["id"]: p for p in plan["ports"]}
ptype = {p["name"]: p["type"] for p in plan["partitions"]}
side = json.loads((src / "source_sidecar.json").read_text())
assert all(side["count_aligned"]["ports"][p]["K"] == b["K"] and side["count_aligned"]["ports"][p]["sched_lat"] == b["sched_lat"]
           for p, b in bind["ports"].items()), "sidecar K != bind K"
def off(p):
    s_, d_ = link[p]["src"], link[p]["dst"]
    return -CAB.reader_start_depth(plan, ptype[d_["part"]]) + CAB.writer_start_depth(plan, ptype[s_["part"]], s_["bus"])
chg = sorted(p for p, b in bind["ports"].items() if p in new and int(new[p]["lat_cycles"]) > int(b["sched_lat"]))
assert all(int(new[p]["lat_cycles"]) == int(bind["ports"][p]["sched_lat"]) + 1 for p in chg), "only +1 cycle handled"
assert not [p for p, b in bind["ports"].items() if p in new and int(new[p]["lat_cycles"]) < int(b["sched_lat"])]
if out.exists(): shutil.rmtree(out)
shutil.copytree(src, out)
top = (out / "s81_head_top.sv").read_text()
delta = []
for p in chg:
    b = bind["ports"][p]; k0 = int(b["K"]); k1 = k0 + 1
    assert 0 <= k1 < 64, (p, k1)
    inst, bus = link[p]["dst"]["part"], link[p]["dst"]["bus"]
    m = re.search(r"\n    (\w+) %s \(\n(.*?)\n    \);" % re.escape(inst), top, re.S)
    assert m, (p, inst)
    body = m.group(2); pin = "strap_ca_k_%s" % bus
    pm = re.search(r"\.%s\(6'b([01]{6})\)" % pin, body)
    assert pm and int(pm.group(1), 2) == (k0 + off(p)) % 64, (p, inst, pin, pm and pm.group(1), k0, off(p))
    nb = body.replace(pm.group(0), ".%s(6'b%s)" % (pin, format((k1 + off(p)) % 64, "06b")))
    top = top[:m.start(2)] + nb + top[m.end(2):]
    b.update(K=k1, sched_lat=int(b["sched_lat"]) + 1, L_lo_ps=round(b["L_lo_ps"] + T, 1), L_hi_ps=round(b["L_hi_ps"] + T, 1),
             margin_lo_ps=round(b["margin_lo_ps"] + T, 1), margin_hi_ps=round(b["margin_hi_ps"] - T, 1), l47k="K+1 (record-clock re-plan)")
    side["count_aligned"]["ports"][p].update(K=k1, sched_lat=b["sched_lat"])
    delta.append(dict(port=p, tie_old=(k0 + off(p)) % 64, tie_new=(k1 + off(p)) % 64, src=b["src"], dst=b["dst"], instance=inst, strap=pin, K_old=k0, K_new=k1,
                      lat_old=b["sched_lat"] - 1, lat_new=b["sched_lat"], replan_L_lo_ps=new[p]["L_lo_ps"], replan_L_hi_ps=new[p]["L_hi_ps"]))
(out / "s81_head_top.sv").write_text(top)
(out / "source_sidecar.json").write_text(json.dumps(side, indent=1) + "\n")
(out / "bind_l47k.json").write_text(json.dumps(bind, indent=1) + "\n")
(out / "l47k_delta.json").write_text(json.dumps(dict(event="l47k", ports=delta, n=len(delta)), indent=1) + "\n")
print(json.dumps(dict(changed=len(delta), ports=[(d["port"], d["instance"], d["strap"], d["K_old"], d["K_new"]) for d in delta])))
