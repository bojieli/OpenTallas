"""A staged native reset must survive the legacy conversion entry point."""
import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import bound_reset_contract as B
import gen_phys as G
import gen_rtl
import kit_rsync as K
import reset_tree as R
from test_reset_json_roles import tree

class NativeRsyncTest(unittest.TestCase):
    def prepare(self, root):
        t=tree()
        p=SimpleNamespace(types={"t":dict(module="top",outline_um=[100,100],
            clock=dict(landing_contract=dict(collector_tree=t)))})
        f=root/"top.sv"
        f.write_text("module top(input clk,arst_n,start_i);\n"
            "bound u_bound(.clk(clk),.arst_n(arst_n),.start_i(start_i));\nendmodule\n"
            "module bound(input clk,arst_n,start_i);\n"+"\n".join(R.rtl_lines(t))+
            "\nendmodule\n"+gen_rtl.CELLS)
        B.emitted(f,"t",t)
        source=B.source(f,"t",root,root)
        p.types["t"]["clock"]["landing_contract"]["collector_tree"]=source["tree"]
        contract=G.install_bound_native_reset(p,"t",[f],source_contract=source)
        B.stage(root,source,contract)
        (root/"kit_rtl.json").write_text(json.dumps(dict(files=[str(f)],bound_module="bound")))
        (root/"kit_rtl.f").write_text(str(f)+"\n")
        (root/"plan.json").write_text("{}")
        return p,f

    def run_main(self, root, p):
        with patch.object(K.S,"Plan",return_value=p), \
             patch.object(R,"consumer_taps",side_effect=AssertionError("native reset must not re-solve")), \
             patch.object(R,"for_type",side_effect=AssertionError("native reset must not re-solve")):
            return K.main([str(root/"plan.json"),"t",str(root)])

    def test_exact_native_rtl_and_sidecars_are_preserved(self):
        with TemporaryDirectory() as d:
            r=Path(d);p,f=self.prepare(r)
            before={x.name:x.read_bytes() for x in r.iterdir() if x.is_file()}
            self.assertEqual(self.run_main(r,p),0)
            self.assertEqual(before,{x.name:x.read_bytes() for x in r.iterdir() if x.is_file()})
            self.assertIn("u_bound[./]u_rst_in",(r/"reset_tree.tcl").read_text())

    def test_tampered_sidecar_refuses_without_repairing(self):
        with TemporaryDirectory() as d:
            r=Path(d);p,f=self.prepare(r)
            q=r/"reset_tree.tcl";q.write_text(q.read_text()+"# changed\n")
            old=q.read_bytes()
            with self.assertRaisesRegex(ValueError,"placement sidecar differs"):
                self.run_main(r,p)
            self.assertEqual(q.read_bytes(),old)

    def test_changed_native_connection_refuses(self):
        with TemporaryDirectory() as d:
            r=Path(d);p,f=self.prepare(r)
            text=f.read_text()
            self.assertIn(".d(rst_root_n)",text)
            f.write_text(text.replace(".d(rst_root_n)",".d(arst_n)",1))
            with self.assertRaises(gen_rtl.GenError):
                self.run_main(r,p)

    def test_placement_receipt_cannot_lie_about_paths(self):
        with TemporaryDirectory() as d:
            r=Path(d);p,f=self.prepare(r)
            q=r/"bound_reset.json";rec=json.loads(q.read_text())
            rec["native_paths"]["u_rst_in"]="other.u_rst_in"
            q.write_text(json.dumps(rec))
            with self.assertRaisesRegex(gen_rtl.GenError,"hierarchy differs"):
                self.run_main(r,p)

if __name__=="__main__":
    unittest.main()
