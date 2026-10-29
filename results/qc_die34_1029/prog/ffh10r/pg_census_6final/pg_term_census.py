"""DIE-QC-35 KITS: PG terminal census of a routed kit ODB (6_final). Every instance master POWER/GROUND MTerm must have its
ITerm connected to a special net of the same signal type (VDD POWER / VSS GROUND); master-terminal driven (does not trust
getITerms coverage). Also counts PG special nets with no SWire.  Usage: openroad -python -exit pg_term_census.py ODB OUT.json"""
import json, sys, collections
import odb
d = odb.dbDatabase.create(); odb.read_db(d, sys.argv[1]); b = d.getChip().getBlock()
res = collections.Counter(); first = []; by_master = collections.Counter()
for inst in b.getInsts():
    m = inst.getMaster()
    for mt in m.getMTerms():
        st = mt.getSigType()
        if st not in ("POWER", "GROUND"):
            continue
        res["pg_terms"] += 1
        it = inst.findITerm(mt.getName())
        net = it.getNet() if it else None
        ok = net is not None and net.isSpecial() and net.getSigType() == st
        if not ok:
            res["open_or_wrong"] += 1; by_master[m.getName()] += 1
            if len(first) < 20:
                first.append([inst.getName(), m.getName(), mt.getName(), net.getName() if net else None])
nets = {}
for n in b.getNets():
    if n.getSigType() in ("POWER", "GROUND"):
        nets[n.getName()] = dict(sig=n.getSigType(), special=n.isSpecial(), swires=len(list(n.getSWires())),
                                 iterms=len(list(n.getITerms())))
out = dict(odb=sys.argv[1], insts=len(list(b.getInsts())), pg_terms=res["pg_terms"], open_or_wrong=res["open_or_wrong"],
           by_master=dict(by_master), first=first, pg_nets=nets,
           verdict="PASS" if res["open_or_wrong"] == 0 and res["pg_terms"] > 0 and all(v["swires"] > 0 for v in nets.values()) else "FAIL")
json.dump(out, open(sys.argv[2], "w"), indent=1)
print("PG_TERM_CENSUS", out["verdict"], "insts", out["insts"], "pg_terms", out["pg_terms"], "open_or_wrong", out["open_or_wrong"],
      {k: (v["swires"], v["iterms"]) for k, v in nets.items()})
