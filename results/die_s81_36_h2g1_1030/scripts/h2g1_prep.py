#!/usr/bin/env python3
"""DIE-S81-35/H2G1: apply the ROOT-admitted H2 slice (codex/h2-window-1030 calibrated_native_admission) to a COPY of
the preserved native-placement kit with the canonical opt-in core_tree.install_stage = "pre_cts" (DIE-QC-36 A0):
the admitted 1811-cell tree is built on the EXISTING 3_place (no SYNTH/GPL), incremental DPL moves only tree cells,
every other instance (all FF homes) held FIRM.  Only two slice keys change: cell_placements removed (pre_cts refuses
frozen placements; node xy_um already equal the admitted converted centres) and install_stage added.
Fail-closed identity checks against the admitted master_core_infra.tcl: same 1811 cells/masters/xy, same 19747
sink lines/leaf memberships, same 1811 tree nodes/parents, native ck[0] entry 147.948/236.52.
usage: h2g1_prep.py WT KIT ADMITTED_SLICE ADMITTED_TCL OUTDIR"""
import copy, hashlib, json, re, sys
from pathlib import Path

wt, kit, sl_path, tcl_path, out = map(Path, sys.argv[1:6])
sys.path.insert(0, str(wt / "tools/die_plan"))
import master_slice as MS  # noqa: E402
import core_infra  # noqa: E402

h = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
sl = MS.load(sl_path)
adm = tcl_path.read_text().splitlines()

# 1. the admitted slice regenerates the admitted pre-GPL Tcl byte-for-byte (provenance of the installed tree)
regen = core_infra.emit_tcl(copy.deepcopy(sl), kit)
same_tcl = regen == tcl_path.read_text()

# 2. pre_cts form
sl2 = copy.deepcopy(sl)
cp = sl2.pop("cell_placements")
for n in sl2["core_tree"]["nodes"]:
    c = cp[n["name"]]
    assert n["xy_um"] == c["centre_um"], n["name"]
sl2["core_tree"]["install_stage"] = "pre_cts"
sl2["h2g1_install"] = ("DIE-S81-36/H2G1 2026-10-30: free-native-site re-converted model-admitted slice with cell_placements removed + "
                       "core_tree.install_stage pre_cts (canonical DIE-QC-36 A0 late install); no other key changed")
out.mkdir(parents=True, exist_ok=True)
sdir = out / "slice"; sdir.mkdir(exist_ok=True)
sp = sdir / f"{sl2['type']}.json"
sp.write_text(json.dumps(sl2, indent=1) + "\n")

# 3. canonical GEN hook: kit_apply (core_infra.install + master_slice copy/tcl + io consume) + plan_tree_cts
outline = sl2["outline_um"]
cfgp = kit / "config.mk"
before = {p.name: h(p) for p in kit.iterdir() if p.is_file()}
stamp = MS.kit_apply(kit, sl2["type"], outline, slice_dir=sdir, trial=True, kind="core", clock_ports=["ck[0]"])
cfg = cfgp.read_text().rstrip("\n").split("\n")
n0 = len(cfg)
hooked = MS.plan_tree_cts(kit, cfg)
cfgp.write_text("\n".join(cfg) + "\n")
after = {p.name: h(p) for p in kit.iterdir() if p.is_file()}
changed = sorted(k for k in after if before.get(k) != after[k])

# 4. identity of the late hook vs the admitted Tcl
late = (kit / "master_core_infra_late.tcl").read_text().splitlines()
pat = lambda lines, kw: [l.split(None, 1)[1] for l in lines if l.startswith(kw + " ")]
adm_cells = [re.sub(r"\s+\{[^}]*\}$", "", s) for s in pat(adm, "ot_ci_cell")]
late_cells = [re.sub(r"\s+\{[^}]*\}$", "", s) for s in pat(late, "ot_ci_late_cell")]
adm_sinks, late_sinks = pat(adm, "ot_ci_tree_sink"), pat(late, "ot_ci_tree_sink")
adm_nodes, late_nodes = pat(adm, "ot_ci_tree_node"), pat(late, "ot_ci_tree_node")
entry = [l for l in (kit / "master_core_infra.tcl").read_text().splitlines() if l.startswith("ot_ci_clock_entry")]
plan = json.loads((kit / "core_infra_plan.json").read_text())
checks = dict(
    admitted_tcl_regenerated_exact=same_tcl,
    cells=len(late_cells), cells_equal=sorted(adm_cells) == sorted(late_cells),
    sinks=len(late_sinks), sinks_equal=sorted(adm_sinks) == sorted(late_sinks),
    nodes=len(late_nodes), nodes_equal=sorted(adm_nodes) == sorted(late_nodes),
    clock_entry=entry, admitted_clock_entry=[l for l in adm if l.startswith("ot_ci_clock_entry")],
    # the admitted slice carries the native pin as native_clock_pin_contract (islands clock_pin None), so neither the
    # admitted nor the regenerated hook re-creates it; the native BTerm already in 3_place is checked at G1 instead
    entry_ok=entry == [] and not [l for l in adm if l.startswith("ot_ci_clock_entry")]
    and sl2["native_clock_pin_contract"] == {"layer": "M5", "xy_um": [147.948, 236.52]},
    core_islands=len(sl2.get("core_islands", [])),
    cts_open=len(plan["core_tree"].get("cts_open", [])),
    late_legalize=[l for l in late if l.startswith("ot_ci_late_legalize")],
    install_stage=plan["core_tree"].get("install_stage"),
    cts_hook_installed=hooked, config_lines_added=cfg[n0:], kit_files_changed=changed,
    slice_sha256_admitted=h(sl_path), slice_sha256_pre_cts=h(sp), admitted_tcl_sha256=h(tcl_path),
    late_tcl_sha256=h(kit / "master_core_infra_late.tcl"), stamp=stamp,
    place_odb_sha256=h(next((kit / "run/results/asap7").glob("*/base/3_place.odb"))))
ok = all(checks[k] for k in ("admitted_tcl_regenerated_exact", "cells_equal", "sinks_equal", "nodes_equal", "entry_ok",
                             "cts_hook_installed")) and checks["cells"] == 1811 and checks["sinks"] == 19747 \
    and checks["install_stage"] == "pre_cts" and checks["core_islands"] == 6
checks["verdict"] = "PASS" if ok else "FAIL"
(out / "prep.json").write_text(json.dumps(checks, indent=1) + "\n")
print(json.dumps({k: v for k, v in checks.items() if k not in ("kit_files_changed",)}, indent=1))
print("changed:", changed)
sys.exit(0 if ok else 1)
