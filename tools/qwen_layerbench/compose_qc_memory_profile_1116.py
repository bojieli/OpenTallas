#!/usr/bin/env python3
"""Compose current native memory3/1 ages from component receipts, never legacy ages."""
import argparse,hashlib,json
from pathlib import Path

FLAT='52ba50094b38e8438837cfca3c846ece2c58ac98e9983022c0f773c55b28a4a4'
PROFILE={'sram_if_mif':1,'relative_memory_alignment':3}

def require(ok,msg):
    if not ok: raise ValueError(msg)
def read(p): return json.loads(Path(p).read_text())
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def row(receipt,fixture,op):
    for r in receipt['runs']:
        if r['fixture']==fixture:
            require(r['rtl_terminal_pass'],f'{fixture} did not pass')
            for a in r['rows']:
                if a.get('op')==op and 'mif_first' in a:
                    require(a['faults']=='0/0' and a['count0']==a['count1'],f'{fixture} native fault/count')
                    require(a['mif_first']-a['base_first']==2 and a['mif_last']-a['base_last']==2,f'{fixture} unexpected differential')
                    return a
    raise ValueError(f'missing qualified {fixture} op{op}')
def dynamic(ledger,fixture,op):
    for r in ledger['dynamic_cases']:
        if r['fixture']==fixture:
            require(r['pass_verdict'],f'{fixture} did not pass')
            for a in r['rows']:
                if a.get('op')==op and 'mif_first' in a:
                    require(a['faults']=='0/0' and a['count0']==a['count1'],f'{fixture} fault/count')
                    return a
    raise ValueError(f'missing dynamic case {fixture}/{op}')
def sampled(a,key): return a[key]-1  # drive-negedge counter origin -> actual input sampling posedge

