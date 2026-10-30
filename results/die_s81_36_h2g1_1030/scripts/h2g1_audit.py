# openroad -python: DIE-S81-35/H2G1 post-install audit (read-only). env PLACE, CTS, SLICE, TCL, OUT
import json, os, re
import odb

U = 1000.0
def load(p):
    db = odb.dbDatabase.create(); odb.read_db(db, p); return db.getChip().getBlock()

b3, b4 = load(os.environ["PLACE"]), load(os.environ["CTS"])
sl = json.load(open(os.environ["SLICE"]))
adm = sl["cell_placements"]
tree = set(adm)

def snap(b):
    d = {}
    for i in b.getInsts():
        x, y = i.getLocation()
        d[i.getName()] = (x, y, i.getOrient(), i.getMaster().getName(), i.getPlacementStatus())
    return d

s3, s4 = snap(b3), snap(b4)
moved = [n for n in s3 if n in s4 and s3[n][:3] != s4[n][:3]]
seqre = re.compile(r"DFF|DHL|DLL|SDF|ICG|ASYNC", re.I)
moved_seq = [n for n in moved if seqre.search(s3[n][3])]
removed = [n for n in s3 if n not in s4]
added = [n for n in s4 if n not in s3]
added_nontree = [n for n in added if n not in tree]
seq_total = sum(1 for n in s3 if seqre.search(s3[n][3]))

disp = []; orient_mis = 0; master_mis = 0; missing = []
for n, c in adm.items():
    if n not in s4: missing.append(n); continue
    x, y, o, m, st = s4[n]
    ox, oy = c["origin_um"]
    disp.append(abs(x / U - ox) + abs(y / U - oy))
    orient_mis += (o != c["orient"]); master_mis += (m != c["master"])

# sink connectivity: every admitted ot_ci_tree_sink pin on its planned node's output net
bad = []; nsinks = 0
outnet = {}
for n in tree:
    i = b4.findInst(n)
    if i: outnet[n] = i.findITerm("Y").getNet()
for line in open(os.environ["TCL"]):
    if not line.startswith("ot_ci_tree_sink "): continue
    m = re.match(r"ot_ci_tree_sink \{([^}]*)\} \{([^}]*)\}", line)
    node, pin = m.group(1), m.group(2)
    nsinks += 1
    inst, term = pin.rsplit("/", 1)
    i = b4.findInst(inst) or b4.findInst(inst.replace("\\", ""))
    it = i.findITerm(term) if i else None
    net = it.getNet() if it else None
    if net is None or outnet.get(node) is None or net.getName() != outnet[node].getName():
        bad.append(pin)
# clock-tree nets: buffers driving clock nets that are not planned
clk_bufs_unplanned = []
for net in b4.getNets():
    if net.getSigType() != "CLOCK": continue
    for it in net.getITerms():
        if it.isOutputSignal() and it.getInst().getName() not in tree:
            mn = it.getInst().getMaster().getName()
            if mn.startswith("BUF") or mn.startswith("INV") or mn.startswith("CKINV"):
                clk_bufs_unplanned.append(it.getInst().getName())
bt = b4.findBTerm("ck[0]")
pins = []
for bp in bt.getBPins():
    for box in bp.getBoxes():
        pins.append(dict(layer=box.getTechLayer().getName(), cx=(box.xMin() + box.xMax()) / 2 / U, cy=(box.yMin() + box.yMax()) / 2 / U))
fixed_or_firm_not_placed = [n for n in tree if n in s4 and s4[n][4] not in ("FIRM", "FIXED", "LOCKED")]
r = dict(insts_place=len(s3), insts_cts=len(s4), moved_preexisting=len(moved), moved_preexisting_sequential=len(moved_seq),
         sequential_preexisting=seq_total, removed=len(removed), added=len(added), added_nontree=len(added_nontree),
         added_nontree_examples=added_nontree[:20], moved_examples=moved[:20], moved_seq_examples=moved_seq[:20],
         tree_cells=len(tree) - len(missing), tree_missing=missing[:10], tree_master_mismatch=master_mis,
         tree_orient_mismatch=orient_mis, tree_disp_um=dict(max=max(disp) if disp else None,
         mean=sum(disp) / len(disp) if disp else None, exact=sum(1 for d in disp if d < 1e-6),
         over_1um=sum(1 for d in disp if d > 1.0)), tree_not_firm=len(fixed_or_firm_not_placed),
         sinks_checked=nsinks, sinks_bad=len(bad), sinks_bad_examples=bad[:10],
         unplanned_clock_drivers=len(clk_bufs_unplanned), unplanned_clock_driver_examples=clk_bufs_unplanned[:10],
         ck0_pins=pins)
r["verdict"] = "PASS" if (r["moved_preexisting_sequential"] == 0 and r["tree_cells"] == 1811 and not master_mis and
                          nsinks == 19747 and not bad and r["added_nontree"] == 0 and not clk_bufs_unplanned and
                          r["removed"] == 0) else "FAIL"
json.dump(r, open(os.environ["OUT"], "w"), indent=1)
print("H2G1_AUDIT", json.dumps({k: v for k, v in r.items() if not k.endswith("examples")}))
