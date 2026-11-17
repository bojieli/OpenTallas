"""QC-NK-HOLD 11-11: plan clock.core_input_lockup selects the hard-core data-input ports that get ot_dp_lk."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bind  # noqa: E402

MODS = {"qfd_tile_nk_a0c": ["n_a", "n_b", "tap"]}


class CoreInputLockup(unittest.TestCase):
    def test_absent_is_off(self):
        self.assertEqual(bind.core_input_lockup({}, "cbn_q11", "qfd_tile_nk_a0c"), ())
        self.assertEqual(bind.core_input_lockup({"clock": {}}, "cbn_q11", "qfd_tile_nk_a0c"), ())

    def test_types_list(self):
        p = {"clock": {"core_input_lockup": {"modules": MODS, "types": ["cbn_q11"]}}}
        self.assertEqual(bind.core_input_lockup(p, "cbn_q11", "qfd_tile_nk_a0c"), ("n_a", "n_b", "tap"))
        self.assertEqual(bind.core_input_lockup(p, "cbn_q00", "qfd_tile_nk_a0c"), ())
        self.assertEqual(bind.core_input_lockup(p, "cbn_q11", "qfd_tile_nl_a0c"), ())

    def test_all_except(self):
        p = {"clock": {"core_input_lockup": {"modules": MODS, "all": True, "except": ["tt_ctlm"]}}}
        self.assertEqual(bind.core_input_lockup(p, "cbf_q00_s2", "qfd_tile_nk_a0c"), ("n_a", "n_b", "tap"))
        self.assertEqual(bind.core_input_lockup(p, "tt_ctlm", "qfd_tile_nk_a0c"), ())

    def test_pipe_depth(self):
        base = {"modules": MODS, "types": ["cbn_q11"]}
        self.assertEqual(bind.core_input_pipe({"clock": {"core_input_lockup": base}}, "cbn_q11", "qfd_tile_nk_a0c"), 0)
        p = {"clock": {"core_input_lockup": dict(base, pipe=1)}}
        self.assertEqual(bind.core_input_pipe(p, "cbn_q11", "qfd_tile_nk_a0c"), 1)
        self.assertEqual(bind.core_input_pipe(p, "cbn_q00", "qfd_tile_nk_a0c"), 0)
        self.assertEqual(bind.core_input_pipe(p, "cbn_q11", "qfd_tile_nl_a0c"), 0)

    def test_verify_declares_the_pipe_stage(self):
        src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "bind_verify.py")).read()
        self.assertIn("bind_core_input_pipe.json", src)
        self.assertIn('{"module": "ot_dp_dly", "map": {"q": "d"}, "drop_in": ["clk"], "stages": 1, "stages_param": "D"}', src)

    def test_pipe_declared_on_every_instance_of_the_type(self):
        """QC-EQ-TRIAGE 11-12: the type module (with its ot_dp_dly pipe) is emitted once from the first partition but
        instantiated by every partition of the type: bind_core_input_pipe.json must name every instance's leaf."""
        from types import SimpleNamespace as NS
        cells = [NS(path="c16_E0_0.u_t_0_0"), NS(path="c16_E0_0.u_t_0_1"),
                 NS(path="c16_W5_1.u_t_0_0"), NS(path="c16_W5_1.u_t_0_1"), NS(path="c99_X.u_t_0_0")]
        B = bind.Binder.__new__(bind.Binder)
        B.F = NS(cells=cells)
        B.members = {"c16_E0_0": [0, 1], "c16_W5_1": [2, 3], "c99_X": [4]}
        B.by_type = {"cbn_q11": ["c16_E0_0", "c16_W5_1"], "other": ["c99_X"]}
        B.local, B.cpart = {}, {0: "c16_E0_0", 1: "c16_E0_0", 2: "c16_W5_1", 3: "c16_W5_1", 4: "c99_X"}
        B.root = {"c16_E0_0": "c16_E0_0", "c16_W5_1": "c16_W5_1", "c99_X": "c99_X"}
        B.declare_core_input_pipe("cbn_q11", "c16_E0_0", 1, "n_a", 1)
        self.assertEqual(B.core_input_pipe, {"c16_E0_0.u_t_0_1.n_a": 1, "c16_W5_1.u_t_0_1.n_a": 1})
        B.members["c16_W5_1"] = [2]           # a partition without that leaf: fail closed, never under-declare
        with self.assertRaises(bind.BindError):
            B.declare_core_input_pipe("cbn_q11", "c16_E0_0", 1, "n_b", 1)
        src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "bind.py")).read()
        self.assertNotIn('setdefault("core_input_pipe", {})[f"{c.path}.{pn}"]', src)

    def test_cell_text_is_negative_level_latch(self):
        t = bind.ft_hop_lockup_cell()
        self.assertIn("module ot_dp_lk", t)
        self.assertIn("if (!clk) q = d;", t)


