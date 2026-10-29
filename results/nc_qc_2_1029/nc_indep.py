"""NUMBER-CHECK-QC-2 independent counts (own code): PG SWire wire/via counts src vs out, contact/group/cell counts from
access_plan, non-PG fingerprint (inst placement + signal-net iterm connectivity + signal wire bytes), and a whole-die VIA12 mutant."""
import json, sys, hashlib, collections, time
import odb
src, out, plan_p, cells_p, res_p, mut_p = sys.argv[1:7]
t0=time.time()
plan = json.load(open(plan_p))
paths = plan["paths"]
pairs = {(m, q["net"]) for q in paths for m in q["members"]}
mem = {m for m, _ in pairs}
netc = collections.Counter(n for _, n in pairs)
R = dict(groups=len(paths), contacts=len(pairs), cells=len(mem), per_net=dict(netc),
         plan_vias=len(plan["vias_dbu"]), plan_failed=len(plan["failed"]), path_keys=sorted(paths[0].keys()))
allc = json.load(open(cells_p))
prov = {c["inst"] for c in allc["cells"]}
R["provider_cells_all_cells_json"] = len(prov); R["contact_cells_in_provider"] = len(mem & prov); R["contact_cells_not_provider"] = len(mem - prov)
R["not_provider_prefix"] = collections.Counter(m.split("_")[0] for m in mem - prov).most_common(5)
def load(p):
    d = odb.dbDatabase.create(); odb.read_db(d, p); return d
def pgcount(b):
    r = {}
    for n in ("VDD", "VSS"):
        w = v = 0; lay = collections.Counter(); grid = 0
        for sw in b.findNet(n).getSWires():
            for z in sw.getWires():
                if z.isVia(): v += 1
                else:
                    w += 1; ln = z.getTechLayer().getName(); lay[ln] += 1
                    if ln in ("M8","M9") and max(z.xMax()-z.xMin(), z.yMax()-z.yMin()) > 1000000: grid += 1
        r[n] = dict(wires=w, vias=v, long_m8m9=grid, by_layer=dict(sorted(lay.items())))
    return r
def nonpg(b):
    h = hashlib.sha256(); ni = 0
    for i in sorted(b.getInsts(), key=lambda i: i.getName()):
        x, y = i.getLocation(); h.update(f"{i.getName()}|{i.getMaster().getName()}|{x}|{y}|{i.getOrient()}|{i.getPlacementStatus()}\n".encode()); ni += 1
    nn = 0
    for n in sorted(b.getNets(), key=lambda n: n.getName()):
        if n.getSigType() in ("POWER", "GROUND"): continue
        nn += 1
        its = sorted(f"{t.getInst().getName()}/{t.getMTerm().getName()}" for t in n.getITerms())
        bts = sorted(t.getName() for t in n.getBTerms())
        w = n.getWire(); wl = w.getLength() if w else -1
        h.update((n.getName() + "|" + ",".join(its) + "|" + ",".join(bts) + f"|{wl}|{len(list(n.getSWires()))}\n").encode())
    return dict(insts=ni, signal_nets=nn, sha256=h.hexdigest())
for tag, p in (("src", src), ("out", out)):
    d = load(p); b = d.getChip().getBlock()
    R[tag] = dict(pg=pgcount(b), nonpg=nonpg(b))
    # contact cells present / master split
    if tag == "out":
        mc = collections.Counter()
        missing = 0
        for m in mem:
            i = b.findInst(m)
            if i is None: missing += 1; continue
            mc["CKINV" if "INV" in i.getMaster().getName() else "other"] += 1
        R["contact_cell_masters"] = dict(mc); R["contact_cells_missing"] = missing
        R["contact_master_top"] = collections.Counter(b.findInst(m).getMaster().getName() for m in mem if b.findInst(m)).most_common(8)
        # mutant: delete every VDD via whose tech via contains a V1 cut (VIA12)
        nd = 0
        for sw in b.findNet("VDD").getSWires():
            kill = [z for z in sw.getWires() if z.isVia() and z.getTechVia() and any(s.getTechLayer() and s.getTechLayer().getName() == "V1" for s in z.getTechVia().getBoxes())]
            for z in kill: odb.dbSBox.destroy(z); nd += 1
        R["mutant_vdd_via12_deleted"] = nd
        odb.write_db(d, mut_p)
    print(tag, json.dumps(R[tag]), round(time.time()-t0), flush=True)
R["delta"] = {n: dict(wires=R["out"]["pg"][n]["wires"]-R["src"]["pg"][n]["wires"], vias=R["out"]["pg"][n]["vias"]-R["src"]["pg"][n]["vias"]) for n in ("VDD","VSS")}
R["delta_total"] = dict(wires=sum(v["wires"] for v in R["delta"].values()), vias=sum(v["vias"] for v in R["delta"].values()))
R["seconds"] = round(time.time()-t0)
json.dump(R, open(res_p, "w"), indent=2, default=str); print(json.dumps({k: R[k] for k in R if k not in ("src","out")}, indent=2, default=str))
