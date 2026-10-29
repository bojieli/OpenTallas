#!/usr/bin/env python3
"""Replace HEAD raw-reset aliases with private same-cycle registered pin outputs.

Runs after head_start_reset_aliases.patch_rtl. The original relay instance/name/Q
and its wavefront D/clock remain; a second kept register samples that exact D.
Only new alias ports get copies. Native existing-port reuse remains untouched.
"""
import copy,re

def prepare_plan(plan,types):
    plan=copy.deepcopy(plan);report={}
    for tn in types:
        t=plan['partition_types'][tn];rows=t.get('reset_start_raw_exports',[])
        new=[r for r in rows if not r.get('existing_port')]
        if len({r['instance'] for r in new})!=len(new):raise ValueError(tn+': multiple exports need an explicit multi-output source design')
        t['private_reset_start_exports']=True;t['cells']=int(t.get('cells',0))+len(new)
        by_port={r['port']:r for r in new}
        for pin in t.get('clock',{}).get('landing_contract',{}).get('pins',[]):
            if pin['name'] in by_port:
                r=by_port[pin['name']];pin.update(source_instance=r['instance'],source_net=r['port'],source_output_pin='export_q',
                    source_copy_from_net=r['net'],source_registered=True)
        report[tn]=dict(new_private_outputs=len(new),existing_outputs_reused=sum(bool(r.get('existing_port')) for r in rows),
            added_flops=len(new),added_cycles=0)
    return plan,report

def patch_rtl(text,t):
    if not t.get('private_reset_start_exports'):return text,dict(added_flops=0,added_cycles=0)
    rows=[r for r in t.get('reset_start_raw_exports',[]) if not r.get('existing_port')]
    for r in rows:
        pat=r'\bot_dp_rrelay\s+'+re.escape(r['instance'])+r'\s*\(([^;]+)\);'
        found=list(re.finditer(pat,text,re.S))
        if len(found)!=1:raise ValueError('private raw export requires its actual native ot_dp_rrelay source '+r['instance'])
        m=found[0];pins=m[1]
        if not re.search(r'\.q\(\s*'+re.escape(r['net'])+r'\s*\)',pins):raise ValueError('raw source Q does not match '+r['port'])
        if any(re.search(r'\.'+p+r'\(\s*[^()]+\s*\)',pins) is None for p in ('clk','d')):raise ValueError('raw source clk/D missing '+r['instance'])
        stmt='ot_dp_head_raw_export_pair '+r['instance']+' ('+pins.rstrip()+', .export_q('+r['port']+'));'
        text=text[:m.start()]+stmt+text[m.end():]
        text,n=re.subn(r'\bassign\s+'+re.escape(r['port'])+r'\s*=\s*'+re.escape(r['net'])+r'\s*;', '',text)
        if n!=1:raise ValueError('raw export must replace exactly one declared alias '+r['port'])
    return text,dict(added_flops=len(rows),added_cycles=0,private_ports=[r['port'] for r in rows])
