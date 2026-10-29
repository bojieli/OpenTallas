#!/usr/bin/env python3
"""Explicit default-off actual four-INDEX publisher/caller source proposal.

This packet composes with caller_packet.py native bank overrides. It retains the
actual single-row qctl and rejects nrows!=1; multirow requires its own source event.
"""
import argparse,hashlib,json,re
from pathlib import Path
from caller_packet import named_ports
ROLES=('SW','SE','NW','NE')
def find_call(s,name):
    pat=r'\b(\w+)[ \t]*(#\([^\n]*\))?[ \t]+'+re.escape(name)+r'\s*\((.*?)\);'
    m=re.search(pat,s,re.S)
    if not m:raise ValueError('actual caller absent '+name)
    return m,named_ports(m[3])
def call(master,name,ports,params=''):
    return master+' '+params+' '+name+' (\n'+',\n'.join(' .'+k+'('+v+')' for k,v in ports.items())+'\n);'
def emit(source,sw_master=None):
    patches=[];decl=['wire [288:0] col_idx__native_cfg;'];records=[]
    m,c=find_call(source,'col_idx')
    if m[1]!='ot_hbm_static_cfg_collar_idx256r' or '.NPR(6)' not in m[2]:raise ValueError('unexpected actual collar')
    c['native_cfg']='col_idx__native_cfg'
    patches.append((m.start(),m.end(),call('ot_hbm_static_cfg_collar_idx256r_r2048','col_idx',c,m[2][:-1].replace('.NPR(6)','.NPR(8)')+',.SINGLE_ROW_ONLY(1))')))
    for sid,role in enumerate(ROLES):
        name='hb_idx__op_'+role;m,c=find_call(source,name)
        if m[1]!='ot_hbm_idx_vm_query_static_n12' or c['sid']!="2'b"+format(sid,'02b'):raise ValueError('unexpected reader/SID '+role)
        if c['weight_sector']!='col_idx__prm[27:12]' or c['query_sector']!='col_idx__prm[43:28]':raise ValueError('old publisher changed')
        base=sid*68;c['frame_start']=f'hb_idx__qctl_{role}__frame_start[0:0]'
        for i,k in enumerate(('weight_sector','query_sector','weight_row_stride','query_row_stride')):c[k]=f'col_idx__native_cfg[{base+i*17}+:17]'
        c['vm_rq']=f'hb_idx__op_{role}__native_rq';decl.append(f'wire [143:0] {c["vm_rq"]};')
        patches.append((m.start(),m.end(),call('ot_hnx_idx_vm_query_static_n12_r2048',name,c,m[2][:-1]+',.WEIGHT_FP32(1))')))
        records.append(dict(path=name,role=role,sid=sid,old_parameters=m[2],frame_start=c['frame_start'],native_config_offset=base))
    # NW registered share: widen A, lift its existing quant client packet field by field.
    m,c=find_call(source,'hb_idx__nwsh')
    if m[1]!='ot_hbm_idx_vm_share2_static_r':raise ValueError('unexpected NW share')
    decl+=['wire [143:0] hb_idx__nwsh__native_b_rq, hb_idx__nwsh__native_rq;',f'wire [135:0] hb_idx__nwsh__legacy_b_rq = {c["b_rq"]};']
    for b in range(8):decl.append(f'assign hb_idx__nwsh__native_b_rq[{b*18}+:18] = {{hb_idx__nwsh__legacy_b_rq[{b*17+16}],hb_idx__nwsh__legacy_b_rq[{b*17+15}],1\'b0,hb_idx__nwsh__legacy_b_rq[{b*17}+:15]}};')
    c.update(a_rq='hb_idx__op_NW__native_rq',b_rq='hb_idx__nwsh__native_b_rq',vm_rq='hb_idx__nwsh__native_rq')
    patches.append((m.start(),m.end(),call('ot_hbm_idx_vm_share2_static_r_r2048','hb_idx__nwsh',c,m[2])))
    m,c=find_call(source,'hb_idx__ctl')
    if m[1]!='ot_hbm_idx_rootctl_static_am':raise ValueError('unexpected actual SW controller')
    c.update(index_rq='hb_idx__op_SW__native_rq',vm_rq='hb_idx__ctl__native_rq');decl.append('wire [143:0] hb_idx__ctl__native_rq;')
    if sw_master:patches.append((m.start(),m.end(),call(sw_master,'hb_idx__ctl',c,m[2])))
    native={}
    for role in ROLES:
        q=f'hb_idx__op_{role}__native_rq' if role in ('NE','SE') else ('hb_idx__nwsh__native_rq' if role=='NW' else 'hb_idx__ctl__native_rq')
        for b in range(8):native[f'vmb_{role}{b}']={'rq4':f'{q}[{b*18}+:18]'}
    out=source
    for a,b,text in sorted(patches,reverse=True):out=out[:a]+text+out[b:]
    # Verilog permits module-scope declarations before the final endmodule.
    end=out.rfind('endmodule');out=out[:end]+'\n'+'\n'.join(decl)+'\n'+out[end:]
    event=dict(schema='ot.idx.native_caller_event.v1',source_sha256=hashlib.sha256(source.encode()).hexdigest(),default_off=True,readers=records,config_bits=289,extra_configuration_frames=2,extra_steady_cycles=0,native_bank_overrides=native,sw_transport_master=sw_master,single_row_calendar_only=True,missing_sw_transport=not bool(sw_master),vm_data_publication_qualified=False,actual_capture_dates_qualified=False,SIGNED=False,full_token=False,holds=['actual source frontier/elaboration and calendar capture required','actual operand publication/image authority required','multirow calendar unsupported and faults before launch','physical source adoption owned by atomic plan'])
    return out,event

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--apply',action='store_true');p.add_argument('--sw-master');a=p.parse_args()
    out,event=emit(a.source.read_text(),a.sw_master)
    if a.apply and not a.sw_master:p.error('--apply requires explicit qualified SW transport master')
    a.out.mkdir(parents=True,exist_ok=False);(a.out/'event.json').write_text(json.dumps(event,indent=2)+'\n');(a.out/'native_ports.json').write_text(json.dumps(event['native_bank_overrides'],indent=2)+'\n')
    if a.apply:(a.out/'top_index_r2048.sv').write_text(out)
if __name__=='__main__':main()
