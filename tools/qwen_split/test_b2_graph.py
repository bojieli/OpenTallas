"""Reject bus-loss, alias leakage and unbound real producers during b2 emission."""
import copy,hashlib,json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from qwen_split.b2_graph import restore_unrelated_buses,audit_preservation,bind_changed_sources,apply,audit_control_preservation,install_calibrated_sources,canonical_graph

class GraphTests(unittest.TestCase):
    def setUp(self):
        self.original=[('keep','native',4,[('a','out'),('b','in')]),
          ('tap','native',1,[('tt_ctlm','ib_bit'),('xs_tap','gi'),('res_train_issue','me_go')]),
          ('fault','native',1,[('res_train_issue','fault'),('sys_face','res_issue_fault')]),
          ('old','tree_spine',8,[('retired','old'),('lane','in')]),
          ('clock','clock_trunk',1,[('root','out'),('retired','ck')]),
          ('source_only','native',1,[('a','unused')])]
        self.new=[('new','tree_spine',8,[('half','actual'),('lane','in')])]
    def test_preserves_all_unrelated_and_fault(self):
        result,receipt=restore_unrelated_buses(self.original,self.new,{'retired'})
        self.assertEqual(audit_preservation(self.original,result,{'retired'}),4)
        self.assertIn(self.original[0],result);self.assertIn(self.original[2],result)
        self.assertEqual(result[1][3],[('tt_ctlm','ib_bit'),('xs_tap','gi')])
        self.assertEqual(len(receipt['replaced_source_taps']),1)
    def test_dropped_unrelated_mutant_fails(self):
        result,_=restore_unrelated_buses(self.original,self.new,{'retired'})
        with self.assertRaisesRegex(ValueError,'dropped unrelated'):
            audit_preservation(self.original,result[1:],{'retired'})
    def test_wrong_width_mutant_fails(self):
        result,_=restore_unrelated_buses(self.original,self.new,{'retired'})
        result[0]=('keep','native',3,result[0][3])
        with self.assertRaises(ValueError):audit_preservation(self.original,result,{'retired'})
    def test_unrelated_reset_and_clock_mutants_fail(self):
        before=[('ck','clock_trunk',1,[('clock','out'),('retired','ck'),('live','ck')]),
                ('rst','reset',1,[('reset','out'),('live','rst_n')])]
        after=[('ck','clock_trunk',1,[('clock','out'),('half','ck'),('live','ck')]),before[1]]
        audit_control_preservation(before,after,{'retired'})
        for bad in [after[:1],[('ck','clock_trunk',1,[('clock','out'),('half','ck')]),after[1]]]:
            with self.assertRaisesRegex(ValueError,'dropped'):
                audit_control_preservation(before,bad,{'retired'})
    def test_duplicate_id_refuses(self):
        with self.assertRaisesRegex(ValueError,'overwrote unrelated'):
            restore_unrelated_buses(self.original,[self.original[0]],{'retired'})
    def test_source_change_missing_producer_and_alias_mutants(self):
        with tempfile.TemporaryDirectory()as d:
            root=Path(d);src=root/'real.sv';out=root/'die.v'
            src.write_text('module actual(input wire ck,input wire [3:0] a,output wire [3:0] y); assign y=a; endmodule\n')
            rec=[dict(master='actual',source='real.sv',sha256=hashlib.sha256(src.read_bytes()).hexdigest())]
            good='module die(); wire ck; wire [3:0] n; wire [3:0] o; actual leaf(.ck(ck),.a(n),.y(o)); endmodule\n'
            out.write_text(good);self.assertEqual(bind_changed_sources(out,rec,root),1)
            for bad in [good.replace('.a(n),',''),good.replace('.a(n)','.a_part(n)'),good.replace('.a(n)','.a(ck)'),good.replace('.a(n)','.a(missing)'),good.replace('.a(n)','.a(n),.a(n)')]:
                out.write_text(bad)
                with self.assertRaises(ValueError):bind_changed_sources(out,rec,root)
            out.write_text(good);src.write_text(src.read_text()+'// changed\n')
            with self.assertRaisesRegex(ValueError,'source changed'):bind_changed_sources(out,rec,root)
    def test_calibrated_sources_require_exact_abi_and_new_identity(self):
        from types import SimpleNamespace
        def vehicle():
            ports={'ck':(1,'input'),'a':(4,'input'),'y':(4,'output')}
            model=dict(insts=[SimpleNamespace(name='tt_ctlm',master='old_controller'),
                 SimpleNamespace(name='res_train_issue',master='old_issuer')],
                 ties=[],port_join={'old_controller':{'a0':('a',[0])}},port_split={})
            prepared=dict(M={m:SimpleNamespace(name=m,note='')for m in ('old_controller','old_issuer')},
                 source_receipts=[dict(master=m,ports=ports)for m in ('old_controller','old_issuer')])
            return model,prepared
        with tempfile.TemporaryDirectory()as d:
            root=Path(d);sources={}
            for role in ('controller','issuer'):
                name='new_'+role;p=root/(name+'.sv')
                p.write_text('module '+name+'(input wire ck,input wire [3:0] a,output wire [3:0] y); assign y=a; endmodule\n')
                sources[role]=dict(module=name,path=p.name,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
            c=dict(calibrated_sources=sources,halves={str(k):dict(halfband_lnk=k)for k in range(6)})
            model,prepared=vehicle();install_calibrated_sources(model,prepared,c,root)
            self.assertEqual([i.master for i in model['insts']],['new_controller','new_issuer'])
            self.assertEqual(len(model['ties']),6)
            self.assertEqual(model['port_join']['new_controller'],model['port_join']['old_controller'])
            bad=copy.deepcopy(c);bad['halves']['0']['halfband_lnk']=55
            with self.assertRaisesRegex(ValueError,'range'):
                install_calibrated_sources(*vehicle(),bad,root)
            p=root/'new_controller.sv';p.write_text(p.read_text().replace('[3:0] a','[2:0] a'))
            with self.assertRaisesRegex(ValueError,'changed'):
                install_calibrated_sources(*vehicle(),c,root)
            c['calibrated_sources']['controller']['sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
            with self.assertRaisesRegex(ValueError,'ABI'):
                install_calibrated_sources(*vehicle(),c,root)
    def test_production_writer_refuses_until_actual_phase_join(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        model=dict(b2_bus_preservation={})
        v=SimpleNamespace(write_netlist=lambda *a: self.fail('unqualified writer ran'))
        prepared=dict(input_coverage=[],source_receipts=[])
        with patch('qwen_split.b2_graph.prepare',return_value=prepared):
            apply(v,model)
        with patch.dict('os.environ',{},clear=True):
            with self.assertRaisesRegex(ValueError,'compiler/relay calibration'):
                v.write_netlist(model,1,'must_not_exist.v')
        import types
        protocol=types.ModuleType('qwen_b2_join.phase_protocol')
        def refused(*args,**kwargs):raise ValueError('actual source/route phase OPEN')
        protocol.validate_calibration=refused
        with patch.dict(sys.modules,{'qwen_b2_join.phase_protocol':protocol}),patch.dict('os.environ',{'OT_SPLIT_B2_CALIBRATION':'unused.json'},clear=True):
            with patch('qwen_split.b2_graph.prepare',return_value=prepared),self.assertRaisesRegex(ValueError,'phase OPEN'):
                apply(v,model)

if __name__=='__main__':unittest.main()
