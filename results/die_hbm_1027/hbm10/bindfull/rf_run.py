"""DIE-HBM-10: run the opt-in release_full check on the HBM canonical bind manifest (asbuilt_canon.json, main) for the 10
release slices (8 SU ot_hbm_su_static_pgslice_lg, 2 SFU ot_hgi_sfu_core_split3), plus a negative test that injects a stub.
usage: rf_run.py REPO OUT_JSON"""
import json, sys, shutil, tempfile
from pathlib import Path
repo, out = Path(sys.argv[1]).resolve(), Path(sys.argv[2])
sys.path.insert(0, str(repo / "tools/die_plan"))
import bind_elab as E

mf = repo / "results/die_hbm_1027/hbm7/bind/asbuilt_canon.json"
ab = json.loads(mf.read_text())
base = str((mf.parent / ab.get("base", ".")).resolve())
assert Path(base) == repo, base
ab["release_full"] = ["ot_hbm_su_static_pgslice_lg", "ot_hgi_sfu_core_split3"]
idx = E.module_index(ab.get("rtl_roots", ["rtl"]), ab.get("files", []), base)
prefer = [str(Path(base) / f) for f in ab.get("prefer", [])]
res = {"manifest": str(mf.relative_to(repo)), "masters": ab["release_full"], "alias": {k: ab["alias"][k] for k in ab["release_full"]}}
try:
    man = E.release_full_check(ab, base, idx, prefer)
    res["positive"] = {"result": "PASS", "full_rtl": man,
                       "modules": {m: len(v["modules"]) for m, v in man.items()}}
except E.ElabError as e:
    res["positive"] = {"result": "FAIL", "error": str(e)}
# negative: a stub file for one SU leaf (ot_hbm_su_static_lane_pinreg) put first in `prefer`
tmp = Path(tempfile.mkdtemp(dir=str(out.parent)))
stub = tmp / "ot_hbm_su_static_lane_pinreg_stub.sv"
src = Path(E.pick(idx, "ot_hbm_su_static_lane_pinreg", prefer)[0])
hdr = E._strip(src.read_text(errors="replace"))
import re
m = re.search(r"module\s+ot_hbm_su_static_lane_pinreg\b.*?\);", hdr, re.S)
stub.write_text(m.group(0) + "\nendmodule\n")
idx2 = {k: list(v) for k, v in idx.items()}
idx2["ot_hbm_su_static_lane_pinreg"].append(str(stub))
try:
    E.release_full_check(ab, base, idx2, prefer + [str(stub)])
    res["negative"] = {"result": "NOT CAUGHT"}
except E.ElabError as e:
    res["negative"] = {"result": "FAIL CLOSED (expected)", "error": str(e)[:400]}
shutil.rmtree(tmp)
out.write_text(json.dumps(res, indent=1))
print(json.dumps({k: (v if k != "positive" else {kk: vv for kk, vv in v.items() if kk != "full_rtl"}) for k, v in res.items()}, indent=1))
