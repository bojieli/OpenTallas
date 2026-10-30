import sys, odb
db = odb.dbDatabase.create(); odb.read_db(db, sys.argv[1]); b = db.getChip().getBlock(); u = b.getDbUnitsPerMicron()
def up(name, k=6):
    i = b.findInst(name)
    for _ in range(k):
        a = [t for t in i.getITerms() if t.isInputSignal() and t.getNet() and t.getNet().getSigType() != "POWER"][0]
        n = a.getNet(); drv = [t for t in n.getITerms() if t.isOutputSignal()]
        wl = 0
        w = n.getWire()
        if w:
            try: wl = w.getLength()/u
            except Exception: wl = -1
        x, y = i.getLocation()
        print(f"  {i.getName()} {i.getMaster().getName()} @({x/u:.1f},{y/u:.1f}) <- net {n.getName()} fanout {len(list(n.getITerms()))-1} wire {wl:.1f}um")
        if not drv: print("   port", [bt.getName() for bt in n.getBTerms()]); break
        i = drv[0].getInst()
for nm in sys.argv[2:]:
    print(nm); up(nm)
