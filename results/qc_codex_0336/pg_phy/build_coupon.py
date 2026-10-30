"""Separate-supply feasibility coupon; legacy point-source diagnostic, not IR sign-off."""
import json
import re
import sys
from pathlib import Path

repo = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(repo / "tools/die_plan"))
import schema as S
import infra_pg_domains as G

inputs = Path(__file__).resolve().parent
plan = repo / "physical/die_plan/qwen_compute/plan_of_record/plan_qc46.json"
raw = S.load(plan)
raw["die"]["io"] = json.loads((plan.parent / "die_io.json").read_text())
actual_core_plan = S.Plan(json.loads(json.dumps(raw)), plan)
# The current repository has no typed finite PHY power-pad dimensions. Preserve
# the existing diagnostic point-source model explicitly; never substitute the
# 70-um core C4 pad for the much finer published-assumption PHY power lattice.
# Core 150-um point sources also make the adjacent high-density core strip a
# conservative feasibility proxy rather than claiming the QC75 finite-pad gate.
raw["die"]["pg"]["bumps"] = {"pitch_um": 150, "pad_um": 0}
P = S.Plan(raw, plan)
pg = json.loads((inputs / "pg.json").read_text())
window = json.loads((inputs / "window.json").read_text())
result = G.make(P, plan.parent, pg, window, Path(sys.argv[1]), float(sys.argv[2]) if len(sys.argv) > 2 else 8.64)
if "--core-finite" in sys.argv:
    # Refine only the known core source geometry: retain the existing QC75/150
    # finite core pads verbatim. PHY tuples remain explicitly zero-width ideal
    # points; a core C4 pad is never silently borrowed for a PHY source.
    source_rows = G.I.pg_bumps(actual_core_plan, actual_core_plan.die["io"], pitch=150)
    x0, y0, x1, y1 = window["window_um"]
    domains = result["die"]["pg"]["domains"]
    bumps = []
    for source in source_rows:
        net, x, y = source[:3]
        if not (x0 < x < x1 and y0 < y < y1):
            continue
        local_x, local_y = round(x - x0, 3), round(y - y0, 3)
        is_phy = any(d["rect_um"][0] <= local_x <= d["rect_um"][2]
                     and d["rect_um"][1] <= local_y <= d["rect_um"][3] for d in domains)
        if len(source) == 3 and not is_phy:
            raise ValueError("untyped source outside PHY body; no finite-pad inference allowed")
        pad = source[3] if len(source) == 4 else 0
        if is_phy:
            assert pad == 0
            if net == "VDD":
                net = "VDDPHY"
        bumps.append((net, local_x, local_y, pad))
    finite = [b for b in bumps if b[3] > 0]
    points = [b[:3] for b in bumps if b[3] == 0]
    # Keep each established emitter's contract: finite per-bump pads must be
    # positive; explicit PHY point sources use the separate legacy point deck.
    finite_text = G.D.bumps_tcl(actual_core_plan, finite, pad_um=0)
    assert "${net}_b$k" in finite_text
    finite_text = finite_text.replace("${net}_b$k", "${net}_core_b$k")
    text = finite_text + G.D.bumps_tcl(actual_core_plan, points, pad_um=0)
    text = text.replace('foreach net_name {VDD VSS}', 'foreach net_name {VDD VSS VDDPHY}')
    text = re.sub(r'(dbBTerm_create \[\$block findNet VDDPHY\].*?\$bt setSigType )GROUND',
                  r'\1POWER', text)
    text = ('set block [ord::get_db_block]\nforeach name {VDD VDDPHY VSS} '
            '{set bt [$block findBTerm $name];if {$bt ne "NULL"} {odb::dbBTerm_destroy $bt}}\n' + text)
    (Path(sys.argv[1]) / "psm/bumps.tcl").write_text(text)
    result["bumps"] = bumps
    result["source_geometry"] = "actual QC75/150 finite core pads; explicit ideal PHY points only"
    (Path(sys.argv[1]) / "domains.json").write_text(json.dumps(result, indent=1) + "\n")
# Include the shared return mesh; a single VDDPHY result cannot establish the
# combined VDD-drop plus VSS-bounce policy. Ground analysis uses its native net
# voltage, matching the existing QC-PG window method.
tcl = Path(sys.argv[1]) / "psm/psm.tcl"
text = tcl.read_text()
text = text.replace('puts OT_DONE',
    'puts "OT_ANALYZE_NET VSS";analyze_power_grid -net VSS '
    '-error_file /work/psm/psm_VSS.rpt -voltage_file /work/psm/ir_VSS.csv;'
    'puts "OT_PSM_OK VSS";puts OT_DONE')
tcl.write_text(text)
print(json.dumps({k: v for k, v in result.items() if k not in {"bumps", "die"}}, indent=1))
