"""CORE-HBM census of the HBM d4g planned hard cores (plan claude/hbm-p5-1023 @0ea1350db).
One hardening TYPE = (module, outline, pins_file); replicated instances are hardened once.
    python3 census.py PLAN.json OUT.json  (also prints a TSV)"""
import collections, hashlib, json, re, sys
from pathlib import Path

EXCL_PARTS = {"q_su2": "HBM-P6 changing SU2", "q_vm": "HBM-P6 changing the VM slice",
              "q_hc2": "HBM-P6 hc2 congestion", "q_hc7": "HBM-P6 hc7 congestion"}
CAP = 400000


def main(plan, out):
    d = json.load(open(plan))
    root = Path(plan).resolve().parent
    pt = d["partition_types"]
    ninst = collections.Counter(p["type"] for p in d["partitions"])
    T = {}
    for tn, t in pt.items():
        for c in t.get("hard_cores", []):
            key = (c["module"], tuple(c["outline_um"]), c.get("pins_file"))
            e = T.setdefault(key, dict(module=c["module"], outline_um=c["outline_um"], pins_file=c.get("pins_file"),
                                       slots=[], die_instances=0, cells=None, basis=None, notes=set()))
            e["slots"].append(f"{tn}.{c['inst']}")
            e["die_instances"] += ninst[tn]
            n = c.get("note", "")
            m = re.search(r"(\d+) cells", n)
            if m:
                e["cells"] = max(e["cells"] or 0, int(m.group(1)))
            for b in ("MEASURED-SYNTH", "CUT-ONLY", "RTL-UNBENCHED", "CLOSED", "SYNAREA", "YOSYS", "DONE"):
                if b in n:
                    e["notes"].add(b)
            if "SPLIT PROPOSAL" in n:
                e["notes"].add("SPLIT:" + n.split("SPLIT PROPOSAL of ")[1].split(" ")[0])
    rows = []
    for key, e in T.items():
        pf = e["pins_file"]
        npins, h = None, None
        if pf and (root / pf).is_file():
            raw = (root / pf).read_bytes()
            h = hashlib.sha256(raw).hexdigest()[:16]
            npins = len(json.loads(raw))
        parts = sorted({s.split(".")[0] for s in e["slots"]})
        excl = [p for p in parts if p in EXCL_PARTS]
        e.update(parts=parts, pins=npins, pins_sha16=h,
                 excluded=("ALL: " + ",".join(excl)) if excl and len(excl) == len(parts) else
                 (("SHARED w/ " + ",".join(excl)) if excl else ""),
                 over_cap=bool(e["cells"] and e["cells"] > CAP), notes=sorted(e["notes"]),
                 type_id=f"{e['module']}__{e['outline_um'][0]:g}x{e['outline_um'][1]:g}")
        del e["slots"]
        rows.append(e)
    rows.sort(key=lambda r: (-r["die_instances"], r["module"]))
    json.dump(dict(schema="opentallas.hbm.core_census.v1", plan=plan, types=rows), open(out, "w"), indent=1)
    print("type_id\tdie_inst\tcells\tpins\texcluded\tover_cap\tnotes\tparts")
    for r in rows:
        print(f"{r['type_id']}\t{r['die_instances']}\t{r['cells']}\t{r['pins']}\t{r['excluded']}\t{r['over_cap']}\t"
              f"{','.join(r['notes'])}\t{','.join(r['parts'][:5])}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
