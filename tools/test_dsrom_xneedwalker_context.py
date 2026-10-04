"""Focused source/model cut checks, not an RTL or physical qualification gate."""
import hashlib,importlib.util,json,re,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'tools'/(name+'.py'))
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
M=load('dsrom_xneed_s81_context_model');C=load('dsrom_xneedwalker_context')
class XneedContext(unittest.TestCase):
    def test_cold_current_source_composition(self):
        m=M.compose();self.assertEqual(m,json.loads((M.BASE/'model_r1.json').read_text()))
        self.assertEqual(m['selected_S81']['q_only_pairs_per_rankdie'],1898)
        self.assertEqual(m['selected_S81']['layer_rankdies'],324)
        self.assertEqual(m['selected_S81']['total_dies'],368)
        self.assertEqual(m['fullfield_increment']['q_only_sites'],614952)
        self.assertIsNone(m['nonlayer_dies']['qpair_inventory'])
        self.assertFalse(m['once_only_fit']['meets_2pct_model_reserve'])
        self.assertFalse(m['physical_policy']['physical_launch_allowed'])
        self.assertEqual(m['latency']['inherited_qpipe_Rcap0_cycles'],2)
        self.assertIsNone(m['latency']['actual_selected_measured_increment_cycles'])
    def test_actual_model_only_cannot_prepare_physical_job(self):
        p=M.BASE/'inputs/epicurus_construction.json';h=hashlib.sha256(p.read_bytes()).hexdigest()
        src='rtl/v41rom/ot_v41_rom_elem_w10.sv'
        s=dict(source_owner='Epicurus',scope='DSROM xneedwalker',source_root=str(ROOT),source_commit='4d5c70aea6b67af143f42892d7e51ddfe7974cf6',
               parameters={'NSEG':8,'FAST':1},parent_instance_regex=r'^u_e\.',
               sources={src:hashlib.sha256((ROOT/src).read_bytes()).hexdigest()},
               functional_receipt={'path':str(p),'sha256':h},latency={'added_latency_cycles':0,'feedback_initiation_interval':1})
        with tempfile.TemporaryDirectory() as d:
            selection=Path(d)/'selection.json';selection.write_text(json.dumps(s))
            with self.assertRaisesRegex(ValueError,'functional terminal PASS'):C.scripts(selection,Path(d)/'job')
            self.assertFalse((Path(d)/'job').exists())
            s['source_owner']='unselected';selection.write_text(json.dumps(s))
            with self.assertRaisesRegex(ValueError,'owner selection'):C.selected(selection)
    def test_cut_and_no_source_or_clock_rewrite(self):
        for name in ('u_e.n_q[0]','u_e.nA[3]','u_e.g_qt_hit.g_hc[1].d_pos[0]','u_e.nQ2[42]'):
            self.assertRegex(name,C.ENDPOINT_RE)
        for name in ('u_e.w_q[0]','u_e.g_ch.u_c0.fwd5[4]','u_e.u_l0.p1_p[7]','u_tree.have[0]'):
            self.assertIsNone(re.search(C.ENDPOINT_RE,name))
        src=(ROOT/'tools/dsrom_xneedwalker_context.py').read_text()
        for forbidden in ('create_clock','set_clock_uncertainty','repair_timing','run_synthesis'):
            self.assertNotIn(forbidden,src)
        self.assertIn('OT_XNEED_INTERNAL_BEGIN',src);self.assertIn('OT_XNEED_EXTERNAL_BEGIN',src)
        self.assertIn('read_spef',src);self.assertIn('set_propagated_clock',src)
if __name__=='__main__':unittest.main()
