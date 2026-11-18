#!/usr/bin/env python3
"""S81-DIE-R3 11-17 (COORD / FABLE-CLOSURE-STRATEGY 17:2x): repoint the t51 native_w hard core from its PENDING unsigned
rc51a abstract (cores/legacy/lef/t51w_rc51a_1106: LEF, no lib -> gen_phys "macros have LEF but no timing liberty") to
the SIGNED rc51f view (R-MINIMAL 11-13 17:52; AGIdock /archive/opentallas-signed-1106/epyc7/.../eco_wf_scope21b_1113/i1;
verdict LOCAL_PASS_NEEDS_PARENT = internal 0 violations, port hold parent-owned).

* every source file is checked against the archive record's sha256 (ARCHIVED.json files[]);
* parent pins must not move: the plan pins_file cites the view pins.json sha and every pin's (layer, x, y) is equal;
* the LEF SIZE must equal the hard core outline (no reshape) and the lib must define the module cell;
* taps that land ONLY on the repointed module take the measured core insertion (signoff core_latency.measured mean,
  TT / FF) instead of the plan bound; taps shared with another child keep theirs.

usage: s81_t51w_repoint.py PLAN (edited in place) SRC_DIR TREE_ROOT OUT_OVERLAY
  SRC_DIR = the signed kit copy: ARCHIVED.json core.json pins.json signoff/signoff.json run/results/.../base/{lef,_tc.lib,_BC.lib}
"""
import hashlib
import json
import os
import re
import shutil
import sys

TYPE = "slice_station__t51"
MOD = "s81p_slice_station__t51_ot_s81_station_t51_native_w"
PD = "physical/die_plan/s81"
OLDLEF = f"{PD}/cores/legacy/lef/t51w_rc51a_1106/{MOD}.lef"
NEWV = f"{PD}/cores/views/{MOD}_signed_1113"
PINS = f"inputs/core_pins/{MOD}.json"
BASE = f"run/results/asap7/kl_{MOD}_rc51f/base"


def sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(8 << 20), b""):
            h.update(b)
    return h.hexdigest()


def view_pin_geometry(view_pins):
    """kit pins.json rows {bus, bit, layer, x, y} -> {name: (layer, x, y)}"""
    key = lambda q: q["bus"] if q.get("bit") is None else f"{q['bus']}[{q['bit']}]"
    return {key(q): (q["layer"], q["x"], q["y"]) for q in view_pins}


def plan_pin_geometry(plan_pins):
    """plan core_pins {pins: [{name, layer, x, y}]} -> {name: (layer, x, y)}"""
    return {q["name"]: (q["layer"], q["x"], q["y"]) for q in plan_pins["pins"]}


def check_pins(plan_pins, view_pins, view_pins_sha):
    if view_pins_sha not in plan_pins.get("source", ""):
        raise ValueError("plan pins_file does not cite the view pins.json sha")
    gv, gp = view_pin_geometry(view_pins), plan_pin_geometry(plan_pins)
    if gv != gp:
        bad = sorted(k for k in set(gv) | set(gp) if gv.get(k) != gp.get(k))
        raise ValueError(f"pin geometry differs on {len(bad)} pins, e.g. {bad[:5]}")
    return len(gv)


def lef_size(lef_text, module):
    if not re.search(rf"\bMACRO\s+{re.escape(module)}\b", lef_text):
        raise ValueError(f"LEF has no MACRO {module}")
    m = re.search(r"\bSIZE\s+([\d.]+)\s+BY\s+([\d.]+)", lef_text)
    return [float(m.group(1)), float(m.group(2))]


def repoint_plan(plan, tn, module, old_lef, new_view, pins_file, measured, outline, note):
    """Point the module's hard core at new_view (lef + tt lib); taps landing only on it take measured TT / FF mean."""
    t = plan["partition_types"][tn]
    hc = [h for h in t["hard_cores"] if h["module"] == module]
    if len(hc) != 1:
        raise ValueError(f"{tn}: {len(hc)} hard cores of {module}")
    hc = hc[0]
    if hc["lef"] != old_lef or "lib" in hc or hc["pins_file"] != pins_file:
        raise ValueError(f"{tn}: {module} is not the expected pending form: {hc.get('lef')} lib={hc.get('lib')}")
    if outline != hc["outline_um"]:
        raise ValueError(f"LEF SIZE {outline} != hard core outline {hc['outline_um']} (no reshape)")
    hc["lef"] = f"{new_view}/{module}.lef"
    hc["lib"] = f"{new_view}/{module}_tt.lib"
    hc["note"] = (hc.get("note", "") + "; " + note).lstrip("; ")
    pre = module + "."
    cnt = {"taps_only": 0, "taps_shared": 0}

    def walk(x):
        if isinstance(x, dict):
            lands = x.get("lands_on")
            if isinstance(lands, list) and lands and "insertion_ps" in x:
                ours = [l for l in lands if isinstance(l, dict) and str(l.get("pin", "")).startswith(pre)]
                if ours and len(ours) == len(lands):
                    x["insertion_ps"] = measured["tt"]["mean"]
                    x["insertion_ff_ps"] = measured["ff"]["mean"]
                    cnt["taps_only"] += 1
                elif ours:
                    cnt["taps_shared"] += 1
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)

    walk(t)
    return cnt


