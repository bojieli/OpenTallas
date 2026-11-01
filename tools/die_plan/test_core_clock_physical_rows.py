import copy,json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import gen_phys as G
import core_clock_contract as CC

class PhysicalMeanRows(unittest.TestCase):
    def setUp(self):
        self.p=SimpleNamespace(clock={'insertion_ps':250},types={'T':{'hard_cores':[dict(inst='logical',module='child',physical_inst='u_bound.actual',physical_master='child')],'clock':{'taps':[]}}})
        self.row=dict(inst='logical',module='child',pin='clk',rise_ps=250,fall_ps=250,tap='clk_c0',corners={'tt':{'mean_ps':250,'source':'actual TT'},'ff':{'mean_ps':202.5,'source':'actual FF'}},basis='parent_budget',signed=False,release_qualified=False)
        self.taps=[('clk_c0','u_bound.actual','clk',0,250)]
    def run_case(self,row):
        with tempfile.TemporaryDirectory() as d,patch.object(CC,'latency_table',return_value=[row]),patch.object(CC,'native_clock_models',return_value=[]),patch.object(G,'core_tap_rows',return_value=self.taps):
            return G.core_latency_files(self.p,'T',Path(d),mean_contract=True,require_signed=False)
    def test_alias_matches_same_means_and_qualification(self):
        before=copy.deepcopy(self.row);out=self.run_case(self.row)['rows'][0]
        self.assertEqual(out['inst'],'u_bound.actual');self.assertEqual(out['logical_inst'],'logical')
        self.assertEqual({k:v for k,v in out.items() if k not in {'inst','logical_inst'}},{k:v for k,v in before.items() if k!='inst'})
        self.assertEqual(self.row,before)
    def test_wrong_mean_still_fails(self):
        self.row['rise_ps']=249
        with self.assertRaisesRegex(CC.ContractError,'does not match selected TT mean'):self.run_case(self.row)
    def test_native_reference_names_follow_same_alias_without_mean(self):
        model=dict(inst='logical',kind='native_sram_clock_reference',reference_pin='CLK')
        with tempfile.TemporaryDirectory() as d,patch.object(CC,'latency_table',return_value=[]),patch.object(CC,'native_clock_models',return_value=[model]),patch.object(G,'core_tap_rows',return_value=[]):
            G.core_latency_files(self.p,'T',Path(d),mean_contract=True,require_signed=False)
            out=json.load(open(Path(d)/'native_clock_models.json'))['rows'][0]
            self.assertEqual(out['inst'],'u_bound.actual');self.assertEqual(out['logical_inst'],'logical')
            self.assertNotIn('rise_ps',out);self.assertNotIn('mean_ps',out)
    def test_unaliased_rows_remain_unchanged(self):
        self.p.types['T']['hard_cores']=[dict(inst='logical',module='child')]
        self.assertEqual(G.core_physical_rows(self.p,'T',[self.row]),[self.row])

if __name__=='__main__':unittest.main()
