"""HBM-BIND-7: bind_elab.flatten of the spliced netlist (as bind.py does, no substitute_parent in this manifest) with the
two coll parents' interfaces retained (metadata only; the flat graph is the default one). usage: mkflat_coll.py NETLIST.json OUT.pkl TOOLS_DIE_PLAN"""
import json, pickle, sys, time
from pathlib import Path
sys.path.insert(0, sys.argv[3])
import bind_elab as E
t = time.time()
y = json.loads(Path(sys.argv[1]).read_text())
F = E.flatten(y, "hbm_current_native_top", (), retain_hierarchy_ports=["hb_coll_NE", "hb_coll_NW"])
print("cells", len(F.cells), "nets", len(F.parent), round(time.time() - t, 1), flush=True)
pickle.dump(F, open(sys.argv[2], "wb"), protocol=5)
print("done", round(time.time() - t, 1))
