#!/usr/bin/env python3
"""Explicit opt-in target78 F20 boot publication graft onto grown actual banks."""
import argparse,json,re,hashlib
from pathlib import Path
from index_packet import find_call,call

def emit(s,abi):
    patches=[];decl=['wire vmload__consume,vmload__collision,vmload__fault,vmload__pending;','wire [281:0] vmload__wq;','wire [4:0] vmload__destination;','wire [31:0] vmload__legacy_valid;','wire vmload__idx_ready;']
    m,c=find_call(s,'col_idx')
    if m[1]!='ot_hbm_static_cfg_collar_idx256r_r2048':raise ValueError('grown collar required')
    p=dict(c)
    p['cfg_v']='('+c['cfg_v']+' && !vmload__consume)'
    for k in ('desc_v','launch_v'):p[k]='('+c[k]+' && !vmload__pending && !vmload__consume)'
    p['c_fault']='('+c['c_fault']+" | {4'b0,vmload__fault})";p['ready']='vmload__idx_ready'
    decl.append('assign '+c['ready']+' = vmload__idx_ready && !vmload__pending && !vmload__fault;')
    patches.append((m.start(),m.end(),call(m[1],'col_idx',p,m[2])))
    load={k:c[k] for k in ('cfg_v','cfg_target','cfg_addr','cfg_data')}
    load.update(clk=c['clk'],rst_n=c['rst_n'],index_active=c['active'],finish='('+c['desc_v']+' || '+c['launch_v']+')',legacy_write_valid='vmload__legacy_valid',consume_cfg='vmload__consume',native_wq='vmload__wq',destination='vmload__destination',collision='vmload__collision',fault='vmload__fault',pending='vmload__pending')
    decl.append(call('ot_vms_f20_boot_publish_r2048','vmload',load))
    records=[]
    for cell in [x for x in abi['cells'] if x['path'].startswith('vmb_')]:
        name=cell['path'];role=name[4:6];bid=int(name[6:]);sid=('SW','SE','NW','NE').index(role);dest=sid*8+bid
        m,p=find_call(s,name)
        if m[1]!='hfd_vms_bank_native_q0_faces_r2048_oneclk':raise ValueError('grown oneclk bank required')
        prefix='vmload__'+name;old={}
        for k in ('wq0','wq1','dq','kq','xq','xq2','pq'):
            d=cell['ports'][k];old[k]=prefix+'__old_'+k;decl.append(f'wire [{d["width"]-1}:0] {old[k]} = {d["source_expression"]};')
        val=[old[k]+f'[{cell["ports"][k]["width"]-1}]' for k in ('wq0','wq1','dq','kq','xq','xq2')]
        val.append('('+old['pq']+'[284] && '+old['pq']+'[283])')
        decl.append(f'assign vmload__legacy_valid[{dest}] = '+' || '.join(val)+';')
        hit=f'(vmload__destination == 5\'d{dest})';cl=f'(vmload__collision && {hit})';new=f'(vmload__wq[281] && {hit})'
        # Preserve all original phases and reads unless an actual new write or
        # explicit colliding write event is present at this bank.
        p['wslot_v']=f'({cl} ? 1\'b0 : ({new} ? 1\'b1 : {p["wslot_v"]}))'
        p['wslot']=f'({new} ? 3\'d1 : {p["wslot"]})'
        for k,width in [('wq0',282),('wq1',282),('dq',282),('kq',282),('xq',277),('xq2',277)]:
            expr=p[k]
            if k=='wq1':expr=f'({new} ? vmload__wq : {expr})'
            p[k]=f'({cl} ? {width}\'d0 : {expr})'
        p['pq']=f'(({cl} && {old["pq"]}[283]) ? 286\'d0 : {p["pq"]})'
        patches.append((m.start(),m.end(),call(m[1],name,p,m[2] or '')))
        records.append({'bank':name,'destination':dest,'carrier_valid_checks':7,'new_write_owner':1,'old_phases_preserved_without_new_or_collision':True})
    if len(records)!=32:raise ValueError('exactly32banks required')
    out=s
    for a,b,t in sorted(patches,reverse=True):out=out[:a]+t+out[b:]
    at=out.rfind('endmodule');out=out[:at]+'\n'+'\n'.join(decl)+'\n'+out[at:]
    e=dict(schema='ot.vm.f20_boot_publication.v1',default_off=True,source_sha256=hashlib.sha256(s.encode()).hexdigest(),target=120,header_address=3840,payload_address=3841,regular_word_address_bits=19,words_per_payload=8,header_frames_per_contiguous_region=1,payload_frames_per_sector=1,drain_cycles_after_bank_sample=5,extra_steady_cycles=0,collision_policy='suppress new and all colliding writecarriers; preserve readonly pq and readslots; actual target78 fault',banks=records,whole_image_qualified=False,runtime_computed_A_replication_qualified=False,source_selected=False,SIGNED=False)
    return out,e

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('source','abi','out'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--apply',action='store_true');a=p.parse_args();out,e=emit(a.source.read_text(),json.loads(a.abi.read_text()));a.out.mkdir(exist_ok=False,parents=True);(a.out/'event.json').write_text(json.dumps(e,indent=2)+'\n')
    if a.apply:(a.out/'top_publish_r2048.sv').write_text(out)
if __name__=='__main__':main()
