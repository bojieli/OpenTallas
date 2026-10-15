"""Real OpenROAD: the clock routing range ref_tile emits for a signal cap below M5 is accepted
(root shared-flow fix 2026-10-14, S81 dsfd_vm_static_bank128_m4_v20 gate died at floorplan with
ODB-0137 because ASAP7 routes clocks on MIN_CLK_ROUTING_LAYER=M4..MAX_ROUTING_LAYER=M4).
The mutant (single-layer range M4-M4, as first proposed) must reproduce ODB-0137.
Skipped when docker or the ORFS image is not available."""
import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
IMAGE = "openroad/orfs:latest"
OR = "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad"
spec = importlib.util.spec_from_file_location("ref_tile", HERE.parent / "ref_tile.py")
RT = importlib.util.module_from_spec(spec)
sys.path.insert(0, str(HERE.parent.parent))
spec.loader.exec_module(RT)

TCL = """set P /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $P/lef/asap7_tech_1x_201209.lef
read_lef $P/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_liberty $P/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz
read_verilog /w/t.v
link_design t
initialize_floorplan -die_area {0 0 20 20} -core_area {2 2 18 18} -site asap7sc7p5t
source $P/openRoad/make_tracks.tcl
foreach r {%s} {
  if {[catch {set_routing_layers -clock $r -signal M2-%s} e]} { puts "RANGE $r ERR" } else { puts "RANGE $r OK" }
}
"""


def docker_ok():
    if not shutil.which("docker"):
        return False
    return subprocess.run(["docker", "image", "inspect", IMAGE], capture_output=True).returncode == 0


def probe(ranges, cap):
    with tempfile.TemporaryDirectory() as td:
        Path(td, "t.v").write_text("module t(input a, output y); INVx1_ASAP7_75t_R u(.A(a),.Y(y)); endmodule\n")
        Path(td, "p.tcl").write_text(TCL % (" ".join(ranges), cap))
        r = subprocess.run(["docker", "run", "--rm", "-v", f"{td}:/w", IMAGE, OR, "-exit", "/w/p.tcl"],
                           capture_output=True, text=True, timeout=300)
        out = r.stdout + r.stderr
        return {ln.split()[1]: ln.split()[2] for ln in out.splitlines() if ln.startswith("RANGE ")}, out


@unittest.skipUnless(docker_ok(), "docker + ORFS image needed")
class ClockLayerRange(unittest.TestCase):
    def test_emitted_range_routes_and_single_layer_mutant_fails(self):
        for cap in ("M3", "M4"):
            lo, hi = RT.clock_rlayers({"rlayers": ("M2", cap)})
            res, out = probe([f"{lo}-{hi}", f"{cap}-{cap}", f"M4-{cap}" if cap == "M3" else "M5-M4"], cap)
            self.assertEqual(res.get(f"{lo}-{hi}"), "OK", out)
            self.assertEqual(res.get(f"{cap}-{cap}"), "ERR", out)   # mutant: single-layer range
        self.assertIsNone(RT.clock_rlayers({"rlayers": ("M2", "M5")}))
        with self.assertRaises(RT.SpecError):
            RT.clock_rlayers({"rlayers": ("M2", "M2")})


if __name__ == "__main__":
    unittest.main()