def main(argv):
    plan_path, src_dir, tree, out = argv[1:5]
    arch = json.load(open(os.path.join(src_dir, "ARCHIVED.json")))
    want = {f["path"].rsplit("/", 1)[-1]: f["sha256"] for f in arch["files"]}
    src = {"lef": os.path.join(src_dir, BASE, MOD + ".lef"), "tt": os.path.join(src_dir, BASE, MOD + "_tc.lib"),
           "ff": os.path.join(src_dir, BASE, MOD + "_BC.lib"), "pins": os.path.join(src_dir, "pins.json"),
           "core": os.path.join(src_dir, "core.json"), "signoff": os.path.join(src_dir, "signoff", "signoff.json")}
    for k, p in src.items():
        if sha_file(p) != want[os.path.basename(p)]:
            raise SystemExit(f"{k}: sha differs from the archive record")
    so = json.load(open(src["signoff"]))
    if so["verdict"] not in ("SIGNED", "LOCAL_PASS_NEEDS_PARENT") or so["policy"]["period_ps"] != 833.0:
        raise SystemExit(f"not a signed 833 ps view: {so['verdict']}")
    measured = so["core_latency"]["measured"]
    npins = check_pins(json.load(open(os.path.join(tree, PD, PINS))), json.load(open(src["pins"])), want["pins.json"])
    size = lef_size(open(src["lef"]).read(), MOD)
    if not re.search(rf"cell\s*\(\s*\"?{MOD}\"?\s*\)", open(src["tt"]).read()):
        raise SystemExit("tt lib has no cell " + MOD)
    vd = os.path.join(out, NEWV)
    os.makedirs(vd)
    for k, f in (("lef", MOD + ".lef"), ("tt", MOD + "_tt.lib"), ("ff", MOD + "_ff.lib"), ("pins", "pins.json"),
                 ("core", MOD + ".core.json"), ("signoff", "signoff.json")):
        shutil.copyfile(src[k], os.path.join(vd, f))
    shutil.copyfile(os.path.join(src_dir, "ARCHIVED.json"), os.path.join(vd, "ARCHIVED.json"))
    with open(os.path.join(vd, "odb.sha"), "w") as f:
        f.write(want["6_final.odb"] + "\n")
    ins = {"tt": {"boundary": measured["tt"]}, "ff": {"boundary": measured["ff"]}, "source": "signoff.json core_latency.measured"}
    json.dump(ins, open(os.path.join(vd, "insertion.json"), "w"), indent=2)
    plan = json.load(open(plan_path))
    note = (f"S81-DIE-R3 11-17 (FABLE-CLOSURE-STRATEGY 17:2x): REPOINTED from the PENDING unsigned rc51a abstract (LEF, no lib) "
            f"to the SIGNED rc51f view {NEWV} (R-MINIMAL 11-13, {so['verdict']}; archive {arch['archive']}); pins unchanged "
            f"({PINS} = view pins.json)")
    cnt = repoint_plan(plan, TYPE, MOD, OLDLEF, NEWV, PINS, measured, size, note)
    json.dump({"schema": "opentallas.s81.view_repoint.v1", "by": "S81-DIE-R3 11-17", "module": MOD,
               "replaces": OLDLEF + " (PENDING.json: unsigned rc51a abstract, no lib)",
               "this_view": f"SIGNED rc51f R-MINIMAL 11-13, verdict {so['verdict']} (port hold parent-owned)",
               "archive": arch["archive"], "odb_sha256": want["6_final.odb"], "files_sha256": want,
               "pins": {"parent_pins_file": PINS, "sha256": want["pins.json"], "pins": npins, "equal_geometry": True},
               "insertion": ins, "taps": cnt}, open(os.path.join(vd, "REPOINT_1117.json"), "w"), indent=1)
    with open(plan_path, "w") as f:
        f.write(json.dumps(plan, sort_keys=True) + "\n")
    print("REPOINT_W", json.dumps(cnt), "pins", npins, "insertion tt", measured["tt"]["mean"], "ff", measured["ff"]["mean"],
          "plan", sha_file(plan_path)[:16])


if __name__ == "__main__":
    main(sys.argv)
