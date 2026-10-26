#!/usr/bin/env python3
"""Wire-only RAW2341 projection from actual compressed q3 body cut pins.
The canonical wrapper scalar-to-packed bindings are authoritative. qout[k]
is a 32-bit CHUNK across destinations, not a whole destination/flit.
"""
import argparse,hashlib,json,re
from pathlib import Path

def project(text):
    up={}
    rx=r"\.\\(u_body\.u_upipe\.SL\[(\d+)\]\.u\.d3\[(\d+)\])\s+\((u_body_u_upipe_SL_\d+_u_d3)\[(\d+)\]\)"
    for escaped,sl,bit,port,pbit in re.findall(rx,text):up[96*int(sl)+int(bit)]=(port,int(pbit))
    qo={}
    rx=r"\.\\(u_body\.g_qout\[(\d+)\]\.g3\.[wn]\.o\.u_out\.u\.dst_d\[(\d+)\])\s+\((u_body_g_qout_\d+_g3_[wn]_o_u_out_u_dst_d)\[(\d+)\]\)"
    for esc,chunk,bit,port,pbit in re.findall(rx,text):qo[int(chunk),int(bit)]=(port,int(pbit))
    valid={}
    rx=r"\.\\u_body\.g_qout\[0\]\.g3\.w\.o\.u_out\.u\.dst_v\[(\d+)\]\s+\((u_body_g_qout_0_g3_w_o_u_out_u_dst_v)\[(\d+)\]\)"
    for orig,port,pbit in re.findall(rx,text):valid[int(orig)]=(port,int(pbit))
    fields=[('tkx_arg_mode',0,704,1),('tkx_cfg_g',1,761,8),('tkx_cfg_gbase',9,769,8),('tkx_cfg_has_r',17,873,1),('tkx_cfg_k',18,735,13),('tkx_cfg_n',31,723,12),('tkx_cfg_nout',43,748,13),('tkx_cfg_obase',56,793,40),('tkx_cfg_pf',96,777,16),('tkx_cfg_rbase',112,833,40),('tkx_del_slot',2332,719,4),('tkx_start',2340,718,1)]
    rows={}
    for field,offset,glob,width in fields:
        for j in range(width):
            port,bit=up[glob+j];rows[offset+j]=dict(raw_bit=offset+j,field=field,field_bit=j,source_port=port,source_bit=bit,native_inst_bit=glob+j)
    for lane in range(4):
        dst=11+lane
        for j in range(545):
            chunk=j//32;cw=1 if chunk==17 else 32;orig=dst*cw+j%32
            port,bit=qo[chunk,orig];idx=152+545*lane+j
            rows[idx]=dict(raw_bit=idx,field='tkx_del_flit',field_bit=545*lane+j,source_port=port,source_bit=bit,native_chunk=chunk,native_destination=dst,native_chunk_bit=orig)
        port,bit=valid[dst];idx=2336+lane
        rows[idx]=dict(raw_bit=idx,field='tkx_del_valid',field_bit=lane,source_port=port,source_bit=bit,native_destination=dst)
    if sorted(rows)!=list(range(2341)):raise ValueError('RAW2341 coverage failure')
    if len({(v['source_port'],v['source_bit']) for v in rows.values()})!=2341:raise ValueError('actual pin alias/duplicate')
    widths={p:int(hi)+1 for hi,p in re.findall(r'output wire \[(\d+):0\] (\w+)',text)}
    ranges=[]
    for i,v in sorted(rows.items()):
        if ranges and v['source_port']==ranges[-1]['source_port'] and v['source_bit']==ranges[-1]['source_lsb']+ranges[-1]['width'] and i==ranges[-1]['raw_lsb']+ranges[-1]['width']:
            ranges[-1]['width']+=1
        else:ranges.append(dict(raw_lsb=i,source_port=v['source_port'],source_lsb=v['source_bit'],width=1))
    ports=sorted({v['source_port'] for v in rows.values()})
    return dict(schema='opentallas.hbm.q3_actual_cut_to_tkx.v1',status='EXACT_WIRE_PROJECTION_NOT_PRODUCER_PROGRAMME_RESET_ADOPTION',canonical_source_sha256=hashlib.sha256(text.encode()).hexdigest(),raw_bits=2341,unique_actual_pin_bits=2341,ranges=ranges,canonical_ports={p:widths[p] for p in ports},bits=[rows[i] for i in range(2341)])

def sv(meta):
    text='`timescale 1ns/1ps\n`default_nettype none\n// Logical wires only; no new physical partition, registers, clock or tied pins.\nmodule ot_hbm_tkx_q3_cut_pack(\n'
    text+=',\n'.join(' input wire[%d:0] %s'%(w-1,p) for p,w in sorted(meta['canonical_ports'].items()))+',\n output wire[2340:0]raw\n);\n'
    for v in meta['ranges']:text+=' assign raw[%d+:%d]=%s[%d+:%d];\n'%(v['raw_lsb'],v['width'],v['source_port'],v['source_lsb'],v['width'])
    return text+'endmodule\n`default_nettype wire\n'

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--body-core',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    m=project(a.body_core.read_text());a.out.mkdir(parents=True,exist_ok=True)
    (a.out/'q3_cut_to_tkx_map.json').write_text(json.dumps(m,indent=2)+'\n')
    (a.out/'ot_hbm_tkx_q3_cut_pack.sv').write_text(sv(m))
    print('Q3_CUT_PACK PASS raw2341 unique2341 ranges%d canonical_ports%d source%s'%(len(m['ranges']),len(m['canonical_ports']),m['canonical_source_sha256']))
if __name__=='__main__':main()
