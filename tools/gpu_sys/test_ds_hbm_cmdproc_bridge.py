"""Protocol-only pin tests; actual SM arithmetic is a separate live gate."""
import unittest
from tools.gpu_sys import ds_hbm_cmdproc_bridge as B

ENTRIES={name:i*64 for i,name in enumerate(B.C.D.KINDS)}


class Pins:
    def __init__(self, *, result=123, mismatch=False, fault=False):
        self.ctl=dict(cmd_v=1,cmd_op=1,cmd_idx=0,cmd_ncol=6,cmd_pos=8,
                      cmd_tok1=0,cmd_toks=[3]*6)
        self.dies=[dict(db_rdy=1,cpl_v=0,cpl_status=0,cpl_token=0) for _ in range(2)]
        self.inputs=[{},{}]; self.c={}; self.memory=[{},{}]
        self.events=[];self.now=0;self.pending={}
        self.result,self.mismatch,self.fault=result,mismatch,fault
    def snapshot(self):
        return dict(ctl=dict(self.ctl),dies=[dict(d) for d in self.dies])
    def drive_die(self,i,**ports): self.inputs[i]=ports
    def drive_ctl(self,**ports): self.c=ports
    def tick(self):
        if self.c['cmd_ready']: self.ctl['cmd_v']=0
        for i,(p,d) in enumerate(zip(self.inputs,self.dies)):
            if p['cmd_we']:
                if not d['db_rdy']: raise AssertionError('write while active')
                self.memory[i][p['cmd_addr']]=p['cmd_wdata']
            if p['db_v'] and d['db_rdy']:
                self.assert_words(i)
                d['db_rdy']=0
                self.pending[i]=self.now+2+3*i
                self.events.append(('launch',i,p['db_token'],p['db_pos']))
            if p['cpl_rdy'] and d['cpl_v']:
                d.update(cpl_v=0,db_rdy=1)
                self.events.append(('retire',i))
            if self.pending.get(i)==self.now:
                entry=self.memory[i][0]&0xffffffff
                head=entry==ENTRIES['head']
                d.update(cpl_v=1,cpl_status=1 if self.fault else (0 if head else 2),
                         cpl_token=self.result+int(self.mismatch and i==1))
                del self.pending[i]
        if self.c['am_v']: self.events.append(('argmax',self.c['am_idx']))
        if self.c['eng_done']: self.events.append(('done',))
        self.now+=1
    def assert_words(self,i):
        assert self.memory[i][1]==2<<60
        assert self.memory[i][0]>>60==1
        assert (self.memory[i][0]>>44)&0xffff==3


class BridgeTest(unittest.TestCase):
    def bridge(self,p): return B.CmdprocBridge(p,ENTRIES,noise=3519,enable=True)
    def finish(self,b):
        # A bounded protocol unit-test loop, not a production runtime cap.
        for _ in range(300):
            if b.step()['eng_done']: return
        self.fail('no actual completion join')
    def test_six_heads_join_both_dies_and_ignore_nonresult_payload(self):
        p=Pins(); b=self.bridge(p); self.finish(b)
        self.assertEqual(b.launches,12)
        self.assertEqual([x for x in p.events if x[0]=='argmax'],[('argmax',123)]*6)
        self.assertEqual(sum(x[0]=='retire' for x in p.events),24)
        self.assertEqual(p.events[-1],('done',))
    def test_missing_second_die_never_completes(self):
        p=Pins(); b=self.bridge(p)
        p.dies[1]['db_rdy']=0
        with self.assertRaisesRegex(RuntimeError,'exclusively idle'): b.step(); b.step()
        self.assertFalse(any(x[0]=='done' for x in p.events))
    def test_live_done_backpressure_retains_early_die_until_join(self):
        p=Pins(); b=self.bridge(p)
        for _ in range(40):
            b.step()
            if b.state=='WAIT' and 0 in b.completed and 1 not in b.completed:
                self.assertFalse(p.c['eng_done']); self.assertFalse(p.c['am_v']); return
        self.fail('did not exercise asymmetric completion')
    def test_cross_die_head_mismatch_refuses_and_no_retry(self):
        p=Pins(mismatch=True);b=self.bridge(p)
        with self.assertRaisesRegex(RuntimeError,'identity mismatch'): self.finish(b)
        self.assertFalse(any(x[0] in ('argmax','done') for x in p.events))
        with self.assertRaisesRegex(RuntimeError,'terminal failure'): b.step()
    def test_actual_sm_fault_aborts(self):
        p=Pins(fault=True);b=self.bridge(p)
        with self.assertRaisesRegex(RuntimeError,'completion status 1'): self.finish(b)
        self.assertFalse(any(x[0]=='done' for x in p.events))
    def test_opt_in_and_real_imem_required(self):
        with self.assertRaisesRegex(ValueError,'enable'): B.CmdprocBridge(Pins(),ENTRIES,noise=3519)
        with self.assertRaisesRegex(ValueError,'IMEM'): B.CmdprocBridge(Pins(),dict(ENTRIES,layer=16384),noise=3519,enable=True)
    def test_stage_fronts_before_backs_and_immutable_noise(self):
        cmd=dict(op='DSTAGE',idx=0,ncol=5,pos=7,toks=[],tok1=19)
        before=B.C.D.NOISE
        launches=B.lower(cmd,ENTRIES,noise=3519)
        self.assertEqual(B.C.D.NOISE,before)
        self.assertEqual([x['token'] for x in launches if x['kind']=='demb'],[19]+[3519]*4)
        kinds=[x['kind'] for x in launches]
        self.assertLess(max(i for i,v in enumerate(kinds) if v=='dsa'),min(i for i,v in enumerate(kinds) if v=='dsb'))
        with self.assertRaisesRegex(ValueError,'storage extent'): B.lower(dict(cmd,pos=30),ENTRIES,noise=3519)


if __name__=='__main__': unittest.main()
