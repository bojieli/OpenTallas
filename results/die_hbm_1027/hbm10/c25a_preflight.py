"""DIE-HBM-10 C25a: (1) gen_core_kit_hbm.io_tcl patch is byte-identical on every C24 pin table without w/h (old = origin
main io_tcl via git show); (2) KIT_PREFLIGHT clock_pin_geometry (tools/die_plan/kit_contract.py, unchanged) on the 8
HBM-CORES-KITS-1 kits with their clock-class io.tcl / pins.json lines regenerated from the C25a pin tables by the
patched io_tcl (the master-slice core clock entry line is kept as the kit has it).
usage: c25a_preflight.py WT C24 C25A KITS_ROOT OUTDIR"""
import json, sys, re, shutil, subprocess, importlib.util, types, glob
from pathlib import Path
WT, C24, C25, KR, OUT = map(Path, sys.argv[1:6])
sys.path.insert(0, str(WT / "tools/die_plan"))
import kit_contract as KC  # noqa: E402


def load(src, name):
    m = types.ModuleType(name); m.__file__ = str(WT / "physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py")
    sys.path.insert(0, str(WT / "physical/die_plan/hbm_arch_cores"))
    exec(compile(src, name, "exec"), m.__dict__)
    return m


new = load((WT / "physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py").read_text(), "gck_new")
old = load(subprocess.run(["git", "-C", str(WT), "show", "origin/main:physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py"],
                          capture_output=True, text=True, check=True).stdout, "gck_old")
P = json.load(open(C25 / "die_plan.json"))
outl = {}
for t in P["partition_types"].values():
    for c in t.get("hard_cores", []):
        if c.get("pins_file"):
            outl[c["pins_file"]] = c["outline_um"]
same = diff = 0
for pf, (w, h) in sorted(outl.items()):
    pins = json.load(open(C24 / pf))
    if any("w" in p for p in pins if isinstance(p, dict)):
        continue
    if not all(isinstance(p, dict) and "name" in p for p in pins):
        continue
    a, b = old.io_tcl(pins, w, h, "t"), new.io_tcl(pins, w, h, "t")
    same += a == b; diff += a != b
res = dict(byte_identity=dict(c24_unsized_pin_tables=same + diff, identical=same, different=diff))
rep = json.load(open(C25 / "c25a_event_report.json"))
res["kits"] = {}
for mod, d in rep["cores"].items():
    ks = sorted(glob.glob(str(KR / "k*/kits" / f"{mod}_*")))
    ks = [k for k in ks if Path(k).is_dir()]
    if not ks:
        res["kits"][mod] = dict(verdict="NO_KIT"); continue
    src = Path(ks[0]); kd = OUT / src.name
    if kd.exists():
        shutil.rmtree(kd)
    kd.mkdir(parents=True)
    for f in ("io.tcl", "constraint.sdc", "pins.json", "make_tracks.tcl", "config.mk", "master_slice.json"):
        if (src / f).exists():
            shutil.copy2(src / f, kd / f)
    for f in src.glob("*.tcl"):
        if not (kd / f.name).exists():
            shutil.copy2(f, kd / f.name)
    W, H = d["outline_um"]
    pins = json.load(open(C25 / d["pins_file"]))
    ck = {m_["pin"] for m_ in d["moves"]}
    io_new, rows_new = new.io_tcl([p for p in pins if p["name"] in ck], W, H, mod)
    lines_new = {re.match(r"place_pin -pin_name \{([^}]*)\}", l).group(1): l for l in io_new.splitlines() if l.startswith("place_pin")}
    out, replaced, kept = [], 0, []
    for l in (kd / "io.tcl").read_text().splitlines():
        m = re.match(r"\s*place_pin\s+-pin_name\s+\{([^}]*)\}", l)
        if m and m.group(1) in lines_new:
            if "master-plan slice" in l:
                kept.append(m.group(1)); out.append(l)
            else:
                out.append(lines_new[m.group(1)]); replaced += 1
        else:
            out.append(l)
    (kd / "io.tcl").write_text("\n".join(out) + "\n")
    pj = json.loads((kd / "pins.json").read_text())
    rows = {(r["bus"], r["bit"]): r for r in rows_new}
    L = pj if isinstance(pj, list) else pj.get("pins", [])
    nrow = 0
    for i, r in enumerate(L):
        k = (r.get("bus"), r.get("bit"))
        if k in rows:
            L[i] = rows[k]; nrow += 1
    (kd / "pins.json").write_text(json.dumps(pj, indent=1))
    errs, info = KC.clock_pin_geometry(kd)
    res["kits"][mod] = dict(kit=src.name, verdict="PASS" if not errs else "FAIL", errors=errs[:12], io_lines_replaced=replaced,
                            slice_entry_kept=kept, pins_json_rows=nrow, clock_ports=info.get("clock_ports"),
                            pins_json_warnings=info.get("pins_json_warnings"))
json.dump(res, open(OUT / "c25a_preflight.json", "w"), indent=1)
print(json.dumps(dict(byte_identity=res["byte_identity"],
                      kits={m: {k: v for k, v in r.items() if k in ("verdict", "errors", "io_lines_replaced", "slice_entry_kept", "pins_json_rows")}
                            for m, r in res["kits"].items()}), indent=1))
