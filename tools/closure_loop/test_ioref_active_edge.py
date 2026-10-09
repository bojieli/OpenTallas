"""FLOW-FIX-0410 2026-10-09: io_ref_routed.sdc reads the ACTIVE-edge insertion of every boundary sink.

Real STA (OpenSTA in the ORFS image, ASAP7 RVT libraries) on four one-flop netlists, each with a 3-buffer clock tree and
a final buffer or inverter in front of the flop:
  buf + DFFHQN (posedge)            insertion = rise arrival from the source rise edge (unchanged)
  buf + DFFLQN (negedge)            insertion = fall arrival from the source fall edge - T/2
  inv + DFFLQN (ot_fwd_link_stage)  insertion = fall arrival from the source rise edge   (pre-0410: T/2 + tree)
  inv + DFFHQN                      insertion = rise arrival from the source fall edge - T/2 (pre-0410: T/2 + tree)
in a single-corner session (TT) and in the route-time two-scene session (orfs_hold_mm: WC = TT, BC = FF, the FF SDCs
read with ::ot_ioref_scene BC).  The expected value comes from report_arrival of the specific source edge, the
measured one from the "OT_IOREF vclk core_clk mean" line.

OT_IOREF_DOCKER_IMAGE overrides the image (default openroad/orfs:latest); skipped when docker or the image is missing.
"""
import os, re, shutil, subprocess, tempfile, unittest
from pathlib import Path

SDC = Path(__file__).resolve().parents[2] / "physical/common_flow/io_ref_routed.sdc"
IMAGE = os.environ.get("OT_IOREF_DOCKER_IMAGE", "openroad/orfs:latest")
STA = "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/sta"
T = 833.333

NET = """module top(ck, d, q);
  input ck; input d; output q;
  wire c1, c2, c3, cs, qn;
  BUFx2_ASAP7_75t_R b1(.A(ck), .Y(c1));
  BUFx2_ASAP7_75t_R b2(.A(c1), .Y(c2));
  BUFx2_ASAP7_75t_R b3(.A(c2), .Y(c3));
  {last}(.A(c3), .Y(cs));
  {flop} f(.CLK(cs), .D(d), .QN(qn));
  INVx1_ASAP7_75t_R o(.A(qn), .Y(q));
endmodule
"""
CASES = {
    # name: (last clock cell, flop, source edge of the active transition, active transition)
    "buf_pos": ("BUFx2_ASAP7_75t_R b4", "DFFHQNx1_ASAP7_75t_R", "^", "r"),
    "buf_neg": ("BUFx2_ASAP7_75t_R b4", "DFFLQNx1_ASAP7_75t_R", "v", "f"),
    "inv_neg": ("INVx2_ASAP7_75t_R i1", "DFFLQNx1_ASAP7_75t_R", "^", "f"),
    "inv_pos": ("INVx2_ASAP7_75t_R i1", "DFFHQNx1_ASAP7_75t_R", "v", "r"),
}
CLOCK_SDC = f"""create_clock -name core_clk -period {T} [get_ports ck]
create_clock -name vclk -period {T}
set_propagated_clock [get_clocks core_clk]
set_input_delay 100 -clock vclk [get_ports d]
set_output_delay 100 -clock vclk [get_ports q]
"""
RUN = """set L /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
proc libs {c} { global L; return [list $L/asap7sc7p5t_SEQ_RVT_${c}_nldm_220123.lib [lindex [glob $L/asap7sc7p5t_INVBUF_RVT_${c}_nldm_*.lib*] 0]] }
set mode $::env(MODE)
if {$mode eq "mm"} {
  foreach c {TT FF} { foreach l [libs $c] { read_liberty $l } }
} else { foreach l [libs $mode] { read_liberty $l } }
read_verilog /w/net.v
link_design top
if {$mode eq "mm"} {
  read_sdc -mode ss /w/clk.sdc
  read_sdc -mode ff /w/clk.sdc
  define_scene WC -mode ss -liberty [libs TT]
  define_scene BC -mode ff -liberty [libs FF]
  set_mode ff
  set ::ot_ioref_scene BC
  set sc [list -scene BC]
} else { read_sdc /w/clk.sdc; set sc {} }
set p [get_pins f/CLK]
sta::redirect_string_begin
report_arrival {*}$sc -digits 4 $p
puts "REF [string map [list "\\n" " | "] [sta::redirect_string_end]]"
source /w/io_ref_routed.sdc
"""


def have_image():
    if not shutil.which("docker"):
        return False
    return subprocess.run(["docker", "image", "inspect", IMAGE], capture_output=True).returncode == 0