class CoreInputPlace(unittest.TestCase):
    """gen_phys.core_input_place: the A+P placement hooks follow the declared pipe, never form A alone."""

    def test_place_only_with_pipe(self):
        import gen_phys
        base = {"modules": MODS, "types": ["cbn_q11"]}
        self.assertFalse(gen_phys.core_input_place({}, "cbn_q11"))
        self.assertFalse(gen_phys.core_input_place({"clock": {"core_input_lockup": base}}, "cbn_q11"))
        p = {"clock": {"core_input_lockup": dict(base, pipe=1)}}
        self.assertTrue(gen_phys.core_input_place(p, "cbn_q11"))
        self.assertFalse(gen_phys.core_input_place(p, "cbn_q00"))

    def test_hook_scripts_present(self):
        import gen_phys
        d = os.path.dirname(os.path.abspath(__file__))
        for f in ("core_input_anchor.tcl", "core_input_chain.tcl"):
            self.assertTrue(os.path.isfile(os.path.join(d, f)))
            self.assertIn(f, gen_phys.CORE_INPUT_PLACE_ANCHOR + gen_phys.CORE_INPUT_PLACE_CHAIN)
        chain = open(os.path.join(d, "core_input_chain.tcl")).read()
        self.assertIn("u_pc_nk_", chain)
        self.assertIn("ot_face_flops.txt", chain)   # face-anchored registers stay fixed


class CoreInputPipeExcept(unittest.TestCase):
    """pipe_except: the listed ports keep the latch but get no pipe register (NK rst_n, COORD 11-11)."""

    def test_pipe_except(self):
        mods = {"qfd_tile_nk_a0c": ["n_a", "n_b", "tap", "rst_n"]}
        p = {"clock": {"core_input_lockup": {"modules": mods, "types": ["cbn_q11"], "pipe": 1, "pipe_except": ["rst_n"]}}}
        self.assertEqual(bind.core_input_pipe(p, "cbn_q11", "qfd_tile_nk_a0c", "n_a"), 1)
        self.assertEqual(bind.core_input_pipe(p, "cbn_q11", "qfd_tile_nk_a0c", "rst_n"), 0)
        self.assertEqual(bind.core_input_pipe(p, "cbn_q11", "qfd_tile_nk_a0c"), 1)
        self.assertIn("rst_n", bind.core_input_lockup(p, "cbn_q11", "qfd_tile_nk_a0c"))


class CoreInputLatchExcept(unittest.TestCase):
    """cb setup class 11-17: a port can keep the pipe register but lose its lockup latch (opt-in, 0 cycles)."""

    def _plan(self, **extra):
        return {"clock": {"core_input_lockup": dict({"modules": MODS, "types": ["cbn_q11"], "pipe": 1}, **extra)}}

    def test_default_every_listed_port_keeps_the_latch(self):
        p = self._plan()
        for port in ("n_a", "n_b", "tap"):
            self.assertTrue(bind.core_input_latch(p, "cbn_q11", "qfd_tile_nk_a0c", port))

    def test_latch_except_drops_only_that_port_and_keeps_the_pipe(self):
        p = self._plan(latch_except={"qfd_tile_nk_a0c": ["tap"]})
        self.assertFalse(bind.core_input_latch(p, "cbn_q11", "qfd_tile_nk_a0c", "tap"))
        self.assertTrue(bind.core_input_latch(p, "cbn_q11", "qfd_tile_nk_a0c", "n_a"))
        self.assertIn("tap", bind.core_input_lockup(p, "cbn_q11", "qfd_tile_nk_a0c"))
        self.assertEqual(bind.core_input_pipe(p, "cbn_q11", "qfd_tile_nk_a0c", "tap"), 1)

    def test_other_module_type_and_unlisted_port_have_no_latch(self):
        p = self._plan(latch_except={"qfd_tile_nk_a0c": ["tap"]})
        self.assertFalse(bind.core_input_latch(p, "cbn_q00", "qfd_tile_nk_a0c", "n_a"))
        self.assertFalse(bind.core_input_latch(p, "cbn_q11", "qfd_tile_nl_a0c", "n_a"))
        self.assertFalse(bind.core_input_latch(p, "cbn_q11", "qfd_tile_nk_a0c", "other"))

    def test_absent_lockup_is_off(self):
        self.assertFalse(bind.core_input_latch({}, "cbn_q11", "qfd_tile_nk_a0c", "tap"))

    def test_emitter_instantiates_the_latch_only_when_kept(self):
        src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "bind.py")).read()
        self.assertIn("has_latch = core_input_latch(self.plan, tn, c.module, pn)", src)
        i = src.index("has_latch = core_input_latch")
        blk = src[i:i + 2600]
        self.assertIn("if has_latch:\n                            body.append(f\"    ot_dp_lk", blk)
        self.assertIn("e = [lk]", blk)



