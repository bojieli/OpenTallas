#!/usr/bin/env python3
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import view_lef as V


def pin(n, x="0", use="SIGNAL"):
    return (f"  PIN {n}\n    DIRECTION INPUT ;\n    USE {use} ;\n    PORT\n      LAYER M3 ;\n        RECT {x} 0 1 1 ;\n"
            f"    END\n  END {n}\n")


def lef(m, pins, size="10 BY 10"):
    return f"VERSION 5.8 ;\nMACRO {m}\n  CLASS BLOCK ;\n  SIZE {size} ;\n" + "".join(pins) + f"  OBS\n    LAYER M1 ;\n  END\nEND {m}\nEND LIBRARY\n"


def lib(m, bus=("r", 1, 0), scalars=("ck",)):
    n, a, b = bus
    return (f'library(x) {{\n type ("t") {{ base_type : array; bit_from : {a}; bit_to : {b}; }}\n cell("{m}") {{\n'
            f'  pg_pin(VDD) {{ }}\n  bus("{n}") {{ bus_type : t; direction : input; }}\n'
            + "".join(f'  pin("{s}") {{ direction : input; }}\n' for s in scalars) + " }\n}\n")


NARROW = [pin("r[1]"), pin("r[0]"), pin("ck"), pin("VDD", use="POWER")]
WIDE = NARROW + [pin("r[3]"), pin("r[2]"), pin("bump", use="ANALOG")]


