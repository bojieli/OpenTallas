"""Stricter signal routing never weakens PG, production geometry, or export."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ref_tile as RT
import pre_route_gate as G
spec = importlib.util.spec_from_file_location("strict_view_export", HERE.parent / "tt_views/view_export.py")
VE = importlib.util.module_from_spec(spec)
spec.loader.exec_module(VE)


def tile(**kw):
    data = json.loads((HERE / "examples/nhb_pbst_ref.json").read_text())
    data.update(name="signal_cap_test_new", **kw)
    with tempfile.NamedTemporaryFile("w", suffix=".json") as f:
        json.dump(data, f); f.flush()
        return RT.load_spec(f.name)


class SignalCap(unittest.TestCase):
    def test_generated_m4_kit_gate_and_tamper_rejection(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "spec.json"
            source.write_text(json.dumps(tile(signal_max_layer="M4")))
            kit = root / RT.gen(str(source), out_root=root)["kit"]
            gate = G.Gate()
            G.check_kit(gate, kit, None)
            self.assertFalse(any(x["check"] == "layer" and x["severity"] == "FAIL" for x in gate.items))
            path = kit / "kit.env"
            original = path.read_text()
            path.write_text(original.replace("CLOCK_RLAYERS='M3 M4'", "CLOCK_RLAYERS='M4 M4'"))
            gate = G.Gate()
            G.check_kit(gate, kit, None)
            self.assertTrue(any(x["check"] == "layer" and x["severity"] == "FAIL" for x in gate.items))
            path.write_text(original.replace("RLAYERS='M2 M4'", "RLAYERS='M2 M5'"))
            gate = G.Gate()
            G.check_kit(gate, kit, None)
            self.assertTrue(any(x["check"] == "layer" and x["severity"] == "FAIL" for x in gate.items))

    def test_default_unchanged_and_stricter_cap_keeps_power(self):
        base = RT.layer_contract(tile(), None)
        self.assertEqual((base["pg_layer"], base["rlayers"], base["strap_layer"]),
                         ("M5", ("M2", "M5"), "M6"))
        s = tile(signal_max_layer="M4")
        lc = RT.layer_contract(s, None)
        self.assertEqual((lc["pg_layer"], lc["rlayers"], lc["strap_layer"]),
                         ("M5", ("M2", "M4"), "M6"))
        self.assertEqual(RT.pin_layers(s, lc), ("M4", "M3"))
        env = RT.gen_env(s, "kit", 220.32, 75.6, lc, [])
        self.assertIn("RLAYERS='M2 M4'", env)
        self.assertIn("CLOCK_RLAYERS='M3 M4'", env)
        legacy = tile()
        self.assertNotIn("CLOCK_RLAYERS", RT.gen_env(legacy, "kit", 220.32, 75.6, base, []))
        self.assertIn("-layers {M4 M5}", RT.gen_pdn(s, lc))
        self.assertIn("signal_layer_audit.tcl", RT.gen_hooks(s, "kit")["post_drt.tcl"])

    def test_route_and_gate_stop_forward_exact_clock_limits(self):
        # Execute the actual shared route shell with only the heavy driver stubbed.
        # This is also the path used by pre_route_gate's floorplan/CTS stops.
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "tools").mkdir()
            (root / "tools/run_abi3_physical.py").write_text(
                "import json, os, sys\nopen(os.environ['CAPTURE'], 'w').write(json.dumps(sys.argv[1:]))\n")
            kit = root / "kit.env"
            base = "TOP=t\nSRCS=''\nPARAMS=()\nPINS=()\nEXTRA=()\nMACROS=()\nFW=100\nFH=100\nKIT=/src/kit\nCLKPORT=ck\nPIN_H=M4\nPIN_V=M3\nREFGLOB='*'\nINTER=none\n"
            for cap in ("M4", "M5"):
                kit.write_text(base + f"RLAYERS='M2 {cap}'\n" +
                               ("CLOCK_RLAYERS='M3 M4'\n" if cap == "M4" else ""))
                capture = root / "args.json"
                env = dict(os.environ, SRC=str(root), CAPTURE=str(capture))
                subprocess.run(["bash", str(HERE / "ref_route.sh"), str(kit), "smoke", str(root / "out"), "floorplan"],
                               env=env, check=True, capture_output=True)
                args = json.loads(capture.read_text())
                self.assertIn("floorplan", args)
                for name in ("MIN_CLK_ROUTING_LAYER", "MAX_CLK_ROUTING_LAYER"):
                    self.assertEqual([a for a in args if a.startswith(name + "=")],
                                     [{"MIN_CLK_ROUTING_LAYER": "MIN_CLK_ROUTING_LAYER=M3", "MAX_CLK_ROUTING_LAYER": "MAX_CLK_ROUTING_LAYER=M4"}[name]] if cap == "M4" else [])

    def test_no_looser_cap_or_high_signal_pin(self):
        for cap in ("M6", "M7", "M1", "invalid"):
            with self.assertRaises(RT.SpecError):
                RT.layer_contract(tile(signal_max_layer=cap), None)
        s = tile(signal_max_layer="M5")
        with self.assertRaises(RT.SpecError):
            RT.layer_contract(s, {"layer_cap": "M5", "signal_max_layer": "M4"})
        s = tile(signal_max_layer="M4", route={"pin_h": "M5"})
        with self.assertRaises(RT.SpecError):
            RT.pin_layers(s, RT.layer_contract(s, None))

    def test_small_tile_is_a_probe_only(self):
        s = tile()
        s["pins"] = {"N": ["ck"], "S": [], "W": [], "E": []}
        block = dict(kind="macro", master="small", idx=0, x=10, y=10,
                     w=30, h=30, offtrack=0, orient="R0")
        base = RT.floorplan_checks(s, 60, 60, [block], None)
        self.assertTrue(any(sev == "FAIL" and check == "macro_edge" for sev, check, *_ in base))
        s["abut_plan"] = dict(channel_um=5.4, edge_um=5.4, why="official diagnostic pin candidate")
        denied = RT.floorplan_checks(s, 60, 60, [block], None)
        self.assertTrue(any(sev == "FAIL" for sev, *_ in denied))
        s["job"]["hold_merge"] = "diagnostic geometry, never native closure"
        probe = RT.floorplan_checks(s, 60, 60, [block], None)
        self.assertFalse(any(sev == "FAIL" for sev, *_ in probe))
        self.assertTrue(any(check == "abut_plan" for _, check, *_ in probe))
        s.pop("abut_plan")
        self.assertTrue(any(sev == "FAIL" for sev, *_ in RT.floorplan_checks(s, 60, 60, [block], None)))

    def test_abstract_high_metal_requires_actual_pg_and_never_signal_pins(self):
        lef = """MACRO x
 PIN data
  USE SIGNAL ;
  PORT
   LAYER M4 ;
   RECT 0 0 1 1 ;
  END
 END data
 OBS
  LAYER M5 ;
  RECT 0 0 1 1 ;
 END
