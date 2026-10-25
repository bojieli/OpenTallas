"""Exact per-bit feedthrough geometry shared by prototype collection and reporting."""
from pathlib import Path
from collections import Counter

def hop_stats(src, reach=405.0):
    """per ft slot: the longest register-to-register hop (Manhattan um) of its station chain in the probe:
    in pin -> st_0 -> ... -> st_{k-1} -> out pin (the neighbour's station 0 sits at that pin).  Hops over `reach`
    (owner 10-24 decision 12: ft on <= M7 with stations every <= 405 um) are plan problems, not timing tuning."""
    import re
    src = Path(src)
    if not (src / "io.tcl").exists():
        return None
    pins = {m.group(1): (float(m.group(2)), float(m.group(3))) for m in
            re.finditer(r"place_pin -pin_name \{(\S+)\} -layer \S+ -location \{([\d.]+) ([\d.]+)\}",
                        (src / "io.tcl").read_text())}
    st = {}
    for m in re.finditer(r"place_inst -name st_(.+?)_(\d+)_(\d+) -location \{([\d.]+) ([\d.]+)\}",
                         (src / "probe.tcl").read_text()):
        st.setdefault((m.group(1), int(m.group(2))), {})[int(m.group(3))] = (float(m.group(4)), float(m.group(5)))
    out = {}
    for (slot, bit), chain in st.items():
        pts = []
        if f"{slot}_i[{bit}]" in pins:
            pts.append(pins[f"{slot}_i[{bit}]"])
        pts += [chain[j] for j in sorted(chain)]
        if f"{slot}_o[{bit}]" in pins:
            pts.append(pins[f"{slot}_o[{bit}]"])
        hop = max((abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(pts, pts[1:])), default=0.0)
        o = out.setdefault(slot, dict(max_hop_um=0.0, bits=0, stations=len(chain)))
        o["max_hop_um"] = round(max(o["max_hop_um"], hop), 1)
        o["bits"] += 1
    blk = [tuple(map(float, m.groups())) for m in
           re.finditer(r"create_blockage -region \{([\d.e-]+) ([\d.e-]+) ([\d.e-]+) ([\d.e-]+)\}",
                       (src / "probe.tcl").read_text())]
    in_core = Counter()
    for (slot, _bit), chain in st.items():
        for x, y in chain.values():
            if any(x0 + 1 < x < x1 - 1 and y0 + 1 < y < y1 - 1 for x0, y0, x1, y1 in blk):
                in_core[slot] += 1
    over = {k: v for k, v in out.items() if v["max_hop_um"] > reach}
    return dict(slots=len(out), max_hop_um=max((v["max_hop_um"] for v in out.values()), default=0.0),
                over_reach={k: v["max_hop_um"] for k, v in sorted(over.items(), key=lambda kv: -kv[1]["max_hop_um"])},
                over_reach_bits=sum(v["bits"] for v in over.values()),
                st_in_core=sum(in_core.values()), st_in_core_slots=dict(in_core.most_common(5)))


