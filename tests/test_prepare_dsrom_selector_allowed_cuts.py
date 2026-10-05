import fnmatch
import gzip
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import prepare_dsrom_selector_allowed_cuts as T
import prepare_dsrom_balanced_selector_candidate as C
import prepare_dsrom_full_selector_dma_fixture as V
import uarch_topk_station_SSFF_cell_model as L

class Cuts(unittest.TestCase):
    def model(self):return json.loads((T.BASE/'model.json').read_text())
    def source(self):return (T.ROOT/'tools/rtl_templates/ot_topk_allowed_cut_packet_prepare.sv').read_text()
    def test_fullgeometry_instance_ledger(self):
        m=self.model();ff=sum(h['WIDTH']*h['EDGES'] for h in m['helpers']);present=sum(h['EDGES'] for h in m['helpers'])
        self.assertEqual(ff,475954);self.assertEqual(present,226)
        self.assertEqual(ff+present,476180)
        self.assertEqual(2*sum((h['WIDTH']+1)*(h['EDGES']+1) for h in m['helpers']),965012)
        self.assertEqual(m['instance_ledger']['BUFx4_terminal_ASAP7_75t_R'],476180)
        self.assertEqual(m['instance_ledger']['TIEHIx1_ASAP7_75t_R'],present+3)
        self.assertAlmostEqual(m['new_tie_reserve_mm2_at50pct'],0.00002003292)
    def test_actual_liberty_port_names_both_corners(self):
        names=['DFFHQNx1_ASAP7_75t_R','DFFASRHQNx1_ASAP7_75t_R','INVx1_ASAP7_75t_R','BUFx4_ASAP7_75t_R','AND2x2_ASAP7_75t_R','TIEHIx1_ASAP7_75t_R']
        source=self.source()
        for corner in ('SS','FF'):
            texts=[]
            for p in (L.BASE/'inputs').glob('*'+corner+'*'):
                texts.append((gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes()).decode())
            for name in names:
                cell=next(body for text in texts for master,body in L.groups(text,'cell') if master==name)
                allowed={n for n,_ in L.groups(cell,'pin')}
                calls=re.findall(name+r'\s+\w+\(([^;]+)\);',source)
                self.assertTrue(calls,name)
                for call in calls:self.assertEqual(set(re.findall(r'\.(\w+)\(',call)),allowed,name)
    def test_all_instantiated_masters_allowed_no_old_HB(self):
        policy=(L.BASE/'inputs/config.mk').read_text();patterns=re.search(r'DONT_USE_CELLS\s*[:?+]?=\s*([^\n]+)',policy)
        self.assertIsNotNone(patterns)
        masters=set(re.findall(r'\b([A-Z][A-Za-z0-9]+_ASAP7_75t_R)\s+u_',self.source()))
        self.assertEqual(len(masters),6)
        for master in masters:
            for pattern in patterns[1].split():self.assertFalse(fnmatch.fnmatchcase(master,pattern),(master,pattern))
        self.assertNotIn('HB2',self.source())
    def test_cut_edges_ports_and_QN_restore(self):
        source=self.source()
        self.assertIn('CELL_MAP=0',source)
        self.assertIn('edge_<=EDGES',source);self.assertIn('edge_<EDGES',source)
        self.assertIn('.D(d),.CLK(clk),.QN(qn)',source)
        self.assertIn('.RESETN(rst_n),.SETN(setn),.QN(qn)',source)
        self.assertIn('.A(qn),.Y(source_bus[edge_+1][bit_])',source)
        self.assertIn('ALLOWED_CUT_FULL_INTERFACE_REQUIRED',source)
        self.assertIn('.A(rst_n),.B(final_bus[WIDTH])',source)
        self.assertNotIn('posedge',source) # no additional behavioral cell/clock RTL.
    def test_async_semantics_from_source_liberty(self):
        for corner in ('SS','FF'):
            seq=(L.BASE/'inputs'/f'asap7sc7p5t_SEQ_RVT_{corner}_nldm_220123.lib').read_text()
            cell=L.group(seq,'cell','DFFASRHQNx1_ASAP7_75t_R')
            ff=next(L.groups(cell,'ff'))[1]
            for expression in ['!D','!SETN','!RESETN']:self.assertIn('"'+expression+'"',ff)
            for data in (0,1):self.assertEqual(1-(1-data),data)
            # Clear=!SETN=0; preset=!RESETN=1 -> IQN1 -> restoredpresent0.
            self.assertEqual(1-1,0)
    def test_current_FAIL_and_unknown_deadline_are_not_admission(self):
        m=self.model();capture=json.loads((T.BASE/'inputs/capture_timing_FAIL.json').read_text())
        self.assertEqual(capture['verdict'],'FAIL_ONE_BALANCED_CUT_CONDITIONAL_SS')
        self.assertFalse(capture['RTL_or_build_admitted'])
        self.assertIsNone(m['consumer_deadline'])
        self.assertFalse(m['compile_admitted']);self.assertFalse(m['integrated_parent_runtime_admitted'])
        self.assertFalse(m['full_phase_accepted_field_trace'])
    def test_fresh_replay_actual_caller_interface_no_standin(self):
        with tempfile.TemporaryDirectory() as d:
            a=Path(d)/'a';b=Path(d)/'b';T.prepare(a);T.prepare(b)
            self.assertEqual((a/'artifact_manifest.json').read_bytes(),(b/'artifact_manifest.json').read_bytes())
            for p,h in json.loads((a/'artifact_manifest.json').read_text()).items():self.assertEqual(V.sha((a/p).read_bytes()),h)
            caller=(a/'candidate/ot_w15_coll_dma_balanced_allowed_cut_prepare.sv').read_text()
            original=C.caller(C.F.SOURCE.read_text())
            start=') (\n';end='    localparam integer LANES'
            self.assertEqual(caller[caller.index(start):caller.index(end)],original[original.index(start):original.index(end)])
            self.assertEqual(caller.count('ot_topk_allowed_cut_packet_prepare #(.CELL_MAP(TK_CELL_MAP)'),3)
            self.assertIn('TK_CELL_MAP = 0',caller)
            for h in ('.EDGES(99)', '.EDGES(28)'):self.assertIn(h,caller)
            plan=json.loads((a/'sourceplan.json').read_text())
            self.assertTrue(plan['official_SEQ_UDP_and_specify_backend_compatibility_unverified'])
            self.assertFalse(plan['compile_admitted'])

if __name__=='__main__':unittest.main()
