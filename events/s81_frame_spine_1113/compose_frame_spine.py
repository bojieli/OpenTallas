#!/usr/bin/env python3
"""compose_frame_spine.py BASE OUT --shards DIR[,DIR...] [--report R.json] [--tsv R.tsv]

FRAME-SPINE-1113 volume merge (FRAME-FORMS-1-VOL).  Each shard DIR is one base item run by run_types.sh / shard.sh:
DIR/plan.json (core_place --out-plan, from the parked-tap plan), DIR/ev.json (core_place event rows), DIR/log.txt
(SEED-MOVED lines under '== <type>' headers) and DIR/street_full.json (street_rule.py check).

An item is ACCEPTED only when every one of its types has applied True, 0 SEED-MOVED lines and 0 hard street kinds
(street, wall, outline_street, face_street, station_alley).  For accepted items partition_types[t] of the shard plan
replaces the base type object; every other byte of the base plan is kept.  Refused items stay at base and are
reported with the reason (no design decision is taken here).  Run finalize.py BASE OUT OUT2 afterwards."""
import collections
import json
import re
import sys
from pathlib import Path

HARD = ("street", "wall", "outline_street", "face_street", "station_alley")


def seed_moved(log):
    cur, out = None, collections.Counter()
    for ln in Path(log).read_text(errors="replace").splitlines():
        m = re.match(r"^== (\S+)", ln)
        if m:
            cur = m.group(1)
        elif "SEED-MOVED" in ln and cur:
            out[cur] += 1
    return out


def main():
    a = sys.argv[1:]
    base, out = a[0], a[1]
    shards = a[a.index("--shards") + 1].split(",")
    B = json.load(open(base))
    rep, n_types = {}, 0
    for d in shards:
        d = Path(d)
        item = d.name
        ev = json.loads((d / "ev.json").read_text())
        rows = ev["rows"] if isinstance(ev, dict) else ev
        sm = seed_moved(d / "log.txt")
        sr = {r["type"]: r["counts"] for r in json.loads((d / "street_full.json").read_text())["rows"]}
        per, why = {}, []
        for r in rows:
            tn = r["type"]
            hard = {k: v for k, v in sr.get(tn, {}).items() if k in HARD}
            per[tn] = dict(applied=r["applied"], seed_moved=sm.get(tn, 0), hard=hard, overlaps=r["overlaps"],
                           eq=len(r["eq_violations"]), tviol=r["timing_violations_end"],
                           need_more_regs=r["stations_report"].get("need_more_regs"),
                           regs=[r["stations_report"].get("regs_old"), r["stations_report"].get("regs_new")],
                           timing_over=r["timing_over"][:3])
            if not r["applied"]:
                why.append("%s applied False (tviol %s, overlaps %s, eq %d)" % (tn, r["timing_violations_end"],
                                                                                r["overlaps"], len(r["eq_violations"])))
            if sm.get(tn):
                why.append("%s SEED-MOVED %d" % (tn, sm[tn]))
            if hard:
                why.append("%s hard street kinds %s" % (tn, hard))
            if tn not in sr:
                why.append("%s no street row" % tn)
        acc = not why and bool(rows)
        if acc:
            P = json.loads((d / "plan.json").read_text())
            for tn in per:
                B["partition_types"][tn] = P["partition_types"][tn]
                n_types += 1
            del P
        rep[item] = dict(accepted=acc, types=len(per), reasons=why, per_type=per)
        print(item, "ACCEPTED" if acc else "REFUSED", len(per), "; ".join(why)[:300], flush=True)
    json.dump(B, open(out, "w"), indent=1)
    print("types replaced", n_types, "items accepted", sum(r["accepted"] for r in rep.values()), "of", len(rep))
    if "--report" in a:
        Path(a[a.index("--report") + 1]).write_text(json.dumps(rep, indent=1, default=str))
    if "--tsv" in a:
        L = ["item\ttype\taccepted\tapplied\tseed_moved\thard\ttviol\tregs_old\tregs_new"]
        for it, r in sorted(rep.items()):
            for tn, p in sorted(r["per_type"].items()):
                L.append("\t".join(map(str, [it, tn, r["accepted"], p["applied"], p["seed_moved"],
                                             json.dumps(p["hard"], sort_keys=True), p["tviol"]] + p["regs"])))
        Path(a[a.index("--tsv") + 1]).write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
