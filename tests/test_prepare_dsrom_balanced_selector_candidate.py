import json
import gzip
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import prepare_dsrom_balanced_selector_candidate as C
import prepare_dsrom_balanced_selector_gate as G
import prepare_dsrom_full_selector_dma_fixture as V
import verify_dsrom_balanced_selector_completion as K
import audit_dsrom_balanced_selector_connections as A
import uarch_topk_station_SSFF_cell_model as L

class Candidate(unittest.TestCase):
    def test_model_before_source_exact_stage_state_price(self):
        model=json.loads((C.BASE/'implementation_model.json').read_text())
        self.assertEqual(sum(C.bits().values()),127140)
        self.assertEqual(model['state_bits_model_gross'],698354)
        self.assertEqual(4*(5+15+9)+6+21-1,142)
        self.assertEqual(model['ports']['load_bits_per_edge'],2048)
        self.assertFalse(model['compile_admitted'])
    def test_actual_generated_register_declaration_count(self):
        source=C.staged(C.SOURCE.read_text())
        self.assertEqual(A.register_bits(source)['net_added_bits'],127140)
        with self.assertRaisesRegex(ValueError,'register count'):
            A.register_bits(source.replace('reg [1:0] hist_pc_1','reg [2:0] hist_pc_1'))
    def test_actual_prefix_sort_connections_full37_numerical_transcription(self):
        source=C.staged(C.SOURCE.read_text());audit=A.audit(source)
        self.assertEqual(len(audit['cases']),37)
        self.assertEqual(audit['rows'],3008)
        self.assertFalse(audit['HDL_executed'])
        with self.assertRaises(ValueError):A.audit(source.replace('(si8^4)','(si8^2)'))
        with self.assertRaises(ValueError):A.audit(source.replace('if(ep3>=8)','if(ep3>=4)'))
    def test_async_reset_debit_exact_and_not_doublecharged(self):
        model=json.loads((C.BASE/'implementation_model.json').read_text());d=model['async_reset_master_debit']
        self.assertEqual(sum(d['groups'].values()),35)
        self.assertAlmostEqual(d['incremental_cell_area_um2'],3.0618)
        self.assertAlmostEqual(d['incremental_reservation_mm2_at50pct'],0.0000061236)
        self.assertTrue(d['new_clock_sinks_already_in_127140_bit_ledger'])
        self.assertTrue(d['reset_distribution_area_and_recovery_removal_unpriced'])
        self.assertEqual(d['SETN_tie_provider']['gross_new_count'],35)
        self.assertEqual(d['SETN_tie_provider']['fanout_per_provider'],1)
        self.assertAlmostEqual(d['total_additional_cell_area_with_ties_um2'],4.5927)
        for corner in ('SS','FF'):
            path=V.ROOT/f'results/uarch/topk_station_SSFF_cell_model_20261002/inputs/asap7sc7p5t_SEQ_RVT_{corner}_nldm_220123.lib'
            text=path.read_text()
            for master,key in [('DFFHQNx1_ASAP7_75t_R','ordinary_FF_area_um2'),('DFFASRHQNx1_ASAP7_75t_R','async_FF_area_um2')]:
                self.assertEqual(L.number(L.group(text,'cell',master),'area'),d[key])
            tie_path=V.ROOT/f'results/uarch/topk_station_SSFF_cell_model_20261002/inputs/asap7sc7p5t_SIMPLE_RVT_{corner}_nldm_211120.lib.gz'
            tie=L.group(gzip.decompress(tie_path.read_bytes()).decode(),'cell','TIEHIx1_ASAP7_75t_R')
            self.assertAlmostEqual(L.number(tie,'area'),d['SETN_tie_provider']['cell_area_um2_each'])
            self.assertIn('function : "1"',L.group(tie,'pin','H').replace('  ',' '))

    def test_complete_interfaces_defaultoff(self):
        wrapper=C.wrapper(C.SOURCE.read_text())
        caller=C.caller(C.F.SOURCE.read_text())
        self.assertIn('BALANCED = 0',wrapper)
        self.assertIn('TK_BALANCED = 0',caller)
        self.assertIn('TK_STATION = 0',caller)
        for port in C.PORTS:self.assertEqual(wrapper.count('.'+port+'('+port+')'),2)
        for param in C.PARAMS:self.assertEqual(wrapper.count('.'+param+'('+param+')'),2)
        self.assertIn('ot_coll_topk_merge_balanced_prepare',caller)
        self.assertIn('tk_drained_done',caller)
        self.assertIn('u_write',caller)
    def test_generated_tree_exact_modular_dependencies(self):
        source=C.staged(C.SOURCE.read_text())
        self.assertNotIn('a = a + cnt[b]',source)
        self.assertNotIn('s = s + h1_hot',source)
        self.assertIn("suffix_down_6[sd7]+cnt[2*sd7+1]",source)
        self.assertIn("choose_lower_sum[cp]<={(suf[cp]<rr),CB'(suf[cp]+cnt[cp])}",source)
        for level in range(8):self.assertIn(f'begin:g_up_{level}',source);self.assertIn(f'begin:g_down_{level}',source)
        self.assertIn('pk==25',source);self.assertIn('pk == 26',source)
        self.assertIn('choose_node_6[1][CB+DIG]?choose_node_6[1]:choose_node_6[0]',source)
    def test_generated_prefix_and_sort_topology(self):
        source=C.staged(C.SOURCE.read_text())
        for level in range(6):
            self.assertIn(f'begin:g_eq_{level}',source)
            self.assertIn(f'eq_count_{level}',source)
        for stage in range(1,22):self.assertIn(f'begin:g_sort_{stage}',source)
        self.assertIn("f3_tp[l]<={!f2_take[l],6'(l)}",source)
        self.assertIn("chosen[38]?32'd0:chosen[31:0]",source)
        self.assertIn('f4_n<=sort_valid[19]?take_total_20',source)
        self.assertIn('(|sort_valid)',source)
        for level in range(6):self.assertIn('|| eq_v_'+str(level),source)
    def test_nan_key_loader_and_badcommand_unchanged(self):
        original=C.SOURCE.read_text();source=C.staged(original)
        for start,end in [('    function automatic [31:0] okey','    // ---- candidate buffers'),('    integer ln, lj;','    // ---- control')]:
            self.assertEqual(original[original.index(start):original.index(end)],source[source.index(start):source.index(end)])
        self.assertIn('nan_seen || k == 0 || n == 0 || ((n * N) % P) != 0 || (n % PF) != 0 || n > NMAX || k > n * N',source)
    def test_stale_implementation_model_source_pins_refused(self):
        prior=C.BASE
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);model=json.loads((C.BASE/'implementation_model.json').read_text())
            model['model_pins'][next(iter(model['model_pins']))]='0'*64
            (root/'implementation_model.json').write_text(json.dumps(model))
            try:
                C.BASE=root
                with self.assertRaisesRegex(ValueError,'model pin changed'):C.prepare(root/'out')
                self.assertFalse((root/'out').exists())
            finally:C.BASE=prior

    def test_replay_dependency_hashes_and_no_compile(self):
        with tempfile.TemporaryDirectory() as t:
            a=Path(t)/'a';b=Path(t)/'b';pa=G.prepare(a);G.prepare(b)
            self.assertEqual((a/'artifact_manifest.json').read_bytes(),(b/'artifact_manifest.json').read_bytes())
            for p,h in json.loads((a/'artifact_manifest.json').read_text()).items():self.assertEqual(V.sha((a/p).read_bytes()),h)
            self.assertTrue(pa['candidate_dependencies_complete']);self.assertFalse(pa['compile_admitted'])
            modules={p.stem for p in (a/'candidate').glob('*.sv')}
            self.assertEqual(modules,{'ot_coll_topk_merge','ot_coll_topk_merge_staged_impl_prepare','ot_coll_topk_merge_balanced_prepare','ot_w15_coll_dma','ot_w15_coll_dma_balanced_station_prepare','ot_chip_v41x_coll_transpose','ot_topk_fixed_packet_delay_prepare'})
    def test_fault_immutable_images(self):
        with tempfile.TemporaryDirectory() as t:
            out=Path(t)/'gate';plan=G.prepare(out)
            for f in plan['fault_input_pins']:
                lines=(out/'fixture'/f['path']).read_text().splitlines()
                self.assertEqual((int(lines[f['beat']],16)>>(32*f['lane']))&0xffffffff,f['score_word'])
                self.assertEqual(V.sha((out/'fixture'/f['path']).read_bytes()),f['sha256'])
                self.assertEqual(len(lines),64)
            self.assertEqual(len(plan['fault_contract']),15)
    def test_fault_ownership_and_settling_not_waived(self):
        source=G.bench((V.ROOT/V.TEMPLATE).read_text())
        self.assertIn('ref_busy!==wanted_busy[0]',source)
        self.assertIn('repeat(204) tick()',source)
        self.assertIn('reset_fixture();observe_reset_drain()',source)
        self.assertIn('cand_fault!==1',source)
        self.assertIn('cycle-ref_return_cycle[cand_return_groups]!=(MUTANT==4?0:340)',source)
        self.assertIn('FAULT_INPUT_ACCEPTANCE_DIFF',source)
        self.assertIn('NATIVE_OPERAND_ORDER_DIFF',source)
        self.assertIn('NATIVE_INPUT_COUNT_DIFF',source)
        self.assertIn('NATIVE_EMIT_PACKET_DIFF',source)
    def test_mutant_sources_and_assertion_binding(self):
        s=C.staged(C.SOURCE.read_text());caller=C.caller(C.F.SOURCE.read_text())
        self.assertIn("pbin ^ DIG'(MUTANT==1)",s)
        self.assertIn("MUTANT==2 ? CB'(eq_count_5[l-1])<=eq_left",s)
        self.assertIn('TK_MUTANT==3 ? tk_done : tk_drained_done',caller)
        bench=G.bench((V.ROOT/V.TEMPLATE).read_text())
        self.assertIn('run_case(0,512,1,0)',bench)
        self.assertIn('MUTANT_NO_DIFFERENCE',bench)
        self.assertNotIn('.o_data(assertions',bench)