END x
"""
        route = dict(schema="opentallas.ref_tile.routed-signal-cap.v1", signal_cap="M4", pg_cap="M5",
                     non_pg_layers={"M4": 20}, pg_layers={"M5": 3}, violations={})
        self.assertEqual(VE.audit_signal_abstract(lef, "M4", "M5", route)["pg_backed_high_obs_layers"], ["M5"])
        with self.assertRaises(VE.VerdictError):
            VE.audit_signal_abstract(lef.replace("LAYER M4", "LAYER M5"), "M4", "M5", route)
        with self.assertRaises(VE.VerdictError):
            VE.audit_signal_abstract(lef.replace("LAYER M5", "LAYER M6"), "M4", "M5", route)
        for field, value in (("pg_layers", {}), ("non_pg_layers", {"M5": 1}),
                             ("violations", {"CLOCK:M5": 1})):
            bad = dict(route, **{field: value})
            with self.assertRaises(VE.VerdictError):
                VE.audit_signal_abstract(lef, "M4", "M5", bad)

    def test_actual_net_type_audit_includes_clock_and_via(self):
        helper = (HERE / "signal_layer_audit.tcl").read_text()
        # Exercise the real Tcl audit with a small OpenDB API double: powerM5
        # is legal, the same routed metal on signal/clock or a signal via fails.
        for kind, via, special, legal in (("POWER",0,0,True),("SIGNAL",0,0,False),
                                          ("CLOCK",0,0,False),("SIGNAL",1,0,False),
                                          ("POWER",0,1,True),("SIGNAL",0,1,False)):
            with tempfile.TemporaryDirectory() as td:
                report = str(Path(td) / "audit.json")
                tcl = '''namespace eval ord {};namespace eval odb {}
proc ord::get_db_tech {} {return tech}
proc ord::get_db_block {} {return block}
proc tech {m l} {return $l}
foreach {n level} {M4 4 M5 5} {
 proc $n {m} [string map [list @N $n @L $level] {if {$m eq "getName"} {return @N};return @L}]
}
proc block {m} {if {$m eq "getNets"} {return net};return {}}
proc net {m} {if {$m eq "getSigType"} {return @K};if {$m eq "getWire"} {return wire};return {}}
set odb::dbWireDecoder_END_DECODE 0;set odb::dbWireDecoder_POINT 1
set odb::dbWireDecoder_POINT_EXT 2;set odb::dbWireDecoder_TECH_VIA 3;set odb::dbWireDecoder_VIA 4
proc odb::dbWireDecoder {} {set ::seq [list @OP 0];return dec}
proc dec {m args} {
 if {$m eq "next"} {set x [lindex $::seq 0];set ::seq [lrange $::seq 1 end];return $x}
 if {$m eq "getLayer"} {return M5}
 if {$m eq "getTechVia"} {return via}
}
proc via {m} {return box}
proc box {m} {if {$m eq "isVia"} {return 0};return M5}
proc sw {m} {return box}
'''.replace("@K", kind).replace("@OP", "3" if via else "1")
                if special:
                    tcl = tcl.replace('if {$m eq "getWire"} {return wire};return {}',
                                      'if {$m eq "getWire"} {return NULL};return sw')
                code = tcl + helper + f'\nset rc [catch {{ot_ref_audit_signal_layers M4 M5 {{{report}}}}} msg]\nputs "RC=$rc"\n'
                proc = subprocess.run(["tclsh"], input=code, text=True, capture_output=True)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertIn("RC=0" if legal else "RC=1", proc.stdout)
                result = json.loads(Path(report).read_text())
                self.assertEqual(bool(result["violations"]), not legal)


if __name__ == "__main__":
    unittest.main()
