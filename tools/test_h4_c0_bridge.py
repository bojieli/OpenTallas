#!/usr/bin/env python3
"""Control properties, complete source decode and CPU-adapter isolation checks."""
import gzip,hashlib,json,pathlib,unittest,collections
import numpy as np
from h4_c0_model import sources,OUT
from h4_c0_bridge import AdmissionError,NativeDecoder,Bridge,ExistingPrimitiveAdapter,DeweyControlAdapter,dewey_scoreboard_class,CommandEncoder,shared_rank_ledger
from h3_qwen_bounded_native import NativePrimitiveVM

class ControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.q,cls.d,cls.r=sources();cls.decoder=NativeDecoder(cls.q,cls.d,cls.r)
    def fresh(self,name='Qwen'):
        b=Bridge(self.decoder,name,enabled=True,software_model=True,entries=8 if name=='Qwen' else 16,generation=17)
        desc=b.begin(0)
        src=next(v for v in desc['reads'] if self.has_home(name,v));dst=next(v for v in desc['writes'] if self.has_home(name,v))
        for v,visible in ((src,True),(dst,False)):
            h=self.decoder.source_home(name,v,0,0)['home'];b.install(v,'RF',h['slot_first'],h['vectors'],external_visible=visible)
        return b,src,dst
    def complete_outputs(self,b,src):
        for dst in self.decoder.decode(b.model,b.pc)['writes']:
            if not self.has_home(b.model,dst):continue
            if dst in b.homes and b.homes[dst].visible:continue
            if dst not in b.homes:
                h=self.decoder.source_home(b.model,dst,0,0)['home'];b.install(dst,'RF',h['slot_first'],h['vectors'])
            t=b.issue('FMUL' if b.model=='Qwen' else 'FADD',[src],dst);b.complete(t);b.ack(t,0);b.ack(t,1);b.accept_done(t)
    def has_home(self,name,v):
        try:return self.decoder.source_home(name,v,0,0).get('home',{}).get('class')=='RF'
        except AdmissionError:return False
    def test_default_off_and_hardware_closed(self):
        with self.assertRaises(AdmissionError):Bridge(self.decoder,'Qwen')
        for name in ('Qwen','DeepSeek'):
            with self.assertRaises(AdmissionError):Bridge(self.decoder,name,enabled=True)
    def test_complete_PC_and_family_decode(self):
        coverage={}
        for name,n,f in [('Qwen',1737,21),('DeepSeek',2213,30)]:
            pcs=[self.decoder.decode(name,i) for i in range(n)];families={x['family'] for x in pcs}
            self.assertEqual(len(families),f);self.assertEqual([p['pc'] for p in pcs],list(range(n)))
            for p in pcs:self.assertTrue(all(d<p['pc'] for d in p['dependencies']));self.assertFalse(p['hardware_admitted'])
            coverage[name]={'PCs':n,'families':f,'all_PCs_decoded':True,'all_family_hardware_gates_closed':True,'numeric_program_executed':False}
        (OUT/'decode_coverage.json').write_text(json.dumps(coverage,indent=2,sort_keys=True)+'\n')
    def test_source_rank_template_and_buffer_decode(self):
        count=0
        for op in self.d['instructions']:
            for rb in op['rank_bindings']:
                ids=([rb['template']] if 'template' in rb else [])+[b['template'] for b in rb.get('buffer_programs',[])]
                for tid in set(ids):
                    # Check stream head/tail without materializing huge full shapes.
                    steps=self.decoder.leaf('DeepSeek',op['pc'],rank=rb['rank'],template=tid)
                    first=next(steps);self.assertEqual(first['source_step'],self.d['templates'][tid]['code'][0]);count+=1
        self.assertGreater(count,100000)
    def test_Qwen_leaf_source_order(self):
        for op in self.q['operations']:
            for kernel in op['calendar_export']['physical_primitives']['kernel_invocations']:
                steps=list(self.decoder.leaf('Qwen',op['pc'],kernel=kernel))
                self.assertEqual([s['source_step'] for s in steps if s['substep']==0],self.q['microcode'][kernel])
    def test_Qwen_lowering_matches_all1737_PC_native_command_counts(self):
        for op in self.q['operations']:
            counted=collections.Counter()
            for kernel,n in op['calendar_export']['physical_primitives']['kernel_invocations'].items():
                for step in self.decoder.leaf('Qwen',op['pc'],kernel=kernel):counted[step['native_opcode']]+=n
            self.assertEqual(dict(counted),op['calendar_export']['physical_primitives']['native_primitive_commands'])
    def test_completion_mirror_ACK_backpressure_and_stale_owner(self):
        for name in ('Qwen','DeepSeek'):
            b,src,dst=self.fresh(name);op='FMUL' if name=='Qwen' else 'FADD';t=b.issue(op,[src],dst)
            with self.assertRaises(AdmissionError):b.ack(t,0)
            with self.assertRaises(AdmissionError):b.accept_done(t)
            with self.assertRaises(AdmissionError):b.issue(op,[src],dst)
            with self.assertRaises(AdmissionError):b.complete((18,0,1,0,0))
            b.complete(t);b.ack(t,1);self.assertFalse(b.homes[dst].visible)
            with self.assertRaises(AdmissionError):b.ack(t,1)
            with self.assertRaises(AdmissionError):b.accept_done(t)
            b.ack(t,0);self.assertTrue(b.homes[dst].visible);b.accept_done(t)
            with self.assertRaises(AdmissionError):b.complete(t)
            self.complete_outputs(b,src);b.finish()
    def test_source_consumer_and_reverse_release(self):
        b,src,dst=self.fresh();t=b.issue('FMUL',[src],dst);b.complete(t);b.ack(t,0);b.ack(t,1);b.accept_done(t);b.finish()
        with self.assertRaises(AdmissionError):b.retire(dst,consumers_done=True,reverse_grant=True)
        self.assertFalse(b.retire(src,consumers_done=True));self.assertIn(src,b.homes)
        self.assertTrue(b.retire(src,reverse_grant=True));self.assertNotIn(src,b.homes)
    def test_RF_source_geometry_and_identity_no_alias(self):
        b,src,dst=self.fresh();h=self.decoder.source_home('Qwen',src,0,0)['home']
        with self.assertRaises(AdmissionError):b.install(src,'RF',511,2)
        with self.assertRaises(AdmissionError):b.install(src,'RF',h['slot_first'],h['vectors'])
        with self.assertRaises(AdmissionError):b.install('fabricated.version','RF',32,1)
    def test_dependency_gate_and_invisible_output(self):
        b=Bridge(self.decoder,'Qwen',enabled=True,software_model=True)
        with self.assertRaises(AdmissionError):b.begin(1)
        b.begin(0)
        with self.assertRaises(AdmissionError):b.finish()
    def test_scratch64B_single_owner_and_matching_lease(self):
        b,_,_=self.fresh()
        for address,size in ((1,64),(65536,64),(0,128)):
            with self.assertRaises(AdmissionError):b.scratch_issue(address,frame_lease='existing.compiler.frame',size=size)
        t=b.scratch_issue(65472,frame_lease='existing.compiler.frame')
        with self.assertRaises(AdmissionError):b.scratch_issue(0,frame_lease='existing.compiler.frame')
        with self.assertRaises(AdmissionError):b.scratch_accept_done(t,'existing.compiler.frame')
        b.scratch_complete(t)
        with self.assertRaises(AdmissionError):b.scratch_accept_done(t,'wrong.owner')
        b.scratch_accept_done(t,'existing.compiler.frame')
    def test_unlowered_shape_and_unsupported_opcode_rejected(self):
        b,src,dst=self.fresh()
        with self.assertRaises(AdmissionError):b.issue('FMUL',[src],dst,logical_shape=[4096])
        with self.assertRaises(AdmissionError):b.issue('NOT_AN_OPCODE',[src],dst)
    def test_Dewey_reused_ACK_retirement_and_future_reader_contract(self):
        for name in ('Qwen','DeepSeek'):
            b,src,dst=self.fresh(name);a=DeweyControlAdapter(b);a.bind(src);a.bind(dst)
            t=a.issue('FMUL' if name=='Qwen' else 'FADD',[src],dst)
            a.complete(t);a.ack(t,0)
            with self.assertRaises(ValueError):a.ledger.release(a.identity(src))
            a.ack(t,1);a.accept_done(t)
            with self.assertRaises(AdmissionError):a.issue('FMUL' if name=='Qwen' else 'FADD',[src],dst)
            a.reverse_retire(t);self.complete_outputs(b,src);b.finish();a.resolve_future_PC(0)
            if name=='Qwen':a.release(src)
            else:
                with self.assertRaises(ValueError):a.release(src)  # future DS readers retain ownership
            with self.assertRaises(ValueError):a.ledger.release(a.identity(dst))
    def test_Dewey_global_HBM_alias_generation_capacity_and_future_reader(self):
        cls=dewey_scoreboard_class();s=cls(entries=2)
        s.publish((0,0,'source',1),('HBM',0,512),future_readers={'future.command'})
        with self.assertRaises(ValueError):s.publish((0,1,'alias',1),('HBM',256,512))
        with self.assertRaises(ValueError):s.release((0,0,'source',1))
        s.publish((0,0,'other',1),('RF',0,512))
        with self.assertRaises(ValueError):s.publish((0,1,'overflow',1),('RF',0,512))
        s.live[(0,0,'source',1)]['future_readers'].remove('future.command');s.release((0,0,'source',1))
        with self.assertRaises(ValueError):s.publish((0,0,'stale',1),('HBM',0,512))
        s.publish((0,1,'new',2),('HBM',0,512))
    def test_RF_temporary_capacity_lease_and_completion_drain(self):
        b,src,_=self.fresh();tmp=b.install_temporary(30,1,compiler_lease='existing.compiler.frame',paired_words=True)
        with self.assertRaises(AdmissionError):b.install_temporary(31,2,compiler_lease='existing.compiler.frame',paired_words=True)
        with self.assertRaises(AdmissionError):b.install_temporary(30,2,compiler_lease='existing.compiler.frame')
        t=b.issue('FMUL',[src],tmp);b.complete(t);b.ack(t,0);b.ack(t,1);b.accept_done(t)
        with self.assertRaises(AdmissionError):b.finish()
        self.assertTrue(b.retire(tmp,consumers_done=True,reverse_grant=True))
    def test_fixed_control_encoding_and_identity_widths(self):
        model=json.load(open(OUT/'model.json'))
        opcodes=set().union(*self.decoder.required.values())|{'CONTROL_PUBLICATION'}
        for name,p in model['programs'].items():
            c=CommandEncoder(p['encoding']['fields_bits'],opcodes);values={f:2**w-1 for f,w in c.fields.items()};values['opcode']=0;values['active_lanes']=128
            self.assertEqual(c.decode(c.encode(values)),values)
            bad=dict(values);bad['RF_dst']=512
            with self.assertRaises(AdmissionError):c.encode(bad)
            bad=dict(values);bad['source_generation_a']=2**64
            with self.assertRaises(AdmissionError):c.encode(bad)
            bad=dict(values);bad['active_lanes']=129
            with self.assertRaises(AdmissionError):c.encode(bad)
    def test_additive_model_optin_default_off(self):
        from h4_c0_model import hbm_native_c0_bridge_model
        result=hbm_native_c0_bridge_model()
        self.assertEqual(result['status'],'OFF');self.assertFalse(result['RTL_allowed'])
    def test_shared_rank_scope_prevents_cross_model_RF_alias(self):
        ledger=shared_rank_ledger();q,qsrc,_=self.fresh('Qwen');d,dsrc,_=self.fresh('DeepSeek')
        qa=DeweyControlAdapter(q,ledger);da=DeweyControlAdapter(d,ledger);qa.bind(qsrc)
        with self.assertRaises(ValueError):da.bind(dsrc)
        self.assertIs(qa.ledger,da.ledger)
    def test_per_SM_capacity_with_shared32SM_ledger(self):
        ledger=shared_rank_ledger()
        for i in range(512):ledger.publish((0,0,'occupied'+str(i),1),('RF',i*512,512))
        b,src,_=self.fresh();a=DeweyControlAdapter(b,ledger)
        with self.assertRaises(AdmissionError):a.bind(src)
    def test_failed_release_preserves_both_owned_ledgers(self):
        b,src,dst=self.fresh();a=DeweyControlAdapter(b);a.bind(src);a.bind(dst)
        with self.assertRaises(AdmissionError):a.release(dst)
        self.assertIn(dst,b.homes);self.assertIn(a.identity(dst),a.ledger.live)
    def test_sequence_counter_cannot_wrap_with_live_generation(self):
        b,src,dst=self.fresh();b.sequence=2**self.decoder.sequence_bits['Qwen']-1
        with self.assertRaises(AdmissionError):b.issue('FMUL',[src],dst)
        self.assertIsNone(b.pending);self.assertFalse(b.homes[dst].visible)
    def test_existing_CPU_primitive_adapter_only(self):
        traces={}
        for name in ('Qwen','DeepSeek'):
            b,src,dst=self.fresh(name);op='FMUL' if name=='Qwen' else 'FADD'
            value,receipt=ExistingPrimitiveAdapter(b,NativePrimitiveVM()).execute(op,[np.array([2],np.float32),np.array([2],np.float32)],[src,src],dst,shape=[1])
            self.assertEqual(value.view(np.uint32).tolist(),np.array([4],np.float32).view(np.uint32).tolist())
            self.assertEqual(receipt['scope'],'CPU_PRIMITIVE_ONLY');self.assertFalse(receipt['hardware_qualified']);self.complete_outputs(b,src);b.finish()
            traces[name]={'scope':'REPRESENTATIVE_CPU_PRIMITIVE_AND_CONTROL_ONLY','full_program_executed':False,'events':b.trace,'outstanding_RF_command':b.pending,'retained_live_versions':list(b.homes),'hardware_qualified':False}

        (OUT/'representative_control_traces.json').write_text(json.dumps(traces,indent=2,sort_keys=True)+'\n')

if __name__=='__main__':unittest.main(verbosity=2)
