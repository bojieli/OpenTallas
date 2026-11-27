"""Install plan-declared scalar capture hold pads before native detailed placement."""
from pathlib import Path
import re
import shutil


def install(plan, type_name, kit_dir):
    rows = plan.types[type_name].get("clock", {}).get("scalar_hold_pads", ())
    if not rows:
        return []

    kit = Path(kit_dir)
    module = plan.types[type_name]["module"]
    wrapper = (kit / "rtl" / f"{module}.sv").read_text()
    seen = set()
    captures = set()
    commands = ["set ::ot_scalar_hold_pads {"]
    for row in rows:
        port = row["port"]
        capture = row["capture"]
        count = row["count"]
        declaration = rf"^\s*input\s+(?:wire\s+)?{re.escape(port)}\s*[,)]"
        if (
            not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", port)
            or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.$/]*", capture)
            or not 1 <= count <= 4
            or not re.search(declaration, wrapper, flags=re.MULTILINE)
            or port in seen
            or capture in captures
        ):
            raise ValueError(f"{type_name}: invalid or duplicate scalar hold pad {row}")
        seen.add(port)
        captures.add(capture)
        trace = "comb" if row.get("through_logic") else "buffer"
        commands.append(f"  {{{port} {{{capture}}} {count} {trace}}}")
    commands.append("}")
    (kit / "scalar_hold_pads_plan.tcl").write_text("\n".join(commands) + "\n")
    source_dir = Path(__file__).resolve().parent
    shutil.copyfile(source_dir / "scalar_hold_pads.tcl", kit / "scalar_hold_pads.tcl")
    shutil.copyfile(
        source_dir.parents[1] / "physical/common_flow/native_pg_binding.tcl",
        kit / "native_pg_binding.tcl",
    )
    sources = "source /work/scalar_hold_pads_plan.tcl\nsource /work/scalar_hold_pads.tcl\n"
    with (kit / "face_flops_release.tcl").open("a") as hook:
        hook.write("\n" + sources + "ot_scalar_hold_insert\n")
    (kit / "scalar_hold_pads_check.tcl").write_text(sources + "ot_scalar_hold_check\n")
    return ["export POST_DETAIL_PLACE_TCL = /work/scalar_hold_pads_check.tcl"]
