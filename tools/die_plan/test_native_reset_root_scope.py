"""Native reset identity is rooted in the actual kit, not unrelated file closure."""
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

import gen_phys as G
import gen_rtl
import reset_tree as R


def fixture(root, extra="", mutate=lambda value: value):
    tree = dict(type="t", entry="relayed", sync_stages=2, root=[8.64, 8.64], start=False,
                relays=[dict(name="u_rrl_0", d="rst_root_n", q="rst_n_t0",
                             xy=[17.28,17.28], depth=1, tap=0, kind="tap")],
                taps=["clk"], own_depth=1, depth=1, n_tree=1, n_pad=0,
                max_hop_um=17.28, reach_um=405, outs=[], core_resets=[], relay_driver=False)
    text = ("module top(input clk, arst_n);\n"
            "bound u_bound(.clk(clk),.arst_n(arst_n));\nendmodule\n"
            "module bound(input clk, arst_n);\n"+"\n".join(R.rtl_lines(tree))+
            "\nendmodule\n"+gen_rtl.CELLS+"\n"+extra)
    path = root/"native.sv"
    path.write_text(mutate(text))
    plan = SimpleNamespace(types={"t":dict(module="top", outline_um=[100,100],
                         clock=dict(landing_contract=dict(collector_tree=tree)))})
    return plan, path


class NativeResetRootScope(unittest.TestCase):
    def test_unrelated_repeated_names_and_external_parent_are_not_kit_hierarchy(self):
        with TemporaryDirectory() as directory:
            extra = ("module unrelated(input clk,arst_n);\n"
                     "ot_dp_rrelay u_rst_in(.clk(clk),.d(arst_n),.q(other));\n"
                     "ot_dp_rrelay u_rrl_0(.clk(clk),.d(other),.q(unused));\nendmodule\n"
                     "module external(input different_clk,arst_n);\n"
                     "top outside(.clk(different_clk),.arst_n(arst_n));\nendmodule\n")
            plan, path = fixture(Path(directory), extra)
            result = G.install_bound_native_reset(plan, "t", [path])
            self.assertEqual(result["entry_path"], "u_bound.u_rst_in")
            self.assertEqual(result["native_paths"]["u_rrl_0"], "u_bound.u_rrl_0")

    def test_same_local_relay_name_in_reachable_other_owner_is_not_native_forest(self):
        with TemporaryDirectory() as directory:
            extra = ("module other(input clk);\n"
                     "ot_dp_rrelay u_rrl_0(.clk(clk),.d(other_reset),.q(other_out));\nendmodule\n")
            def add_other(text):
                return text.replace("bound u_bound(", "other sibling(.clk(clk));\nbound u_bound(", 1)
            plan, path = fixture(Path(directory), extra, add_other)
            result = G.install_bound_native_reset(plan, "t", [path])
            self.assertEqual(result["native_paths"]["u_rrl_0"], "u_bound.u_rrl_0")

    def test_missing_wrong_duplicate_tied_and_ambiguous_owner_still_refuse(self):
        mutations = [
            lambda t:t.replace("u_rrl_0 (","missing_relay ("),
            lambda t:t.replace("ot_dp_rrelay u_rrl_0","ot_dp_rgate u_rrl_0"),
            lambda t:t.replace(".d(rst_root_n), .q(rst_n_t0)",".d(wrong), .q(rst_n_t0)"),
            lambda t:t.replace("bound u_bound(", "bound duplicate(.clk(clk),.arst_n(arst_n));\nbound u_bound(", 1),
            lambda t:t.replace("bound u_bound(.clk(clk),.arst_n(arst_n))",
                               "bound u_bound(.clk(clk),.arst_n(1'b1))"),
        ]
        for index, mutate in enumerate(mutations):
            with self.subTest(index=index), TemporaryDirectory() as directory:
                plan, path = fixture(Path(directory), mutate=mutate)
                with self.assertRaises(gen_rtl.GenError):
                    G.install_bound_native_reset(plan, "t", [path])

    def test_explicit_missing_or_duplicate_top_does_not_fall_back(self):
        for duplicate in [False, True]:
            with self.subTest(duplicate=duplicate), TemporaryDirectory() as directory:
                extra = "module top; endmodule\n" if duplicate else ""
                plan, path = fixture(Path(directory), extra)
                if not duplicate:
                    plan.types["t"]["module"] = "missing"
                with self.assertRaisesRegex(gen_rtl.GenError, "selected hierarchy"):
                    G.install_bound_native_reset(plan, "t", [path])


if __name__ == "__main__":
    unittest.main()
