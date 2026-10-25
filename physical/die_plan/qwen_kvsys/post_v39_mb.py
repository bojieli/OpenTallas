"""KV-FT v3.9 move MB (imported by post_v39_ft.py): OR fault chains run TOWARD their collector.

Each chain = nodes head (efault only) -> ... -> tail -> collector.  As built the head sits next to the hub (row 7) and
the tail at the die edge (row 0), so the tail lane returns over 7-9 partitions.  An OR chain's order is free: reversed,
row 0 is the head (sends its own efault), every other row ORs its efault with the chain, and row 7 (beside the hub row)
feeds the collector over one abutted face.  Hop windows / ft slots are reused (slot in/out faces swapped); the old tail
lane and its slots go.  hg chains land in hub_Eo / hub_Wo (new OR beside their efault, whose existing lane to hub_C then
carries the joined fault) instead of hub_C: hg_X_7 abuts hub_Eo/Wo, not hub_C.
"""
import re

import schema as S

OPP = {"N": "S", "S": "N", "E": "W", "W": "E"}


def chains(raw):
    out = []
    for q in ("EN", "ES", "WN", "WS"):
        out.append(dict(fam="hg", nodes=[f"hg_{q}_{k}" for k in range(7, -1, -1)],
                        new_coll=("hub_Eo" if q[0] == "E" else "hub_Wo"), new_coll_bus=f"i_fch_hg_{q}_q",
                        census_coll=("fchj_hub_Eo" if q[0] == "E" else "fchj_hub_Wo")))
        out.append(dict(fam="pc", nodes=[f"pc_{q}_{k}" for k in range(7, -1, -1)], new_coll=None))
    for h in ("N", "S"):
        out.append(dict(fam="pv", nodes=[f"pv_{h}_{k}" for k in (7, 5, 3, 1, 0)], new_coll=None))
    return out


