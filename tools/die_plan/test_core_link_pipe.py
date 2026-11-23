"""KV-PVGEN 11-15: plan clock.core_link_pipe puts declared ot_dp_dly stages on named core input ports (default off)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bind  # noqa: E402

MODS = {"ot_qwen_tp8_pv_join_t": {"ts0": 2, "ts1": 2, "join_go": 2}}


class CoreLinkPipe(unittest.TestCase):
    def test_absent_is_off(self):
        self.assertEqual(bind.core_link_pipe({}, "kv3_pv_v1n", "ot_qwen_tp8_pv_join_t", "ts0"), 0)
        self.assertEqual(bind.core_link_pipe({"clock": {}}, "kv3_pv_v1n", "ot_qwen_tp8_pv_join_t", "ts0"), 0)

    def test_types_and_ports(self):
        p = {"clock": {"core_link_pipe": {"modules": MODS, "types": ["kv3_pv_v1n"]}}}
        self.assertEqual(bind.core_link_pipe(p, "kv3_pv_v1n", "ot_qwen_tp8_pv_join_t", "ts0"), 2)
        self.assertEqual(bind.core_link_pipe(p, "kv3_pv_v1n", "ot_qwen_tp8_pv_join_t", "ts3"), 0)   # port not listed
        self.assertEqual(bind.core_link_pipe(p, "kv3_pv_v2n", "ot_qwen_tp8_pv_join_t", "ts0"), 0)   # type not listed
        self.assertEqual(bind.core_link_pipe(p, "kv3_pv_v1n", "ot_qwen_tp8_pv_slice_t", "ts0"), 0)  # module not listed

    def test_all_except(self):
        p = {"clock": {"core_link_pipe": {"modules": MODS, "all": True, "except": ["kv3_pv_v2n"]}}}
        self.assertEqual(bind.core_link_pipe(p, "kv3_pv_v1n", "ot_qwen_tp8_pv_join_t", "join_go"), 2)
        self.assertEqual(bind.core_link_pipe(p, "kv3_pv_v2n", "ot_qwen_tp8_pv_join_t", "join_go"), 0)

    def test_emit_is_declared_and_default_off(self):
        src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "bind.py")).read()
        self.assertIn("u_pc_lp_", src)
        self.assertIn("core_link_pipe_bits(self.plan, tn, c.module, pn, len(bits))", src)
        # the declaration goes through the shared record read by bind_verify / LATCHECK / compiler
        self.assertIn("self.declare_core_input_pipe(tn, p, ci, pn, depth", src)

    def test_keep_option(self):
        """FAM-KV-IOPC-R4 11-22: core_link_pipe.keep emits the kept module (no yosys merge with an identical consumer flop); default off"""
        import schema
        src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "bind.py")).read()
        self.assertIn('.get("core_link_pipe") or {}).get("keep")', src)
        node = schema.SCHEMA["properties"]["clock"]["properties"]["core_link_pipe"]
        self.assertEqual(node["properties"]["keep"], {"type": "boolean"})

    def test_schema(self):
        import schema
        node = schema.SCHEMA["properties"]["clock"]["properties"]["core_link_pipe"]
        self.assertFalse(node["additionalProperties"])
        self.assertIn("anyOf", node["properties"]["modules"]["additionalProperties"]["additionalProperties"])

    def test_bit_runs(self):
        mods = {"qkd_rlyi_258s": {"y": [{"D": 3, "bits": [0, 255]}]}, "j": {"ts0": 2}}
        p = {"clock": {"core_link_pipe": {"modules": mods, "types": ["t"]}}}
        d = bind.core_link_pipe_bits(p, "t", "qkd_rlyi_258s", "y", 258)
        self.assertEqual(d[:256], [3] * 256)
        self.assertEqual(d[256:], [0, 0])               # epoch / spare bits stay untouched
        self.assertEqual(bind.core_link_pipe_bits(p, "t", "j", "ts0", 4), [2] * 4)
        self.assertEqual(bind.core_link_pipe_bits(p, "t", "j", "other", 4), [0] * 4)
        with self.assertRaises(bind.BindError):
            bind.core_link_pipe_bits(p, "t", "qkd_rlyi_258s", "y", 100)
        dup = {"clock": {"core_link_pipe": {"modules": {"m": {"y": [{"D": 1, "bits": [0, 3]}, {"D": 2, "bits": [3, 5]}]}}, "all": True}}}
        with self.assertRaises(bind.BindError):
            bind.core_link_pipe_bits(dup, "t", "m", "y", 8)

    def test_source_side_depth(self):
        """family 4: depth follows the DRIVER module/port/bit, applied at each sink; port-level specs are independent"""
        p = {"clock": {"core_link_pipe": {"types": ["t"], "sources": {"qkd_pv16_vport_b": {
            "out_v_lo": [{"D": 3, "bits": [0, 255]}], "out_v_hi": 2}}}}}
        self.assertEqual(bind.core_link_src_depth(p, "t", "qkd_pv16_vport_b", "out_v_lo", 0), 3)
        self.assertEqual(bind.core_link_src_depth(p, "t", "qkd_pv16_vport_b", "out_v_lo", 255), 3)
        self.assertEqual(bind.core_link_src_depth(p, "t", "qkd_pv16_vport_b", "out_v_lo", 256), 0)
        self.assertEqual(bind.core_link_src_depth(p, "t", "qkd_pv16_vport_b", "out_v_hi", 511), 2)
        self.assertEqual(bind.core_link_src_depth(p, "t", "qkd_pv16_vport_b", "out_t", 0), 0)
        self.assertEqual(bind.core_link_src_depth(p, "u", "qkd_pv16_vport_b", "out_v_lo", 0), 0)
        self.assertEqual(bind.core_link_pipe(p, "t", "qkd_pv16_vport_b", "out_v_lo"), 0)   # not a port-level pipe
        import jsonschema, schema
        jsonschema.validate(p["clock"]["core_link_pipe"], schema.SCHEMA["properties"]["clock"]["properties"]["core_link_pipe"])

    def test_lp_even_hook_selection_and_tcl(self):
        """FIRM sites for the stages: gen_phys wires lp_even.tcl only for types with core_link_pipe; the Tcl parses"""
        import shutil, subprocess
        import gen_phys
        raw = {"clock": {"core_link_pipe": {"types": ["t"], "modules": {"m": {"a": 1}}}}}
        self.assertTrue(gen_phys.core_link_pipe_place(raw, "t"))
        self.assertFalse(gen_phys.core_link_pipe_place(raw, "u"))
        self.assertFalse(gen_phys.core_link_pipe_place({}, "t"))
        self.assertTrue(gen_phys.core_link_pipe_place({"clock": {"core_link_pipe": {"all": True, "except": ["u"], "modules": {"m": {"a": 1}}}}}, "t"))
        d = os.path.dirname(os.path.abspath(__file__))
        src = open(os.path.join(d, "lp_even.tcl")).read()
        self.assertIn("u_pc_lp_", src)
        self.assertIn("(j+1)", src.replace("$j+1", "j+1"))
        if shutil.which("tclsh"):
            r = subprocess.run(["tclsh"], input="set f [open " + os.path.join(d, "lp_even.tcl") + "]; set s [read $f]; "
                               "if {![info complete $s]} {exit 3}", capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_schema_validates_forms(self):
        import jsonschema, schema
        node = schema.SCHEMA["properties"]["clock"]["properties"]["core_link_pipe"]
        ok = {"types": ["t"], "modules": {"m": {"a": 2, "y": [{"D": 3, "bits": [0, 255]}], "z": {"D": 1, "bits": [0, 3]}}}}
        jsonschema.validate(ok, node)
        for bad in ({"types": ["t"], "modules": {"m": {"a": 9}}}, {"types": ["t"]}, {"modules": {"m": {"a": 0}}}):
            with self.assertRaises(jsonschema.ValidationError):
                jsonschema.validate(bad, node)


if __name__ == "__main__":
    unittest.main()
