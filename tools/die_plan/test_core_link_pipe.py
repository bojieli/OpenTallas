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
