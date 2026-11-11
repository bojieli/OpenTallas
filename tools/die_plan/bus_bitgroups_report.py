#!/usr/bin/env python3
"""KIT-ISTATIONS 11-11: chainchk for every type: per multi-core bus, the merged chain's worst core hop vs the per-bit-group
hop, bits beyond the 405-um reach, owners resolved.  usage: bus_bitgroups_report.py PLAN RTLDIR [TYPE...]
(RTLDIR holds hbm_arch_<type>.sv, the bound module text)"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_bus_bitgroups as BG  # noqa: E402
import kit_istations as KI  # noqa: E402


def main(argv):
    raw = json.load(open(argv[0]))
    T = raw["partition_types"]
    rtl = Path(argv[1])
    names = argv[2:] or sorted(T)
    print("type\tbus\tdir\tbits\tcores\tdepth\tmerged_max_core_hop\tmerged_bits>405\tgroup_max_hop\tunresolved_bits\tmode")
    for tn in names:
        t = T[tn]
        f = rtl / f"hbm_arch_{tn}.sv"
        for e in KI.bus_entries(t):
            if e.get("merged_entries", 1) < 2 or e.get("bit_route") or "bit_sites_um" in e:
                continue
            bus = e["conn"][4:]
            b = next(x for x in t["buses"] if x["name"] == bus)
            in_bus = b["dir"] == "in"
            rows = e["per_core_rows"]
            regs = e["regs_um"]
            tot = sum(int(r.get("bits", 1)) for r in rows)
            far = worst = 0
            for r in rows:
                ff = in_bus or str(r.get("launch", "")).startswith("face bus")
                core = r["to_um"] if ff else r["from_um"]
                d = min(BG._dist(core, regs[0]), BG._dist(core, regs[-1]))
                worst = max(worst, d)
                far += int(r.get("bits", 1)) if d > BG.REACH_UM else 0
            hard = [h['inst'] for h in t.get('hard_cores', [])]
            cores = sorted({BG.core_of_entry(r, hard) for r in rows} - {None})
            n = KI.gen_rtl.sv_id(bus)
            g, unres = None, "no-rtl"
            if f.exists():
                txt = f.read_text()
                W = b["width"]
                try:
                    W = KI.bound_bus_width(tn, b, txt, dict())
                except SystemExit:
                    pass
                own = BG.in_bit_owners(txt, n, cores) if in_bus else BG.out_bit_owners(txt, n, W, cores)
                g = BG.plan_groups(rows, in_bus, len(regs), W, own, hard)
                unres = g["unresolved_bits"] if g else "no-owners"
            gh = round(max(v["hop_um"] for v in g["groups"].values())) if g else ""
            mode = "AUTO-ON" if BG.merged_violates(rows, regs, in_bus) else "unchanged"
            print(f"{tn}\t{bus}\t{b['dir']}\t{tot}\t{len(cores)}\t{len(regs)}\t{round(worst)}\t{far} ({100*far//max(tot,1)}%)\t{gh}\t{unres}\t{mode}")


main(sys.argv[1:])