class Base(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.d = Path(td.name)
        self.kd = self.d / "kit"
        (self.kd / "macros").mkdir(parents=True)
        self.resolve = lambda p: self.d / p
        self.lines = []

    def put(self, rel, text):
        p = self.d / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        return rel

    def stage(self, lef_rel, lib_rel):
        (self.kd / "macros" / Path(lef_rel).name).write_text((self.d / lef_rel).read_text())
        return V.stage_kit_macros(self.kd, [("u", "m", lef_rel, lib_rel, 0, 0, "R0")], self.resolve, log=self.lines.append)


class Parse(Base):
    def test_lib_bits_expand_bus_and_skip_pg(self):
        p = self.d / "a.lib"
        p.write_text(lib("m"))
        self.assertEqual(V.lib_view(p), ("m", {"r[1]", "r[0]", "ck"}))

    def test_supply_pins_in_lib_are_not_ports(self):
        p = self.d / "a.lib"
        p.write_text(lib("m", scalars=("ck", "VDD", "VSS")))
        self.assertNotIn("VDD", V.lib_view(p)[1])

    def test_unknown_bus_type_reads_as_unknown(self):
        p = self.d / "a.lib"
        p.write_text('cell(m) {\n bus(r) { bus_type : nope; }\n}\n')
        self.assertIsNone(V.lib_view(p)[1])

    def test_prune_keeps_power_analog_obs_and_other_macros(self):
        other = lef("n", [pin("r[3]")])
        new, removed = V.prune_lef_text(lef("m", WIDE) + other, "m", {"r[1]", "r[0]", "ck"})
        self.assertEqual(removed, ["r[2]", "r[3]"])
        pins, _ = V.lef_view(new, "m")
        self.assertEqual(set(pins), {"r[1]", "r[0]", "ck"})
        self.assertIn("PIN VDD", new)
        self.assertIn("PIN bump", new)
        self.assertIn("OBS", new)
        self.assertIn("r[3]", V.lef_view(new, "n")[0])


class Gen(Base):
    def test_clean_pair_silent_and_byte_identical(self):
        self.put("v/m.lef", lef("m", NARROW))
        self.put("v/m_tt.lib", lib("m"))
        self.stage("v/m.lef", "v/m_tt.lib")
        self.assertEqual(self.lines, [])
        self.assertEqual((self.kd / "macros/m.lef").read_text(), lef("m", NARROW))

    def test_no_own_lef_prunes_staged_copy_only(self):
        self.put("old/m.lef", lef("m", WIDE))
        self.put("sign/m_tt.lib", lib("m"))
        self.stage("old/m.lef", "sign/m_tt.lib")
        self.assertEqual((self.d / "old/m.lef").read_text(), lef("m", WIDE))
        pins, _ = V.lef_view((self.kd / "macros/m.lef").read_text(), "m")
        self.assertEqual(set(pins), {"r[1]", "r[0]", "ck"})
        self.assertIn('"action": "pruned 2 LEF-only pins"', self.lines[0])

    def test_own_lef_is_advisory_never_pruned(self):
        self.put("old/m.lef", lef("m", WIDE))
        self.put("v/m.lef", lef("m", [pin("r[1]", "0.5"), pin("r[0]"), pin("ck")]))
        self.put("v/m_tt.lib", lib("m"))
        self.stage("old/m.lef", "v/m_tt.lib")
        self.assertEqual((self.kd / "macros/m.lef").read_text(), lef("m", WIDE))
        row = json.loads(self.lines[0].split(" ", 1)[1])
        self.assertEqual((row["action"], row["own_lef"], row["lef_only"], row["moved"]), ("none", True, 2, 1))

    def test_prune_off_when_caller_says_so(self):
        self.put("old/m.lef", lef("m", WIDE))
        self.put("sign/m_tt.lib", lib("m"))
        (self.kd / "macros/m.lef").write_text(lef("m", WIDE))
        V.stage_kit_macros(self.kd, [("u", "m", "old/m.lef", "sign/m_tt.lib", 0, 0, "R0")], self.resolve, prune=False, log=self.lines.append)
        self.assertEqual((self.kd / "macros/m.lef").read_text(), lef("m", WIDE))

    def test_lib_only_is_reported_not_changed(self):
        self.put("old/m.lef", lef("m", [pin("r[0]"), pin("ck")]))
        self.put("sign/m_tt.lib", lib("m"))
        self.stage("old/m.lef", "sign/m_tt.lib")
        self.assertEqual(json.loads(self.lines[0].split(" ", 1)[1])["lib_only"], 1)

    def test_unreadable_view_never_stops_gen(self):
        self.put("old/m.lef", lef("m", WIDE))
        (self.kd / "macros/m.lef").write_text(lef("m", WIDE))
        out = V.stage_kit_macros(self.kd, [("u", "m", "old/m.lef", "gone/m_tt.lib", 0, 0, "R0")], self.resolve, log=self.lines.append)
        self.assertEqual(out, [])
        self.assertIn("error", self.lines[0])
        self.assertEqual((self.kd / "macros/m.lef").read_text(), lef("m", WIDE))

    def test_lib_cell_not_in_lef_keeps_copy(self):
        self.put("old/m.lef", lef("q", WIDE))
        self.put("sign/m_tt.lib", lib("m"))
        self.stage("old/m.lef", "sign/m_tt.lib")
        self.assertEqual((self.kd / "macros/m.lef").read_text(), lef("q", WIDE))
        self.assertIn("not a MACRO", self.lines[0])


class Receipt(Base):
    def setup_view(self):
        self.put("old/m.lef", lef("m", WIDE))
        self.put("sign/m_tt.lib", lib("m"))
        self.put("run/m.lef", lef("m", NARROW))
        return V.bind(self.d / "sign/m_tt.lib", self.d / "run/m.lef", "h:/s/signoff.json")

    def test_bind_files_lef_and_receipt_gen_uses_it(self):
        r = self.setup_view()
        self.assertEqual((r["pins"], r["record"]), (3, "h:/s/signoff.json"))
        self.assertEqual(V.view_lef_for("old/m.lef", "sign/m_tt.lib", self.resolve, self.lines.append), "sign/m.lef")
        self.assertIn("view LEF used", self.lines[0])

    def test_changed_lib_ignores_receipt(self):
        self.setup_view()
        self.put("sign/m_tt.lib", lib("m", bus=("r", 3, 0)))
        self.assertEqual(V.view_lef_for("old/m.lef", "sign/m_tt.lib", self.resolve, self.lines.append), "old/m.lef")
        self.assertIn("hash differs", self.lines[0])

    def test_no_receipt_no_swap_even_with_a_sibling(self):
        # legacy/lef copies carry deliberate clock-pin edits; the export beside the lib can be the older one (base566)
        self.put("v/m.lef", lef("m", NARROW))
        self.put("v/m_tt.lib", lib("m"))
        self.assertEqual(V.view_lef_for("old/m.lef", "v/m_tt.lib", self.resolve, self.lines.append), "old/m.lef")
        self.assertEqual(self.lines, [])

    def test_bind_refuses_disagreeing_pair(self):
        self.put("sign/m_tt.lib", lib("m"))
        self.put("run/m.lef", lef("m", WIDE))
        with self.assertRaises(SystemExit):
            V.bind(self.d / "sign/m_tt.lib", self.d / "run/m.lef", "r")
        self.assertFalse((self.d / "sign/m.lef").exists())


class Attach(Base):
    def test_attach_moves_lef_with_lib(self):
        self.put("v/m.lef", lef("m", NARROW))
        e = dict(lef="old/m.lef")
        self.assertEqual(V.attach(e, "v/m_tt.lib", self.resolve), "v/m.lef")
        self.assertEqual(e, dict(lef="v/m.lef", lib="v/m_tt.lib"))

    def test_attach_keeps_lef_when_view_has_none(self):
        e = dict(lef="old/m.lef")
        self.assertIsNone(V.attach(e, "prov/m_tt.lib", self.resolve))
        self.assertEqual(e, dict(lef="old/m.lef", lib="prov/m_tt.lib"))


class Plan(Base):
    def plan(self, **over):
        c = dict(inst="u", module="m", lef="old/m.lef", lib="v/m_tt.lib", origin_um=[0, 0])
        c.update(over)
        return dict(partition_types=dict(p=dict(hard_cores=[c]), q=dict(hard_cores=[dict(c, inst="u2")]), clean=dict(contents=[])))

    def test_scan_and_derived(self):
        self.put("old/m.lef", lef("m", WIDE))
        self.put("old/m_c.lef", lef("m", NARROW))
        self.put("v/m.lef", lef("m", NARROW))
        self.put("v/m_tt.lib", lib("m"))
        rows = V.scan(self.plan(), self.resolve)
        v = rows[("m", "old/m.lef", "v/m_tt.lib")]
        self.assertEqual(v["types"], {"p", "q"})
        self.assertFalse(v["derived"])
        self.assertEqual(len(v["row"]["lef_only"]), 2)
        self.assertTrue(V.scan(self.plan(lef="old/m_c.lef"), self.resolve)[("m", "old/m_c.lef", "v/m_tt.lib")]["derived"])

    def test_number_format_is_not_a_moved_pin(self):
        self.put("old/m.lef", lef("m", [pin("r[1]", "0.000"), pin("r[0]"), pin("ck")]))
        self.put("v/m.lef", lef("m", NARROW[:3]))
        self.put("v/m_tt.lib", lib("m"))
        self.assertEqual(V.scan(self.plan(), self.resolve)[("m", "old/m.lef", "v/m_tt.lib")]["row"]["moved"], [])

    def run_move(self, masters, root_extra=()):
        self.put("old/m.lef", lef("m", WIDE))
        self.put("v/m.lef", lef("m", NARROW))
        self.put("v/m_tt.lib", lib("m"))
        pi = self.d / "in.json"
        po = self.d / "out.json"
        pi.write_text(json.dumps(self.plan()))
        V.main(["move", str(pi), str(po), str(self.d), "--masters", masters])
        return json.loads(po.read_text())

    def test_move_only_named_and_only_lef(self):
        before = self.plan()
        after = self.run_move("m")
        self.assertEqual(after["partition_types"]["p"]["hard_cores"][0]["lef"], "v/m.lef")
        self.assertEqual(after["partition_types"]["q"]["hard_cores"][0]["lef"], "v/m.lef")
        after["partition_types"]["p"]["hard_cores"][0]["lef"] = "old/m.lef"
        after["partition_types"]["q"]["hard_cores"][0]["lef"] = "old/m.lef"
        self.assertEqual(after, before)

    def test_move_rejects_unknown_master(self):
        with self.assertRaises(SystemExit):
            self.run_move("nope")



def routed_lef(m="m", frag_layers=("M6",), step=1.0):
    """10x10 macro: M1-M3 solid, signal pins on M3, fragment routing (one short wire per step cell) on frag_layers"""
    obs = "".join(f"    LAYER M{i} ;\n     RECT  0 0 10 10 ;\n" for i in (1, 2, 3))
    for L in ("M4", "M5", "M6", "M7"):
        if L in frag_layers:
            obs += f"    LAYER {L} ;\n" + "".join(f"     RECT  {x + 0.1:.3f} {y + 0.1:.3f} {x + 0.4:.3f} {y + 0.132:.3f} ;\n"
                                             for x in [i * step for i in range(int(10 / step))]
                                             for y in [j * step for j in range(int(10 / step))])
    obs += "    LAYER M7 ;\n     RECT  1 1 1.2 1.032 ;\n" if "M7" not in frag_layers else ""
    return (f"VERSION 5.8 ;\nMACRO {m}\n  CLASS BLOCK ;\n  SIZE 10 BY 10 ;\n" + "".join(NARROW)
            + f"  OBS\n{obs}  END\nEND {m}\nEND LIBRARY\n")


class SolidRoutedObs(Base):
    # KV-PLAN-2 11-09: kv3_hgi_v3 GRT overflow lay inside the hard cores, whose M6/M7 OBS is their own routing fragments
    def test_fragment_layer_above_pins_becomes_one_solid_rect(self):
        t = routed_lef(frag_layers=("M6",), step=1.0)
        new, cov = V.solid_routed_obs(t, "m", grid=1.0)
        self.assertEqual(set(cov), {"M6"})
        self.assertIn("    LAYER M6 ;\n     RECT  0 0 10 10 ;\n", new)
        self.assertEqual(new.count("RECT  0 0 10 10"), 4)            # M1-M3 as exported + M6
        self.assertIn("RECT  1 1 1.2 1.032", new)                     # sparse M7 (1 of 100 cells) stays as exported
        self.assertEqual(V.lef_view(new, "m"), V.lef_view(t, "m"))     # pins and SIZE unchanged

    def test_sparse_fragments_stay(self):
        t = routed_lef(frag_layers=("M6",), step=2.0)                  # 25 of 100 cells
        self.assertEqual(V.solid_routed_obs(t, "m", grid=1.0), (t, {}))

    def test_pin_layer_and_below_keep_their_gaps(self):
        t = routed_lef(frag_layers=("M6",), step=1.0).replace("LAYER M3 ;\n     RECT  0 0 10 10 ;\n",
                                                              "LAYER M3 ;\n     RECT  0 1.1 10 10 ;\n")
        new, cov = V.solid_routed_obs(t, "m", grid=1.0)
        self.assertNotIn("M3", cov)
        self.assertIn("RECT  0 1.1 10 10", new)

    def test_solid_layer_untouched_and_clean_master_byte_identical(self):
        t = routed_lef(frag_layers=(), step=1.0)
        self.assertEqual(V.solid_routed_obs(t, "m"), (t, {}))

    def test_stage_writes_solid_copy_and_logs(self):
        lef_rel = self.put("v/m.lef", routed_lef(frag_layers=("M6", "M7"), step=1.0))
        lib_rel = self.put("v/m_tt.lib", lib("m"))
        (self.kd / "macros" / "m.lef").write_text((self.d / lef_rel).read_text())
        out = V.stage_kit_macros(self.kd, [("u", "m", lef_rel, lib_rel, 0, 0, "R0")], self.resolve,
                                 log=self.lines.append, solid=True)   # default 2.88-um grid: every cell touched
        staged = (self.kd / "macros" / "m.lef").read_text()
        self.assertEqual(staged.count("RECT  0 0 10 10"), 5)          # M1-M3 + M6 + M7
        self.assertTrue(any(l.startswith("OT_SOLID_OBS ") for l in self.lines))
        self.assertIn("solid OBS M6,M7", out[0][2])
        self.assertEqual((self.d / lef_rel).read_text().count("RECT  0 0 10 10"), 3)   # the plan LEF is never edited

    def test_stage_default_is_off_and_byte_identical(self):
        text = routed_lef(frag_layers=("M6", "M7"), step=1.0)
        lef_rel = self.put("v/m.lef", text)
        lib_rel = self.put("v/m_tt.lib", lib("m"))
        self.stage(lef_rel, lib_rel)                                   # no solid= : the pre-11-09 behaviour
        self.assertEqual((self.kd / "macros" / "m.lef").read_text(), text)
        self.assertFalse(any(l.startswith("OT_SOLID_OBS ") for l in self.lines))


if __name__ == "__main__":
    unittest.main()
