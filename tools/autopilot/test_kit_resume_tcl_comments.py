import unittest
import kit_resume as KR

class TclCommentDependencies(unittest.TestCase):
    def test_actual_hc_comment_chain_does_not_promote_place_hook(self):
        texts = {
            "face_keep.tcl": "# reset_taps.tcl could not re-point FIRM flops\nset keep 1\n",
            "reset_taps.tcl": "# landing_placement.tcl calls rt_repoint_only\nproc rt_repoint_only {} {}\n",
            "face_flops.tcl": "source /work/reset_taps.tcl\nuplevel #0 {source /work/landing_placement.tcl}\n",
            "landing_placement.tcl": "if {[info exists ::env(OT_CLAND_STRIP_ROWS)]} {puts yes}\n",
            "rtl/top.sv": "module top; endmodule\n", "unknown.tcl": "puts unknown\n"}
        config = {"PRE_SYNTH_TCL": "/work/face_keep.tcl", "PRE_GLOBAL_PLACE_TCL": "/work/face_flops.tcl",
                  "VERILOG_FILES": "/work/rtl/top.sv", "OT_CLAND_STRIP_ROWS": "3"}
        stages = KR.classify(texts, list(texts), config)
        self.assertEqual(stages["landing_placement.tcl"], "place")
        self.assertEqual(stages["reset_taps.tcl"], "place")
        self.assertEqual(KR.config_var_stages(config, texts, stages)["OT_CLAND_STRIP_ROWS"], "place")
        self.assertEqual(stages["rtl/top.sv"], "synth")
        self.assertEqual(stages["unknown.tcl"], "synth")
        texts["face_keep.tcl"] += "source /work/reset_taps.tcl\n"
        stages = KR.classify(texts, list(texts), config)
        self.assertEqual(stages["reset_taps.tcl"], "synth")
        # Real executable dependency is still early, even across the same files.
        texts["reset_taps.tcl"] += "source /work/landing_placement.tcl\n"
        stages = KR.classify(texts, list(texts), config)
        self.assertEqual(stages["landing_placement.tcl"], "synth")

if __name__ == "__main__": unittest.main()