class Completion(unittest.TestCase):
    def good(self):
        lines=[]
        for i,(n,k,_) in enumerate(V.cases()):lines.append(f'CASE_PASS case={i} n={n} k={k} ref_words={(k+15)//16} cand_words={(k+15)//16} delta=368 fetch_words={2*n//16}')
        lines += [f'ABORT_PASS phase={p} case=5' for p in range(1,5)]
        lines += [f'FAULT_PASS kind={k} busy={int(k>=10)}' for k in range(15)]
        return '\n'.join(lines+[K.TERMINAL])
    def mutant(self,mode):
        if mode==2:return f'MUTANT_DIFF mode=2 case=0 kind=CAND_VALUE_DIFF index=0 expected={0:0128x} actual={1<<32:0128x}'
        return f'MUTANT_DIFF mode={mode} case=0 kind=CAND_RETIRE_COUNT_DIFF index=0 expected=1 actual=0'
    def test_exact_normal_completion(self):self.assertEqual(K.verify(self.good(),0)['cases'],37)
    def test_exact_defaultoff_and_wrong_profile_refused(self):
        default=self.good().replace('delta=368','delta=0').replace('profile=0','profile=4')
        self.assertEqual(K.verify(default,4)['cases'],37)
        with self.assertRaises(ValueError):K.verify(default,0)
        with self.assertRaises(ValueError):K.verify(self.good(),4)
    def test_missing_altered_duplicate_foreign_markers(self):
        good=self.good()
        hostile=[good.replace('case=3 n=512','case=3 n=2048'),good.replace('delta=368','delta=367',1),good.replace('fetch_words=64','fetch_words=63',1),
                 good.replace('ABORT_PASS phase=2 case=5\n',''),good.replace('FAULT_PASS kind=4 busy=0','FAULT_PASS kind=4 busy=1'),
                 good+'\n'+K.TERMINAL,good+'\nFOREIGN_PASS',good.replace('CASE_PASS case=2','CASE_PASS case=1'),good.replace(K.TERMINAL,'')]
        for log in hostile:
            with self.subTest(log=log[-100:]),self.assertRaises(ValueError):K.verify(log,0)
    def test_exact_source_mutant_witnesses(self):
        for mode in (1,2,3):self.assertEqual(K.verify(self.mutant(mode),mode)['status'],'EXPECTED_MUTANT_DIFF')
    def test_hostile_diff_binding_format_index_and_terminal(self):
        good=self.mutant(2)
        hostile=[good.replace('mode=2','mode=1'),good.replace('case=0','case=37'),good.replace('index=0','index=512'),
                 good.replace('expected='+128*'0','expected='+127*'0'+'1'),
                 good.replace('actual=','actual=x'),good+'\n'+good,'MUTANT_DIFF malformed\n'+good,
                 good+'\n'+K.TERMINAL,good.replace(f'{1<<32:0128x}',f'{2<<32:0128x}'),good.replace(f'{1<<32:0128x}',128*'0')]
        for log in hostile:
            with self.subTest(log=log[-100:]),self.assertRaises(ValueError):K.verify(log,2)
    def test_crash_and_no_difference_rejected(self):
        for log in ('%Error: assertion','fatal build','MUTANT_NO_DIFFERENCE',self.good(),''):
            with self.assertRaises(ValueError):K.verify(log,1)

if __name__=='__main__':unittest.main()
