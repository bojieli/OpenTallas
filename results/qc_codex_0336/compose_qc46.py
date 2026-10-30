"""Physical-only QC46 candidate: bounded CA bands and die-edge PHY core inset."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PD = ROOT / "physical/die_plan/qwen_compute/plan_of_record"
plan = json.loads((PD / "plan_qc45.json").read_text())
for name in (
    "sle_su_l1__cl5ea486db",
    "slw_su_l1__cla2a78701",
    "slw_su_l1__clcc9d0155",
):
    # Same rectangle, same CA circuit and latency: only the sequential ring cells
    # are fixed in the reserved band. Combinational ring logic goes to GPL.
    plan["partition_types"][name]["clock"]["landing_contract"]["bands"]["rsn_i"]["ring_place"] = "ff"
# PHY occupies the existing west/south/east edges of its unchanged slot.
plan["partition_types"]["coll_ucie"]["kit_core_margins_um"] = [0, 0, 0, 4.32]
# Physical placement uses the actual generated wrapper hierarchy. Logical inst,
# source RTL, pin positions and macro geometry remain unchanged.
for content in plan["partition_types"]["coll_ucie"]["contents"]:
    if content["inst"] == "u_io_ucie":
        content["physical_inst"] = "u_bound.u_io_ucie"
        content["physical_master"] = "ot_qfd_ucie_x64_phy"
# Full-wrapper mapped standard-cell totals already include CA rings, so they
# belong in type.cells rather than a by-type side table that adds rings again.
measured = json.loads((Path(__file__).parent / "synth_cells_imported.json").read_text())
for row in measured["rows"]:
    plan["partition_types"][row["type"]]["cells"] = row["stdcells"]
(PD / "plan_qc46.json").write_text(json.dumps(plan, indent=1) + "\n")