class CoreInputLatchExceptBits(unittest.TestCase):
    """FABLE-PD-QC-0600 11-17: bit-level latch_except; only tap[0] drops its latch, the other tap bits keep it."""

    def _plan(self, ex):
        return {"clock": {"core_input_lockup": {"modules": MODS, "types": ["cbn_q11"], "pipe": 1, "latch_except": ex}}}

    def test_bit_entry_does_not_drop_the_port_latch_but_lists_the_bit(self):
        p = self._plan({"qfd_tile_nk_a0c": ["tap[0]"]})
        self.assertTrue(bind.core_input_latch(p, "cbn_q11", "qfd_tile_nk_a0c", "tap"))
        self.assertEqual(bind.core_input_latch_except_bits(p, "cbn_q11", "qfd_tile_nk_a0c", "tap"), {0})
        self.assertEqual(bind.core_input_latch_except_bits(p, "cbn_q11", "qfd_tile_nk_a0c", "n_a"), set())

    def test_several_bits_other_module_and_port_wide_entry(self):
        p = self._plan({"qfd_tile_nk_a0c": ["tap[0]", "tap[7]", "n_a[1]"]})
        self.assertEqual(bind.core_input_latch_except_bits(p, "cbn_q11", "qfd_tile_nk_a0c", "tap"), {0, 7})
        self.assertEqual(bind.core_input_latch_except_bits(p, "cbn_q11", "qfd_tile_nl_a0c", "tap"), set())
        self.assertEqual(bind.core_input_latch_except_bits(p, "cbn_q00", "qfd_tile_nk_a0c", "tap"), set())
        q = self._plan({"qfd_tile_nk_a0c": ["tap"]})   # port-wide form unchanged
        self.assertFalse(bind.core_input_latch(q, "cbn_q11", "qfd_tile_nk_a0c", "tap"))
        self.assertEqual(bind.core_input_latch_except_bits(q, "cbn_q11", "qfd_tile_nk_a0c", "tap"), set())

    def test_absent_key_is_byte_identical(self):
        p = {"clock": {"core_input_lockup": {"modules": MODS, "types": ["cbn_q11"], "pipe": 1}}}
        self.assertEqual(bind.core_input_latch_except_bits(p, "cbn_q11", "qfd_tile_nk_a0c", "tap"), set())
        self.assertEqual(bind.core_input_latch_except_bits({}, "cbn_q11", "qfd_tile_nk_a0c", "tap"), set())

    def test_emitter_latches_only_the_other_bits(self):
        src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "bind.py")).read()
        i = src.index("xbits = {i_ for i_ in core_input_latch_except_bits")
        blk = src[i:i + 3200]
        self.assertIn("keep_ = [i_ for i_ in range(len(bits)) if i_ not in xbits]", blk)
        self.assertIn("ot_dp_lk #(.W({len(keep_)}))", blk)
        self.assertIn("e[i_] = f\"{lk}[{j_}]\"", blk)

if __name__ == "__main__":
    unittest.main()


class CoreInputLockupSchema(unittest.TestCase):
    """QC-EVENT-S25 11-11: the schema accepts the ap2 adoption form (DIE-QC-99 plan event) and rejects typos."""

    def test_schema(self):
        import schema
        try:
            import jsonschema
        except ImportError:
            self.skipTest("jsonschema not installed")
        v = jsonschema.Draft202012Validator(schema.SCHEMA["properties"]["clock"])
        good = {"modules": {"qfd_tile_nk_a0c": ["n_a", "n_b", "tap", "rst_n"]}, "all": True, "pipe": 1,
                "pipe_except": ["rst_n"]}
        self.assertFalse(list(v.iter_errors({"core_input_lockup": good})))
        self.assertTrue(list(v.iter_errors({"core_input_lockup": dict(good, pipes=1)})))
        self.assertTrue(list(v.iter_errors({"core_input_lockup": dict(good, pipe=-1)})))
        self.assertTrue(list(v.iter_errors({"core_input_lockup": {"all": True}})))
        self.assertTrue(list(v.iter_errors({"core_input_lockup": dict(good, modules={"m": []})})))

