#!/usr/bin/env python3
"""Opt-in source binding for the existing indexed gather engine. Candidate only.

All 32 native RG0/WG0 owners are preserved behind programme-selected local
selectors. Calendar owner slots remain driven by the existing calendars. The
compiler must reserve those slots and keep the old clients idle, including
transport drain/return guards. Post-landing ages must be proven separately.
"""
import argparse, copy, hashlib, json
from pathlib import Path
G='rtl/hbm_accel/generic/adapters/static_su/gather/'
SRC=G+'ot_hbm_su_indexed_scalar_f20.sv'

def bind(graph, read_sample, write_commit):
    c=copy.deepcopy(graph);I=c['instances'];E=c['edges'];name='su_indexed_gather'
    assert name not in I
    used={int(s['value']) for s in c['straps'] if s['port']=='tgt'}
    assert 180 not in used, 'F20 target 180 already owned'
    def ports(ins, outs):
        return {p:{'direction':d,'bits':b} for d,ps in [('input',ins),('output',outs)] for p,b in ps.items()}
    def inst(master, ps, params=None):
        return dict(master=master,source=SRC,rtl_deps=[G+'ot_hbm_su_indexed_scalar.sv','rtl/hbm_accel/generic/vm/static/ot_static_program_target.sv'],
                    params=params or {},ports=ps,slot=None,owner='CODEX-HBM-IDXSU-2000',region='su_indexed_gather',
                    note='Candidate explicit static VM RG0/WG0 reservation; no release or physical-age claim')
    def edge(label, src, dst, bits):
        E.append(dict(name='indexed_gather_'+label,bits=bits,source=src,sink=dst,clock='stream',ready_or_credit=False,
                      allowed_exception=None,basis='Existing indexed engine plus dated F20 producer; compiler static reservation',region='su_indexed_gather'))
    def ep(n,p,b,lo=0): return [n,p,lo,lo+b]
    cfg={'cfg_v':1,'cfg_target':8,'cfg_addr':12,'cfg_data':256,'desc_v':1,'desc_base':12,'desc_limit':13,'desc_loops':16,'launch_v':1}
    out={'rq':32*17,'wq':32*281,'active':1,'done':1,'program_fault':1,'configured':1,'target_fault':1,'engine_fault':1,
         'edge_index':16,'engine_busy':1,'engine_done':1,'engine_start':1,'descriptor':120}
    I[name]=inst('ot_hbm_su_indexed_scalar_f20',ports({'clk':1,'rst_n':1,'rr':32*257,**cfg},out),
                 {'READ_SAMPLE':read_sample,'WRITE_COMMIT':write_commit,'TARGET':180})
    for p,b in cfg.items():
        # Copy the actual released host-leaf producer, not a top-level test pin.
        original=[e for e in E if e['sink'][:2]==['calendar_SW',p]]
        assert len(original)==1,(p,original)
        edge('f20_'+p,original[0]['source'],ep(name,p,b),b)
    clocks=[]
    def ck(n):
        for p,kind,source in [('clk','clock',['hb_ckgen','pll_stream']),('rst_n','reset',['hb_ckgen','por_stream'])]:
            clocks.append(dict(instance=n,port=p,bits=1,domain='stream',kind=kind,source=source))
    ck(name)
    inventory=[]
    for q,qn in enumerate(['SW','SE','NW','NE']):
        for b in range(8):
            bank=f'vmb_{qn}{b}';n=f'indexed_gather_select_{qn}{b}';j=q*8+b
            assert I[bank]['master']=='hfd_vms_bank_native_q0_faces', (bank,I[bank]['master'])
            I[n]=inst('ot_hbm_su_indexed_scalar_bank_select',ports(
                {'clk':1,'rst_n':1,'reserve':1,'normal_rq':17,'gather_rq':17,'normal_wq':281,'gather_wq':281,'bank_rr':257,'bank_done':1},
                {'bank_rq':17,'bank_wq':281,'normal_rr':257,'gather_rr':257,'normal_done':1,'fault':1}))
            owners={}
            for pin,muxpin,width in [('rq0','normal_rq',17),('wq0','normal_wq',281)]:
                matches=[e for e in E if e['sink'][:2]==[bank,pin]]
                assert len(matches)==1,(bank,pin,matches)
                e=matches[0];owners[pin]=e['source'];e['sink']=ep(n,muxpin,width)
                edge(n+'_'+pin,ep(n,'bank_'+pin[:2],width),ep(bank,pin,width),width)
            for pin,muxpin,width in [('rr0','normal_rr',257),('wq_done0','normal_done',1)]:
                matches=[e for e in E if e['source'][:2]==[bank,pin]]
                assert len(matches)==1,(bank,pin,matches)
                matches[0]['source']=ep(n,muxpin,width)
                edge(n+'_'+pin,ep(bank,pin,width),ep(n,'bank_rr' if pin=='rr0' else 'bank_done',width),width)
            for p,width in [('rq',17),('wq',281)]:
                edge(n+'_'+p,ep(name,p,width,j*width),ep(n,'gather_'+p,width),width)
            edge(n+'_rr',ep(n,'gather_rr',257),ep(name,'rr',257,j*257),257)
            edge(n+'_reserve',ep(name,'active',1),ep(n,'reserve',1),1)
            ck(n);c['open_outputs'].append([n,'fault',1])
            inventory.append(dict(bank=bank,selector=n,read_owner=0,write_owner=0,preserved_sources=owners))
    c['clock_resets']+=clocks
    for p,b in out.items():
        if p not in ['rq','wq','active']:c['open_outputs'].append([name,p,b])
    c.setdefault('notes',[]).append('Indexed gather source is opt-in candidate; physical homes, fault aggregation, source-ready dates, calendar reservation and exact post-landing latency remain required before release.')
    report=dict(schema='opentallas.hbm.indexed_gather.binding_candidate.v1',target=180,clock='stream',endpoint=name,
                READ_SAMPLE=read_sample,WRITE_COMMIT=write_commit,banks=inventory,
                descriptor_fields={'index_word':[0,24],'score_base':[24,24],'score_limit':[48,24],'dest_word':[72,24],'dyn_mul':[96,24],'start':[120,16],'release_exclusive':[136,16]},
                required_release_gap=2*read_sample+write_commit+7,release_ready=False,
                open=['Measured source-ready dates','Exact F20 launch-to-local-edge-zero measurement','Actual mapped route/clock/reset qualification','Fault aggregation','All native client/calendar drain guards','Post-landing latency equality'])
    return c,report

def main():
    a=argparse.ArgumentParser();a.add_argument('graph');a.add_argument('out');a.add_argument('--report',required=True)
    a.add_argument('--read-sample',required=True,type=int);a.add_argument('--write-commit',required=True,type=int);v=a.parse_args()
    raw=Path(v.graph).read_bytes();c,r=bind(json.loads(raw),v.read_sample,v.write_commit);r['source_die_sha256']=hashlib.sha256(raw).hexdigest()
    Path(v.out).write_text(json.dumps(c,indent=2)+'\n');Path(v.report).write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