def compose(su,static,head,red):
    require(su['source_flat_sha256']==FLAT,'SU source mismatch')
    require(su['profile1']==PROFILE,'SU memory profile mismatch')
    require(static['prefix']['edges']==3 and static['native_d2d_suffix']['edges']==3 and static['native_sc_psum_suffix']['edges']==3,'unreviewed static boundary')
    require(head['schema']=='opentallas.qwen.native-head-emission-profile.v2' and head['status']=='PASS_COMPONENT','HEAD receiver receipt missing/PASS required')
    require(head['memory_profile']=={'MEMORY_ALIGNMENT':3,'MEMORY_READ_EXTRA':1},'HEAD memory mismatch')
    require(head['source_projection_metadata']['flat_sha256']==FLAT,'HEAD source mismatch')
    require(all(c['result']=='CAUGHT' for c in head['controls'].values()) and len(head['controls'])>=3,'HEAD negative controls missing')
    copy=row(su,'single',0); ssq=row(su,'single',2); rs=row(su,'single',3); silu=row(su,'silu_sigm',1)
    require(sampled(copy,'mif_first')==61,'native input origin or source changed')
    residual=dynamic(static,'residual_readback3',2)
    require(residual['mif_first']==ssq['mif_first'] and residual['count1']==256 and residual['mif_last']-ssq['mif_last']==16,'residual scalar cadence mismatch')
    require(len(head['slices'])==12,'HEAD production slice map missing')
    for s in head['slices']:
        a=s['command_input_ages']; beats=s['BF16_receiver_beats']
        require(a['write_age']==61 and a['stream_age']-a['write_age']==11,'HEAD first packing mismatch')
        require(a['last_stream_age']-a['last_write_age']==4,'HEAD tail packing mismatch')
        require([x['offset'] for x in beats]==list(range(a['stream_age'],a['last_stream_age']+1,8)),'HEAD beat calendar mismatch')
    # RED receipt is a normalized boundary receipt, not an old per-op age file.
    require(red['schema']=='opentallas.qc.native-red-age.v1' and red['status'] in ('PASS_COMPONENT','PASS_TIMING_COMPONENT'),'current RED receipt required')
    require(red['row_input_beats']==16,'RED row shape mismatch')
    require(red['selected_input_pipeline_edges']==2 and red['selected_output_pipeline_edges']==3,'selected RED physical profile mismatch')
    require(red['producer_to_next_receiver_edges']==1,'RED receiver phase mismatch')
    require(red['ctl_input_to_vm_publication_receiver_edges']==7,'VM publication path mismatch')
    require(len(red['source_sha256'])==64,'RED source pin missing')
    base=red['first_input_to_producer_output_edges']
    require(type(base) is int and base>=15,'invalid measured RED base age')
    prefix=static['prefix']['edges']; dd=static['native_d2d_suffix']['edges']; sc=static['native_sc_psum_suffix']['edges']
    red_first=prefix+sampled(ssq,'mif_first')+base+2+3+1
    ps=[red_first+sc+16*j for j in range(3)]
    root_cfg=4 # fixed compiler command guard; independent of SU memory-read age
    scalar={'schema':'opentallas.qwen.dv-slice-ages.v1','memory_profile':PROFILE,'slice_rtl':'s8','ssq_psum_out':ps,'root_cfg_lead':root_cfg,
            'per_slice':{str(s['slice']):ps[:s['FP32_words']//128] for s in head['slices']}}
    def dd_array(a):
        first=sampled(a,'mif_first')+prefix+dd; last=sampled(a,'mif_last')+prefix+dd
        require(last-first+1==a['count1']//8 or a['count1']==1,'D2D cadence mismatch')
        return list(range(first,last+1))
    d2d={'rs':[sampled(rs,'mif_first')+prefix+dd],
         'qn':dd_array(dynamic(static,'qn_rope_lo',1)),
         'rope_q':dd_array(dynamic(static,'qn_rope_lo',3)),
         'rope_k':dd_array(dynamic(static,'rope_hi_v',1)),
         'v':dd_array(dynamic(static,'v_gur',1)),
         'gur':dd_array(dynamic(static,'v_gur',3))}
    # Readback3 has the same fixed command and sixteen beats per repeated row;
    # HEAD receiver receipt measures the full three-row control and packing span.
    d2d['readback']=dd_array(dynamic(static,'residual_readback3',3))
    xs=[x['offset']+prefix for x in max(head['slices'],key=lambda x:x['FP32_words'])['BF16_receiver_beats']]
    silu_first=sampled(silu,'mif_first')+11+prefix
    vector={'schema':'opentallas.qwen.dv-slice-vec-ages.v1','memory_profile':PROFILE,'slice_rtl':'s8','add_psum_out':ps,'xs_out':xs,
            'silu_out':[silu_first,silu_first+8],'red_vm':red_first+7,'root_cfg_lead':root_cfg,'d2d':d2d}
    note={'schema':'opentallas.qc.memory-profile-composition.v1','status':'PASS_COMPOSED_COMPONENTS','memory_profile':PROFILE,
          'origin':'actual flat cmd_i sampling posedge to receiver sampling posedge; final bound lane transport remains separate',
          'native_zero_parent_transport':True,'bound_profile_adoption':False,'raw_su_origin_conversion':-1,'prefix':prefix,'d2d_suffix':dd,'red_measured_base':base,'red_selected_IN_OUT':5,
          'red_producer_to_next_receiver':1,'sc_suffix_from_input_receiver':sc,'vm_publication_from_ctl_input_receiver':7,
          'source_flat_sha256':FLAT,'static_source_sha256':static['source_sha256'],'HEAD_stream_source_sha256':head['stream_source_sha256'],'RED_source_sha256':red['source_sha256'],'RED_qualification_status':red['status'],'RED_scope':red.get('scope','See RED receipt'),
          'root_cfg_lead_note':'Fixed four-edge compiler ROOT-configuration guard, not an SU read age; preserved separately from measured SU ages.',
          'qualification_limit':'Native zero-parent-transport composition only; final bound READ_EXTRA9 is not qualified by this memory1 receipt. Current native component composition only. Requires selected source/plan transport dates and final bound shared calendar before programme/token adoption.'}
    scalar['composition']=note;vector['composition']=note
    return scalar,vector,note

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('su','static','head','red'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    try:
        scalar,vector,ledger=compose(*(read(getattr(a,k)) for k in ('su','static','head','red')))
        require(not a.out.exists(),'output directory already exists; preserve prior verdict')
        ledger['receipts']={k:{'path':str(getattr(a,k)),'sha256':sha(getattr(a,k))} for k in ('su','static','head','red')}
        a.out.mkdir(parents=True)
        (a.out/'inputs').mkdir()
        for k in ('su','static','head','red'):
            (a.out/'inputs'/f'{k}.json').write_text(getattr(a,k).read_text())
        for name,value in [('slice_ages.json',scalar),('vec_ages.json',vector),('composition.json',ledger)]:
            (a.out/name).write_text(json.dumps(value,indent=2)+'\n')
        print(json.dumps({'status':ledger['status'],'out':str(a.out),'ssq_psum_out':scalar['ssq_psum_out'],'xs_out':vector['xs_out'],'silu_out':vector['silu_out'],'red_vm':vector['red_vm']}))
    except (ValueError,KeyError,OSError,TypeError) as e:p.exit(2,f'profile composition refused: {e}\n')
if __name__=='__main__':main()
