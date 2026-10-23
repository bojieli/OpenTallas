"""custom_io_faces reads the canonical ot_assigned_pin_exact literal-bit IO (stream t3e/t3f, SQC-CB16b 2026-10-22)."""
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import custom_io_faces as IO

HELPER = "proc ot_assigned_pin_exact {name layer face center_um} {\n    # fixture helper body\n}\n"
KIT = ("FW=259.2\nFH=907.2\n"
       "EXTRA=('--orfs-var' 'IO_CONSTRAINTS=/src/physical/ref_tile/k/io.tcl')\n")
T3E_HEAD = ("# E-row R0 variant: W<->E face swap\n"
            "source /src/physical/common_flow/assigned_pin_exact.tcl\n"
            "ot_assigned_pin_exact {cfg_dir[0]} M3 N 132.309000\n"
            "ot_assigned_pin_exact {cfg_dir[1]} M5 N 131.676000\n"
            "ot_assigned_pin_exact {so_w[0]} M4 E 200.016000\n"
            "ot_assigned_pin_exact {sw_lo[0]} M4 W 4.032000\n"
            "ot_assigned_pin_exact {rst_n} M3 S 12.051000\n")


def store(io, helper=HELPER):
    files = {"physical/ref_tile/k/io.tcl": io}
    if helper is not None:
        files[IO.ASSIGNED_PIN_EXACT_TCL] = helper
    return lambda commit, path: files.get(path)


class ExactAssignments(unittest.TestCase):
    def test_sourced_helper_reads_literal_faces(self):
        r = IO.read(KIT, "c", store(T3E_HEAD))
        self.assertEqual(r["status"], "verified", r)
        self.assertEqual(r["faces"], {"cfg_dir[0]": "N", "cfg_dir[1]": "N", "so_w[0]": "E", "sw_lo[0]": "W",
                                      "rst_n": "S"})

    def test_inlined_helper_reads_literal_faces(self):
        body = T3E_HEAD.replace("source /src/physical/common_flow/assigned_pin_exact.tcl\n", "")
        r = IO.read(KIT, "c", store(HELPER + body))
        self.assertEqual(r["status"], "verified", r)
        self.assertEqual(len(r["faces"]), 5)

    def test_mirror_is_a_face_change(self):
        swapped = T3E_HEAD.replace(" M4 E ", " M4 X ").replace(" M4 W ", " M4 E ").replace(" M4 X ", " M4 W ")
        a, b = IO.read(KIT, "c", store(T3E_HEAD)), IO.read(KIT, "c", store(swapped))
        cmp = IO.compare(a, b)
        self.assertEqual(cmp["status"], "changed", cmp)
        self.assertEqual(cmp["changed_pins"], 2)
        self.assertEqual(IO.compare(a, a)["status"], "same")

    def test_refusals(self):
        no_src = T3E_HEAD.replace("source /src/physical/common_flow/assigned_pin_exact.tcl\n", "")
        self.assertEqual(IO.read(KIT, "c", store(no_src))["status"], "error")           # no helper
        self.assertEqual(IO.read(KIT, "c", store(T3E_HEAD, helper=None))["status"], "error")  # helper not pinned
        dup = T3E_HEAD + "ot_assigned_pin_exact {rst_n} M3 S 13.0\n"
        self.assertIn("duplicate", IO.read(KIT, "c", store(dup))["error"])
        out = T3E_HEAD + "ot_assigned_pin_exact {x} M3 N 300.0\n"
        self.assertIn("outside", IO.read(KIT, "c", store(out))["error"])
        bad = T3E_HEAD + "ot_assigned_pin_exact {y} M3 Q 3.0\n"
        self.assertIn("unsupported", IO.read(KIT, "c", store(bad))["error"])
        prog = T3E_HEAD + "foreach p $pins { ot_assigned_pin_exact $p M3 N 1.0 }\n"
        self.assertIn("unsupported", IO.read(KIT, "c", store(prog))["error"])


class ActualStreamKits(unittest.TestCase):
    """the actual t3e/t3f kits at their pushed commit (skipped where the object is absent)."""
    def test_actual_t3e_t3f(self):
        root = HERE.parents[1]

        def show(commit, path):
            p = subprocess.run(["git", "-C", str(root), "show", f"{commit}:{path}"], capture_output=True, text=True)
            return p.stdout if p.returncode == 0 else None
        for k in ("t3e", "t3f"):
            kit = show("37ce10189", f"physical/ref_tile/qfd_dv_stream_{k}_1022/kit.env")
            if kit is None:
                self.skipTest("37ce10189 not in this clone")
            r = IO.read(kit, "37ce10189", show)
            self.assertEqual(r["status"], "verified", r)
            self.assertEqual(r["pins"], 6947)


if __name__ == "__main__":
    unittest.main()
