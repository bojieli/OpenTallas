"""Regression: a declared TT bundle must not disappear from a seam-only parser."""
import sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent))
import record_bundles as RB

FIELDS = [("emb_start","head_prepare_v",1),("emb_token","head_prepare_token",18),
          ("emb_position","head_prepare_position",18),("emb_user","head_prepare_user",2)]
BUNDLES = {"TT.head_prepare":[("tt_ctlm",s,"native59",d) for s,d,_ in FIELDS]}

def vehicle(extra_token_edge=False,missing_user=False):
    src=", ".join(f".{s}(n_{s})" for s,_,_ in FIELDS)
    dst=", ".join(f".{d}(n_{s}__r{2 if extra_token_edge and s=='emb_token' else 1})"
                  for s,d,_ in FIELDS if not(missing_user and s=="emb_user"))
    lines=[f"m_tt tt_ctlm ({src});",f"m_native native59 ({dst});"]
    lines += [f"qfd_rly_w{w} rly_{s}_0 (.i(n_{s}), .o(n_{s}__r1));" for s,_,w in FIELDS]
    if extra_token_edge:lines += ["qfd_rly_w18 rly_emb_token_1 (.i(n_emb_token__r1), .o(n_emb_token__r2));"]
    return "\n".join(lines)+"\n"

class DeclaredEndpoints(unittest.TestCase):
    def audit(self,**kwargs):
        with tempfile.TemporaryDirectory() as t,patch.object(RB,"BUNDLES",BUNDLES):
            p=Path(t)/"die.v";p.write_text(vehicle(**kwargs));return RB.audit_netlist(p)
    def test_actual_four_tt_members_are_seen(self):
        rec=self.audit()
        self.assertEqual(rec["verdict"],"PASS",rec["fails"])
        self.assertEqual(len(rec["bundles"]["TT.head_prepare"]["members"]),4)
        self.assertEqual(rec["bundles"]["TT.head_prepare"]["cycles"],[1])
    def test_extra_actual_token_edge_fails(self):
        rec=self.audit(extra_token_edge=True)
        self.assertEqual(rec["verdict"],"FAIL")
        self.assertIn("different edges"," ".join(rec["fails"]))
    def test_missing_actual_user_pin_fails(self):
        rec=self.audit(missing_user=True)
        self.assertEqual(rec["verdict"],"FAIL")
        self.assertIn("head_prepare_user"," ".join(rec["fails"]))

if __name__=="__main__":unittest.main()
