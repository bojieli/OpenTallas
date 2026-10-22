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
        return dict(master=master,source=SRC,rtl_deps=[G+'ot_hbm_su_indexed_scalar.sv','rtl/hbm_accel/generic/vm/static/ot_static_program_target.sv',G+'ot_hbm_su_indexed_scalar_banked.sv','rtl/lib/ot_rst_relay.sv'],
                    params=params or {},ports=ps,slot=None,owner='CODEX-HBM-IDXSU-2000',region='su_indexed_gather',
                    note='Candidate explicit static VM RG0/WG0 reservation; no release or physical-age claim')
    def edge(label, src, dst, bits):
        E.append(dict(name='indexed_gather_'+label,bits=bits,source=src,sink=dst,clock='stream',ready_or_credit=False,
                      allowed_exception=None,basis='Existing indexed engine plus dated F20 producer; compiler static reservation',region='su_indexed_gather'))
    def ep(n,p,b,lo=0): return [n,p,lo,lo+b]
    cfg={'cfg_v':1,'cfg_target':8,'cfg_addr':12,'cfg_data':256,'desc_v':1,'desc_base':12,'desc_limit':13,'desc_loops':16,'launch_v':1}
    out={'rq':32*17,'wq':32*281,'active':1,'done':1,'program_fault':1,'configured':1,'target_fault':1,'engine_fault':1,
         'edge_index':16,'engine_busy':1,'engine_done':1,'engine_start':1,'descriptor':120,'active0':1,'active1':1,'reservation_active':1}
    I[name]=inst('ot_hbm_su_indexed_scalar_f20',ports({'clk':1,'rst_n':1,'rr':32*257,**cfg},out),
                 {'READ_SAMPLE':read_sample,'WRITE_COMMIT':write_commit,'TARGET':180,'NATIVE_BANKED':1,'SEGMENTED96':1})
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
            edge(n+'_reserve',ep(name,'active0' if j<16 else 'active1',1),ep(n,'reserve',1),1)
            ck(n)
            inventory.append(dict(bank=bank,selector=n,read_owner=0,write_owner=0,preserved_sources=owners))
    c['clock_resets']+=clocks
    # Target membership and faults are real host-status inputs, not open debug.
    hs=I['host_status'];nt=int(hs['params']['NT']);nf=int(hs['params']['NF'])
    width,packed=hs['params']['TGTS'].split("'h")
    assert int(width)==nt*8
    assert 180 not in bytes.fromhex(packed.zfill(nt*2))
    hs['params'].update(NT=nt+1,NF=nf+35,TGTS=f"{(nt+1)*8}'h"+'b4'+packed.zfill(nt*2))
    for p in ['t_ready','t_active']: hs['ports'][p]['bits']=nt+1
    hs['ports']['t_fault']['bits']=nf+35
    edge('target_ready',ep(name,'configured',1),ep('host_status','t_ready',1,nt),1)
    edge('target_active',ep(name,'reservation_active',1),ep('host_status','t_active',1,nt),1)
    for j,p in enumerate(['target_fault','program_fault','engine_fault']):
        edge('target_'+p,ep(name,p,1),ep('host_status','t_fault',1,nf+j),1)
    for j,r in enumerate(inventory):
        edge(r['selector']+'_fault',ep(r['selector'],'fault',1),ep('host_status','t_fault',1,nf+3+j),1)
    # The host ingress must accept the new F20 target before its leaf can see it.
    ing=I['host_cp_ingress'];mw,mhex=ing['params']['TARGET_MASK'].split("'h")
    assert int(mw)==256
    ing['params']['TARGET_MASK']=f"256'h{int(mhex,16)|(1<<180):064x}"
    for changed in ['host_status','host_cp_ingress']:
        for key in ['physical_view','closed_record']:
            I[changed].pop(key,None)
        I[changed]['force_synth']=True
    for p,b in out.items():
        if p not in ['rq','wq','active0','active1','reservation_active','configured','target_fault','program_fault','engine_fault']:
            c['open_outputs'].append([name,p,b])
    c.setdefault('notes',[]).append('Indexed gather is opt-in candidate; all faults and target readiness join real host_status. Physical homes, source-ready dates, calendar drain guards and post-landing age proof remain required.')
    report=dict(schema='opentallas.hbm.indexed_gather.binding_candidate.v1',target=180,clock='stream',endpoint=name,
                READ_SAMPLE=read_sample,WRITE_COMMIT=write_commit,banks=inventory,
                descriptor_fields={'index_word':[0,24],'score_base':[24,24],'score_limit':[48,24],'dest_word':[72,24],'dyn_mul':[96,24],'start':[120,16],'release_exclusive':[136,16],'rank1_base':[152,24],'rank2_base':[176,24],'rank3_base':[200,24]},
                required_release_gap=2*read_sample+write_commit+7,selector_capture_edges=2,first_start_min=2,final_ownership_tail=2,SEGMENTED96=1,NATIVE_BANKED=1,release_ready=False,
                open=['Measured source-ready dates','Exact F20 launch-to-local-edge-zero measurement','Actual mapped route/clock/reset qualification','Host readiness round-trip GUARD after route','All native client/calendar drain guards','Post-landing latency equality'])
    return c,report

def main():
    a=argparse.ArgumentParser();a.add_argument('graph');a.add_argument('out');a.add_argument('--report',required=True)
    a.add_argument('--read-sample',required=True,type=int);a.add_argument('--write-commit',required=True,type=int);v=a.parse_args()
    raw=Path(v.graph).read_bytes();c,r=bind(json.loads(raw),v.read_sample,v.write_commit);r['source_die_sha256']=hashlib.sha256(raw).hexdigest()
    Path(v.out).write_text(json.dumps(c,indent=2)+'\n');Path(v.report).write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