def run_case(name, mode, sdc=SDC, extra=""):
    last, flop, _, _ = CASES[name]
    with tempfile.TemporaryDirectory(prefix="ioref_ae_") as d:
        Path(d, "net.v").write_text(NET.format(last=last, flop=flop))
        Path(d, "clk.sdc").write_text(CLOCK_SDC)
        Path(d, "run.tcl").write_text(RUN + extra)
        shutil.copy(sdc, Path(d, "io_ref_routed.sdc"))
        os.chmod(d, 0o755)
        r = subprocess.run(["docker", "run", "--rm", "-v", f"{d}:/w", "-e", f"MODE={mode}", IMAGE,
                            STA, "-no_init", "-no_splash", "-exit", "/w/run.tcl"],
                           capture_output=True, text=True, timeout=600)
    out = r.stdout + r.stderr
    m = re.search(r"OT_IOREF vclk core_clk mean (\S+) min \S+ max \S+ n (\d+) (\w+)", out)
    ref = {}
    for ck, e, rv, fv in re.findall(r"\((\S+) ([\^v])\)\s+r\s+(\S+)\s+f\s+(\S+)", out.split("REF", 1)[1] if "REF" in out else ""):
        for tr, v in (("r", rv), ("f", fv)):
            x = v.split(":")[-1]
            if re.fullmatch(r"-?[0-9.]+", x):
                ref[(e, tr)] = float(x)
    edge = re.search(r"OT_IOREF_EDGE core_clk boundary (\d+) negedge (\d+) noarc (\d+) inverted (\d+)", out)
    return out, (float(m.group(1)) if m else None), ref, edge


@unittest.skipUnless(have_image(), f"docker image {IMAGE} not available")
class IorefActiveEdge(unittest.TestCase):
    def check(self, name, mode):
        out, got, ref, edge = run_case(name, mode)
        self.assertIsNotNone(got, out[-3000:])
        _, _, e, tr = CASES[name]
        want = ref[(e, tr)] - (T / 2 if e == "v" else 0.0)
        self.assertAlmostEqual(got, want, delta=0.11, msg=f"{name} {mode}: {out[-1500:]}")
        self.assertLess(got, T / 4, f"{name} {mode}: insertion must be the tree, not T/2 + tree")
        self.assertIsNotNone(edge, out[-1500:])
        n, neg, noarc, inv = map(int, edge.groups())
        self.assertEqual((n, neg, noarc, inv), (1, int(tr == "f"), 0, int(e == "v")))
        return got

    def test_single_corner(self):
        for name in CASES:
            with self.subTest(name=name):
                self.check(name, "TT")

    def test_multi_scene_reads_the_ff_scene(self):
        for name in CASES:
            with self.subTest(name=name):
                mm = self.check(name, "mm")
                _, ff, _, _ = run_case(name, "FF")
                _, tt, _, _ = run_case(name, "TT")
                self.assertAlmostEqual(mm, ff, delta=0.11)
                self.assertGreater(tt - ff, 1.0)

    def test_posedge_unchanged_from_pre_0410(self):
        old = subprocess.run(["git", "show", "7dc926e71:physical/common_flow/io_ref_routed.sdc"], cwd=SDC.parent,
                             capture_output=True, text=True)
        if old.returncode:
            self.skipTest("pre-0410 io_ref_routed.sdc not in this clone")
        with tempfile.NamedTemporaryFile("w", suffix=".sdc", delete=False) as f:
            f.write(old.stdout)
        try:
            for mode in ("TT", "mm"):
                _, before, _, _ = run_case("buf_pos", mode, sdc=f.name)
                _, after, _, _ = run_case("buf_pos", mode)
                self.assertAlmostEqual(before, after, delta=0.051)
                # the defect the fix removes: behind the inverter the old reading is T/2 late
                _, bad, _, _ = run_case("inv_neg", mode, sdc=f.name)
                _, good, _, _ = run_case("inv_neg", mode)
                self.assertAlmostEqual(bad - good, T / 2, delta=T / 8)
        finally:
            os.unlink(f.name)

    def test_ck_insertion_calibrate_uses_the_same_rule(self):
        import sys
        sys.path.insert(0, str(Path(__file__).parent))
        import ck_insertion
        extra = ck_insertion.ACTIVE_TCL + 'puts "OT_CK_TEST [ot_ck_arr [get_pins f/CLK] [lindex [get_clocks core_clk] 0]]"\n'
        for name in CASES:
            with self.subTest(name=name):
                out, ioref, ref, _ = run_case(name, "TT", extra=extra)
                m = re.search(r"OT_CK_TEST (\S+)", out)
                self.assertIsNotNone(m, out[-1500:])
                _, _, e, tr = CASES[name]
                self.assertAlmostEqual(float(m.group(1)), ref[(e, tr)] - (T / 2 if e == "v" else 0.0), delta=0.11)
                self.assertAlmostEqual(float(m.group(1)), ioref, delta=0.06)


if __name__ == "__main__":
    unittest.main()
