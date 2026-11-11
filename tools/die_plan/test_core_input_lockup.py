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


if __name__ == "__main__":
    unittest.main()
