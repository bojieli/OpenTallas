import unittest
from unittest.mock import patch
import pathlib,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import clock_entry_constraints as CE

class DirectLandingReserve(unittest.TestCase):
    def record(self, direct=True):
        return dict(D=4,E=2,landings=[dict(name='0')],landing_implementation=dict(direct_quarter_period_timing=direct,chunk_bits=24))
    def test_direct_removes_old_mcp_and_retains_deep_entry_reserve(self):
        with patch.object(CE,'landed_record',return_value=self.record()):
            s=CE.landed_sdc(dict(landed_record='fixture',landing_direct_residual_ps=150),'.')
        self.assertNotRegex(s,r'set_(?:multicycle_path|false_path|clock_groups|disable_timing)')
        self.assertIn('210.0 + 0.75 * $ot_lp_direct_T',s)
        self.assertIn('hold 175.0',s)
        self.assertIn('foreach a $ot_lp_direct_clocks',s)
        self.assertIn('ot_cf_root [get_full_name $a]',s)
    def test_mutant_direct_record_cannot_fall_back_to_mcp(self):
        rec=self.record();rec['E']=3
        with patch.object(CE,'landed_record',return_value=rec):
            with self.assertRaisesRegex(ValueError,'D4/E2'):CE.landed_sdc(dict(landing_direct_residual_ps=150),'.')
    def test_missing_or_weakened_reserve_fails_closed(self):
        for residual in [None,60,149]:
            spec=dict(landed_record='fixture')
            if residual is not None: spec['landing_direct_residual_ps']=residual
            with self.subTest(residual=residual),patch.object(CE,'landed_record',return_value=self.record()):
                with self.assertRaisesRegex(ValueError,'preserve'):CE.landed_sdc(spec,'.')
    def test_default_keeps_existing_landing_contract(self):
        with patch.object(CE,'landed_record',return_value=self.record(False)):
            s=CE.landed_sdc(dict(landed_record='fixture'),'.')
        self.assertIn('set_multicycle_path -setup 2',s)
        self.assertNotIn('0.75 *',s)
if __name__=='__main__':unittest.main()