def move_mb(raw, census, LOG):
    rows, mp = census
    gone = set()
    swapped = set()
    rev_lanes = set()
    hub_fch = {}
    for ch in chains(raw):
        ports = {x["id"]: x for x in raw["ports"]}
        lanes = {x["id"]: x for x in raw["lanes"]}
        parts = {x["name"]: x for x in raw["partitions"]}
        T = raw["partition_types"]
        nodes = ch["nodes"]

        def ends(l):
            ln = lanes[l]
            return ports[ln["ports"][0]], ports[ln["ports"][-1]]
        hops = []
        for a, b in zip(nodes, nodes[1:]):
            l = next(l for l in lanes if ends(l)[0]["src"]["part"] == a and ends(l)[1]["dst"]["part"] == b
                     and re.search(r"(fch|efault)", ends(l)[0]["src"]["bus"]))
            hops.append(l)
        tail = next(l for l in lanes if ends(l)[0]["src"]["part"] == nodes[-1]
                    and re.search(r"fch", ends(l)[0]["src"]["bus"]) and ends(l)[1]["dst"]["part"] not in nodes)
        coll_old = ends(tail)[1]["dst"]
        HEAD_OUT = ends(hops[0])[0]["src"]["bus"]          # o_efault_*
        FIRST_IN = ends(hops[0])[1]["dst"]["bus"]          # i_efault_* (old node 1)
        MID_OUT = ends(hops[1])[0]["src"]["bus"]           # o_fch_*
        MID_IN = ends(hops[1])[1]["dst"]["bus"]            # i_fch_*
        TAIL_OUT = ends(tail)[0]["src"]["bus"]
        assert TAIL_OUT == MID_OUT, (TAIL_OUT, MID_OUT)
        # collector port: the old tail lane's port that leaves nodes[0] (old head = new tail)
        tp = [ports[x] for x in lanes[tail]["ports"]]
        if ch["new_coll"]:
            cp = next(p for p in tp if p["src"]["part"] == nodes[0] and p["dst"]["part"] == ch["new_coll"])
            coll = dict(part=ch["new_coll"], bus=ch["new_coll_bus"])
        else:
            cp = next(p for p in tp if p["src"]["part"] == nodes[0])
            assert cp["dst"]["part"] == coll_old["part"], (tail, cp)
            coll = dict(coll_old)
        new_ports = [dict(cp, id=f"FCH_{nodes[0]}", src=dict(part=nodes[0], bus=MID_OUT), dst=coll)]
        new_lanes = [dict(id=f"LFCH_{nodes[0]}", ports=[new_ports[0]["id"]], fixed_cycles=0,
                          note=f"KV-FT v3.9 MB: {ch['fam']} fault chain tail {nodes[0]} -> {coll['part']} "
                               f"(was {nodes[-1]} -> {coll_old['part']} over {len(tp) - 1} crossings)")]
        # reverse every hop
        n = len(nodes)
        for i, l in enumerate(hops):                       # old nodes[i] -> nodes[i+1]; new nodes[i+1] -> nodes[i]
            old = [ports[x] for x in lanes[l]["ports"]]
            src_bus = HEAD_OUT if i + 1 == n - 1 else MID_OUT
            dst_bus = MID_IN       # one in-bus name for every non-head row (row types 1..5 are shared, e.g. kv3_pc_v1)
            rp = []
            for j, p in enumerate(reversed(old)):
                q = dict(p, id=f"{l}_r{j}", face=OPP[p["face"]], src=dict(p["dst"]), dst=dict(p["src"]))
                if q["src"]["bus"].endswith("_i"):
                    q["src"]["bus"] = q["src"]["bus"][:-2] + "_o"
                if q["dst"]["bus"].endswith("_o"):
                    q["dst"]["bus"] = q["dst"]["bus"][:-2] + "_i"
                rp.append(q)
            rp[0]["src"]["bus"] = src_bus
            rp[-1]["dst"]["bus"] = dst_bus
            for q in rp[:-1]:                              # crossed slots: swap faces (type frame)
                part = q["dst"]["part"]
                sn = q["dst"]["bus"][:-2]
                key = (parts[part]["type"], sn)
                if key not in swapped:
                    s = next(x for x in T[key[0]]["ft_slots"] if x["name"] == sn)
                    s["in_face"], s["out_face"] = s["out_face"], s["in_face"]
                    if s.get("regs_um"):
                        s["regs_um"] = list(reversed(s["regs_um"]))
                    swapped.add(key)
            new_ports += rp
            new_lanes.append(dict(id=l, ports=[q["id"] for q in rp], fixed_cycles=lanes[l].get("fixed_cycles", 0),
                                  note=lanes[l].get("note", "") + " | KV-FT v3.9 MB: reversed (chain runs toward its "
                                  "collector)", **({"param": lanes[l]["param"]} if "param" in lanes[l] else {})))
            rev_lanes.add(l)
        drop = set(hops) | {tail}
        pids = {pid for l in drop for pid in lanes[l]["ports"]}
        raw["ports"] = [x for x in raw["ports"] if x["id"] not in pids] + new_ports
        raw["lanes"] = [x for x in raw["lanes"] if x["id"] not in drop] + new_lanes
        gone.add(tail)
        # type buses per new role
        for k, nd in enumerate(nodes):
            t = T[parts[nd]["type"]]
            names = {HEAD_OUT, FIRST_IN, MID_OUT, MID_IN}
            t["buses"] = [b for b in t["buses"] if b["name"] not in names]
            if k == n - 1:            # new head
                need = [(HEAD_OUT, "out")]
            else:
                need = [(MID_IN, "in"), (MID_OUT, "out")]
            for nm, d in need:
                if not any(b["name"] == nm for b in t["buses"]):
                    t["buses"].append(dict(name=nm, dir=d, width=1, kind="data"))
            fch = [c for c in t["contents"] if c["inst"] == "u_fch"]
            if k == n - 1 and fch:
                t["contents"] = [c for c in t["contents"] if c["inst"] != "u_fch"]
            if k == 0 and not fch:
                t["contents"].append(dict(inst="u_fch", module="qkd_hp_or2", status="reuse",
                                          note="fault or (KV-FT v3.9 MB: chain tail beside the collector)"))
        if ch["new_coll"]:
            hub_fch.setdefault(ch["new_coll"], []).append(ch["new_coll_bus"])
            hc = T["kv3_hub_C"]
            hc["buses"] = [b for b in hc["buses"] if b["name"] != coll_old["bus"]]
        # census
        inst = lambda p: f"fch_{p}"                       # noqa: E731
        drop_rows = []
        for r in rows:
            if (r[0] == f"efault_{nodes[0]}" and r[2] == inst(nodes[1])) or \
               (r[0] in {inst(x) for x in nodes} and r[1] == "q" and (r[2] in {inst(x) for x in nodes}
                                                                      or r[0] == inst(nodes[-1]))):
                drop_rows.append(r)
        assert len(drop_rows) == n, (nodes, drop_rows)
        coll_inst = next(r[2] for r in drop_rows if r[0] == inst(nodes[-1]))
        rows[:] = [r for r in rows if r not in drop_rows]
        rows.append([f"efault_{nodes[-1]}", "fault", inst(nodes[-2]), "b", "data", "1"])
        for a, b in zip(list(reversed(nodes))[1:], list(reversed(nodes))[2:]):
            rows.append([inst(a), "q", inst(b), "b", "data", "1"])
        rows.append([inst(nodes[0]), "q", ch.get("census_coll") or coll_inst, "b", "data", "1"])
        mp["parts"][inst(nodes[0])] = nodes[0]
        mp["parts"].setdefault(f"efault_{nodes[-1]}", nodes[-1])
        LOG.append(dict(move="MB", chain=f"{nodes[0]}..{nodes[-1]}", tail_lane_removed=tail,
                        tail_crossings=len(tp) - 1, collector=coll["part"]))
    # hub_Eo / hub_Wo join: hg chains OR into the partition fault that already lanes to hub_C
    T = raw["partition_types"]
    parts = {x["name"]: x for x in raw["partitions"]}
    for hub, buses in hub_fch.items():
        t = T[parts[hub]["type"]]
        for b in buses:
            t["buses"].append(dict(name=b, dir="in", width=1, kind="data"))
        t["contents"].append(dict(inst="u_fchj", module="qkd_hp_or2", status="reuse", note=(
            "KV-FT v3.9 MB: OR of the two hg fault chains with this partition's efault; drives the existing "
            "o_efault_* lane to hub_C")))
        cinst = "fchj_" + hub
        mp["parts"][cinst] = hub
        for r in rows:
            if r[0] == f"efault_{hub}" and r[1] == "fault":
                r[0], r[1] = cinst, "q"
        rows.append([f"efault_{hub}", "fault", cinst, "a", "data", "1"])
    return gone
