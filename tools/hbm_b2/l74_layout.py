#!/usr/bin/env python3
"""Concrete native hub->root source-bit layout for DATA L74 and correlated CTL L89.
Derives source bits from the emitted die, preserving aliases and rebuilt widths.
Pulse/control masks distinguish transactions from sticky status levels. These
masks and both path depths are the serializer/compiler interface, not a token gate.
"""
import argparse,collections,gzip,json,re
from pathlib import Path
import b2_top as T

def pulse_bits(inst,port,bits):
    if inst.startswith('epcal_') and port=='payload':return {38,47,49}&bits
    if port in {'tx_pin_v','tkx_del_valid','tkx_start','valid','done','cfg_v','desc_v','launch_v'} or port.endswith(('_v','_done')):return bits
    if inst.startswith('hb_vms_') and port=='cr':return {273,547}&bits
    if inst.startswith('hb_idx__op_') and port=='vm_rq':return set(range(16,136,17))&bits
    if inst.startswith('vmb_') and port=='rr4':return {256}&bits
    if inst.startswith('stl_') and port=='up_o':return {40}&bits
    return set()

def hold_bits(inst,port,bits):
    # Persistent control/status must remain known before the first frame and
    # between frames. They are not pulses and must not trip slot1 phase checks.
    if port in {'fault','eng_fault','tgt_fault','ps_f','vmstat','busy','active','configured','s_ready','s_active','s_fault'}:
        return bits
    return set()

def ranges(bits):
    out=[]
    for b in sorted(bits):
        if out and out[-1][1]+1==b:out[-1][1]=b
        else:out.append([b,b])
    return out

def layout(die,plan,cmap,census):
    d=T.Die(die,[]);cm=json.loads(Path(cmap).read_text());cm['parts']['b2_ep1_root']='root'
    parts={}
    for n in d.insts:
        if n in cm['parts']:parts[n]=[cm['parts'][n]]
        else:
            for rx,g in cm['rules']:
                if re.search(rx,n):parts[n]=cm['groups'][g];break
    kinds={(g['src'],g['src_bus'],g['dst'],g['dst_bus']):g['kind'] for g in json.load(gzip.open(census,'rt'))['groups']}
    def kind(si,sp,ki,kp):
        for f in (lambda x:x,lambda x:re.sub(r'(?<=_)NE(?=\d|_|$)','SW',x)):
            k=kinds.get((f(si),sp,f(ki),kp))
            if k:return 'ctl' if k=='ctl' else 'data'
        return 'data'
    traffic=collections.defaultdict(set);sinks=collections.defaultdict(set)
    for ki,i in d.insts.items():
        if parts.get(ki)!=['root']:continue
        for kp,e in i['conns'].items():
            if d.dirs.get(e)=='output':continue
            for s,_ in d.resolve(T.parse_expr(e,d.widths)):
                if s[0]!='n' or s[1] not in d.driver:continue
                si,sp=d.driver[s[1]];pa=parts.get(si)
                if pa not in [['NW_hub'],['NE_hub']]:continue
                key=(pa[0],kind(si,sp,ki,kp),si,sp)
                traffic[key].update(range(s[2],s[3]+1));sinks[key].add(ki+'.'+kp)
    p=json.loads(Path(plan).read_text());out={}
    for q,suffix in [('NW_hub',''),('NE_hub','m')]:
        out[q]={}
        for kd,lane in [('data','L74'+suffix),('ctl','L89'+suffix)]:
            offset=0;rows=[];mask=0;hmask=0
            for key,bits in sorted(traffic.items()):
                part,k,si,sp=key
                if part!=q or k!=kd:continue
                pulses=pulse_bits(si,sp,bits);holds=hold_bits(si,sp,bits)-pulses;local=[j for j,b in enumerate(sorted(bits)) if b in pulses]
                for j in local:mask|=1<<(offset+j)
                held=[j for j,b in enumerate(sorted(bits)) if b in holds]
                for j in held:hmask|=1<<(offset+j)
                rows.append(dict(source=si,port=sp,ranges=ranges(bits),width=len(bits),offset=offset,
                                 control_positions=local,hold_positions=held,sinks=sorted(sinks[key])))
                offset+=len(bits)
            lat=p['latency']['lanes'][lane]
            out[q][kd]=dict(lane=lane,width=offset,fields=rows,control_mask=hex(mask),hold_mask=hex(hmask),cycles=lat['cycles'],
                            boundary=lat['boundary'],stations=lat['stations'])
        out[q]['ctl_padding_to_data']=out[q]['data']['cycles']-out[q]['ctl']['cycles']
    return out

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--die',required=True);ap.add_argument('--plan',required=True);ap.add_argument('--census-map',required=True);ap.add_argument('--census',default='physical/die_plan/hbm/inputs/census/hbm_census.json.gz');ap.add_argument('--out',required=True);a=ap.parse_args()
    r=layout(a.die,a.plan,a.census_map,a.census);Path(a.out).write_text(json.dumps(r,indent=1))
    for q,v in r.items():print('L74_LAYOUT',q,'data',v['data']['width'],'ctl',v['ctl']['width'],'ctl_pad',v['ctl_padding_to_data'])
if __name__=='__main__':main()
