"""Serialized captured reset trees must preserve bootstrap/mission cell semantics."""
import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

import bound_reset_contract as B
import gen_phys as G
import gen_rtl
import reset_tree as R


def tree():
    return dict(type="t",entry="relayed",sync_stages=2,root=[8.64,8.64],
                start=True,start_in=[8.64,10.8],start_role="bootstrap",start_tap=1,
                tap_roles={i:("bootstrap" if i%2==0 else "mission") for i in range(12)},
                relays=[dict(name=f"u_rrl_{i}",d="rst_root_n",q=f"rst_n_t{i}",
                             xy=[17.28+i*.054,17.28],depth=1,tap=i,kind="tap") for i in range(12)],
                taps=[f"clk{i}" for i in range(12)],n_clock_taps=12,own_depth=1,depth=1,
                n_tree=12,n_pad=0,max_hop_um=18,reach_um=405,outs=[],core_resets=[],relay_driver=False)


class ResetJsonRoles(unittest.TestCase):
    def test_json_roundtrip_preserves_cells_and_exact_emitted_rtl_tcl(self):
        original=tree();stored=json.loads(json.dumps(original))
        self.assertEqual(R.start_relays(original),R.start_relays(stored))
        self.assertEqual(R.rtl_lines(original),R.rtl_lines(stored))
        self.assertEqual(R.tcl_text(original),R.tcl_text(stored))
        nodes={r["name"]:r for r in R.start_relays(stored)}
        self.assertEqual(nodes["u_rrl_0"]["role"],"boot")
        self.assertEqual(nodes["u_rrl_1"]["role"],"gated")

    def test_actual_source_receipt_reimport_matches_bootstrap_native_cells(self):
        with TemporaryDirectory() as directory:
            root=Path(directory);original=tree()
            text=("module top(input clk,arst_n,start_i);\n"
                  "bound u_bound(.clk(clk),.arst_n(arst_n),.start_i(start_i));\nendmodule\n"
                  "module bound(input clk,arst_n,start_i);\n"+"\n".join(R.rtl_lines(original))+
                  "\nendmodule\n"+gen_rtl.CELLS)
            path=root/"top.sv";path.write_text(text)
            B.emitted(path,"t",original)
            captured=B.source(path,"t",root,root)
            self.assertIn("0",captured["tree"]["tap_roles"])
            plan=SimpleNamespace(types={"t":dict(module="top",outline_um=[100,100],
                 clock=dict(landing_contract=dict(collector_tree=captured["tree"])))})
            result=G.install_bound_native_reset(plan,"t",[path],source_contract=captured)
            self.assertEqual(result["native_paths"]["u_rrl_0"],"u_bound.u_rrl_0")
            changed=copy.deepcopy(captured);changed["tree"]["tap_roles"]["0"]="mission"
            changed["tree_sha256"]=B.digest(changed["tree"])
            plan.types["t"]["clock"]["landing_contract"]["collector_tree"]=changed["tree"]
            with self.assertRaises(gen_rtl.GenError):
                G.install_bound_native_reset(plan,"t",[path],source_contract=changed)

    def test_conflicting_representations_refuse(self):
        original=tree();original["tap_roles"]["0"]="mission"
        with self.assertRaisesRegex(R.ResetError,"conflicting integer/string"):
            R.start_relays(original)


if __name__=="__main__":
    unittest.main()
