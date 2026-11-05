#!/usr/bin/env python3
"""HBM-REFORM-A2 d44v part 18 plan delta.   mk_p18.py PLAN_DIR PART_DIR REPO
PLAN_DIR: a plan copy with part 17 applied.  lane_exp0_id rows first grow 414.72 -> 440.64 on local E so both rows take one sfu_s outline; E-face pins follow.
Then results/die_hbm_1103/reform/mk_split.py unchanged; lane_exp_x and lane_full_x get one-clock tables (mk_oneclk.py); id rows carry parent_id_straps like canon."""
import json, os, re, subprocess, sys
from pathlib import Path
pd, part, repo = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
ID, CANON = "ot_hbm_su_static_pgslice_lg__lane_exp0_id", "ot_hbm_su_static_pgslice_lg__lane_exp__canon_7cd691"
XE, XF, SFU = "ot_hbm_su_pg_lane_exp_x_core", "ot_hbm_su_pg_lane_full_x_core", "ot_hbm_su_pg_sfu_s_core"
GROW = 25.92; RX = repo / "rtl/hbm_accel/cores_split/reform_1104a/lane_x"
def wr(f, s):
    t = Path(str(f) + ".tmp"); t.write_text(s); os.replace(t, f)
D = json.loads((pd / "die_plan.json").read_text())
rows = [h for t in D["partition_types"].values() for h in t.get("hard_cores") or [] if h["module"] == ID]
pf = {h["pins_file"] for h in rows}; assert len(pf) == 1, pf; pf = pf.pop()
T = json.loads((pd / pf).read_text()); W = rows[0]["outline_um"][0]; n = 0
for p in T:
    if p["x"] > W - 1.0: p["x"] = round(p["x"] + GROW, 3); n += 1
nf = pf.replace("414.72x207.36", "440.64x207.36").replace(".json", "__p18.json"); wr(pd / nf, json.dumps(T, indent=1) + "\n")
vals = {}
for h in rows:
    assert h.get("orient", "R0") in ("R0", "MX"), h["inst"]
    h["outline_um"] = [440.64, 207.36]; h["pins_file"] = nf; vals[h["inst"]] = h["straps"][0]["value"]
print("id rows", len(rows), "E pins moved", n, "ids", sorted(set(vals.values())))
wr(pd / "die_plan.json", json.dumps(D, indent=1) + "\n")
subprocess.run([sys.executable, str(repo / "results/die_hbm_1103/reform/mk_split.py"), str(pd), str(part / "split_p18.json"), str(part)], check=True, stdout=open(pd / "split_p18.log", "w"))
print((pd / "split_p18.log").read_text()[-1400:])
D = json.loads((pd / "die_plan.json").read_text()); k = 0
for t in D["partition_types"].values():
    for h in t.get("hard_cores") or []:
        if h["module"] == XF:
            I = h["inst"].rsplit("__", 1)[0]
            h.pop("straps", None); h.pop("physical_id_alias", None)
            h["parent_id_straps"] = {"lane_lane_id": dict(width=11, value=vals[I])}; k += 1
wr(pd / "die_plan.json", json.dumps(D, indent=1) + "\n"); print("id straps", k)
sh = {}
for m in (XE, XF):
    txt = (RX / f"{m}.sv").read_text()
    hdr = re.search(r"module\s+" + m + r"\s*#\s*\(.*?\)\s*\((.*?)\n\);", txt, re.S).group(1)
    pl = ["# dir width name"] + [f"{a} [{int(w or 0)}:0] {nm}" for a, w, nm in re.findall(r"(input|output)\s+wire\s+(?:\[(\d+):0\]\s*)?(\w+)", hdr)]
    (part / f"{m}.portlist").write_text("\n".join(pl) + "\n")
    w = repo / f"physical/die_plan/hbm_arch_cores/wrappers/oneclk/{m}.sv"
    r = subprocess.run([sys.executable, str(repo / "results/die_hbm_1104/reform/mk_oneclk.py"), str(pd), m, str(w), "--rename-top", m + "__mc", "--portlist", str(part / f"{m}.portlist")], check=True, capture_output=True, text=True)
    print(r.stdout.strip()[:300]); sh[m] = re.search(r"[0-9a-f]{64}", r.stdout).group(0)
f = pd / "core_clock_regions.json"; G = json.loads(f.read_text()); gone = []
if isinstance(G.get("modules"), dict):
    for m in (ID, CANON):
        if m in G["modules"]: gone.append(m); G["modules"].pop(m)
    wr(f, json.dumps(G, indent=1) + "\n")
print("regions removed", gone)
f = repo / "physical/die_plan/hbm_arch_cores/recipes_b2.json"; R = json.loads(f.read_text())
for m, parent, base in ((XE, CANON, "ot_hbm_su_pg_lane_exp_core"), (XF, ID, "ot_hbm_su_pg_lane_full_core")):
    r = json.loads(json.dumps(R[parent])); fs = [x for x in r["files"] if not x.endswith(("/ot_hbm_su_static_lane.sv", "/ot_hbm_su_static_lane_pinreg.sv", f"/{base}.sv"))]
    r["files"] = fs + [str((RX / x).relative_to(repo)) for x in ("ot_hbm_su_static_lane_x.sv", "ot_hbm_su_static_lane_pinreg_x.sv", f"{m}.sv")]
    r["top"] = m; r["rename_top"] = m + "__mc"; r.pop("files_at", None); r.pop("functional_type", None); r.pop("port_map_note", None)
    r["source"] = f"HBM-REFORM-A d44v part 18: S chain of {base} moved to {SFU}; bench results/die_hbm_1104/reform_a/part18"
    r["wrapper_by_pins_sha256"] = {sh[m]: f"physical/die_plan/hbm_arch_cores/wrappers/oneclk/{m}.sv"}; R[m] = r
r = json.loads(json.dumps(R[CANON])); r["files"] = [x for x in r["files"] if re.search(r"/ot_(hdc|fp32)", x)] + [str((RX / f"{SFU}.sv").relative_to(repo))]
r["top"] = SFU; r["macros"] = []; r.pop("wrapper_by_pins_sha256", None); r.pop("files_at", None); r.pop("functional_type", None); r.pop("port_map_note", None); r.pop("rename_top", None)
r["source"] = "HBM-REFORM-A d44v part 18: exp, +1, divide chain of the KIND 1/2 SU lane, verbatim"; R[SFU] = r
wr(f, json.dumps(R, indent=1) + "\n")
f = repo / "physical/die_plan/hbm/reset_contract.json"; C = json.loads(f.read_text()); m = C["modules"]
for x in (XE, XF, SFU):
    if x not in m: m.append(x)
m.sort(); C["modules_basis"] = C["modules_basis"].rstrip() + " d44v part 18: lane_exp_x, lane_full_x, sfu_s reset pins from the same parent lane reset through wires only."
wr(f, json.dumps(C, indent=1) + "\n"); print("recipes + reset contract done")
