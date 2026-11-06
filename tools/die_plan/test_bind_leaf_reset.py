import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import bind_leaf_reset as LR
import kit_topology as KT

def rule():
    return dict(type="pc",module="soft_leaf",ports=["hbm_rst_n","host_rst_n"],anchors={"hsl0":"pcc0"})

class LeafReset(unittest.TestCase):
    def test_default_and_other_type_are_unchanged(self):
        self.assertEqual(LR.selected(None,"pc",[]),[])
        self.assertEqual(LR.selected([rule()],"different",[]),[])
    def test_explicit_anchor_and_ports(self):
        rs=LR.selected([rule()],"pc",[dict(inst="pcc0")])
        self.assertEqual(LR.resolve(rs,"soft_leaf","hsl0","hbm_rst_n"),"pcc0")
        self.assertIsNone(LR.resolve(rs,"soft_leaf","hsl0","data"))
        with self.assertRaises(ValueError):LR.resolve(rs,"soft_leaf","hsl1","hbm_rst_n")
    def test_missing_and_duplicate_anchors_refused(self):
        with self.assertRaises(ValueError):LR.selected([rule()],"pc",[])
        with self.assertRaises(ValueError):LR.selected([rule(),rule()],"pc",[dict(inst="pcc0")])
        bad=rule();bad["ports"]=["hbm_rst_n","hbm_rst_n"]
        with self.assertRaises(ValueError):LR.selected([bad],"pc",[dict(inst="pcc0")])
    def test_native_seal_only_changes_selected_type(self):
        typ=dict(hard_cores=[dict(inst="pcc0")],buses=[])
        raw=dict(partition_types={"pc":typ,"other":copy.deepcopy(typ)},lanes=[],ports=[])
        before=KT.native_contract(dict(raw,asbuilt={}))
        expected=KT.digest(dict(native_out_stations=[],clock={},clock_table_sha256=None,buses=[],count_straps=None,id_straps=None))
        self.assertEqual(before["types"]["pc"],expected)
        after=KT.native_contract(dict(raw,asbuilt=dict(reset_gate_bindings=[rule()])))
        self.assertNotEqual(before["types"]["pc"],after["types"]["pc"])
        self.assertEqual(before["types"]["other"],after["types"]["other"])

if __name__=="__main__":unittest.main()
