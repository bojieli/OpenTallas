#!/usr/bin/env python3
"""Execute generated PDN Tcl control flow with source-derived master/pin mocks.

No pdngen or physical qualification. This traces actual Tcl glob/regexp grid
selection over the entire emitted netlist and LEF library without creating ODBs.
The actual grid geometry is independently covered by the OpenROAD fixture.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import tkinter
from .apply_case import NAMES

def trace(case):
    case=Path(case);interp=tkinter.Tcl();masters={};layers={};heights={}
    files=list(case.glob('*.lef'))
    for file in files:
        for m in re.finditer(r'(?ms)^MACRO (\S+)\n(.*?)^END \1\s*$',file.read_text()):
            name,body=m.groups();masters[name]=bool(re.search(r'CLASS BLOCK',body))
            heights[name]=round(float(re.search(r'SIZE [\d.]+ BY ([\d.]+)',body)[1])*1000)
            vdd=re.search(r'(?ms)^\s*PIN VDD\s*\n(.*?)^\s*END VDD',body)
            layers[name]=sorted(set(re.findall(r'LAYER (M\d+)\s*;',vdd[1]))) if vdd else []
    net=(case/'die.v').read_text();instances={}
    for master,inst in re.findall(r'(?m)^\s*(\w+)\s+(\w+)\s*\(',net):
        if master in masters:instances[inst]=master
    all_phy=[n for n,m in instances.items() if re.fullmatch(NAMES,m)]
    phy=json.loads((case/'assumed_phy_pg_access.json').read_text())['instances']
    interp.eval('namespace eval ord {}');interp.createcommand('ord::get_db',lambda:'db')
    interp.createcommand('db',lambda method:'lib' if method=='getLibs' else fail(method))
    handles={f'm{k}':m for k,m in enumerate(masters)}
    reverse={n:h for h,n in handles.items()}
    interp.createcommand('lib',lambda method,*args:tuple(handles) if method=='getMasters' else reverse.get(args[0],'NULL') if method=='findMaster' else fail(method))
    for handle,name in handles.items():
        def mst(method,*args,name=name,handle=handle):
            if method=='getName':return name
            if method=='getHeight':return heights[name]
            if method=='isBlock':return '1' if masters[name] else '0'
            if method=='findMTerm':return 'term_'+handle if layers[name] else 'NULL'
            raise ValueError(method)
        interp.createcommand(handle,mst)
        interp.createcommand('term_'+handle,lambda method,h=handle:('mp_'+h,) if method=='getMPins' else fail(method))
        interp.createcommand('mp_'+handle,lambda method,h=handle,n=name:tuple('box_'+h+'_'+l for l in layers[n]) if method=='getGeometry' else fail(method))
        for layer in layers[name]:
            interp.createcommand('box_'+handle+'_'+layer,lambda method,l=layer:'layer_'+l if method=='getTechLayer' else fail(method))
    for layer in set(l for ls in layers.values() for l in ls):
        interp.createcommand('layer_'+layer,lambda method,l=layer:l if method=='getName' else fail(method))
    grids=[]
    def define(*args):
        args=list(args);name=args[args.index('-name')+1];selected=[]
        if '-cells' in args:
            cells=interp.splitlist(args[args.index('-cells')+1]);selected=[i for i,m in instances.items() if m in cells]
        elif '-instances' in args:
            patterns=interp.splitlist(args[args.index('-instances')+1])
            if any(not p or p in ['^','$','^$'] for p in patterns):raise ValueError('empty/broad selector')
            selected=[i for i in instances if any(int(interp.call('regexp','--',p,i)) for p in patterns)]
        grids.append(dict(grid=name,selected_count=len(selected),phy=sorted(set(selected)&set(phy))))
        return ''
    interp.createcommand('define_pdn_grid',define)
    for name in ['add_global_connection','global_connect','set_voltage_domain','add_pdn_stripe','add_pdn_connect']:
        interp.createcommand(name,lambda *args:'')
    interp.createcommand('source',lambda *args:'')
    interp.eval('namespace eval ot_hbm_pg {}')
    interp.createcommand('ot_hbm_pg::begin',lambda:'')
    interp.createcommand('puts',lambda *args:'')
    interp.createcommand('ot_assumed_phy_pg_grids',lambda:grids.append(dict(grid='NEW_DECLARED_PHY',selected_count=len(phy),phy=sorted(phy))) or '')
    text=(case/'pdn.tcl').read_text();interp.eval(text)
    old_owned=[n for g in grids if g['grid']!='NEW_DECLARED_PHY' for n in g['phy']]
    if old_owned:raise ValueError('PHY still claimed by old grid: '+repr(old_owned))
    return dict(status='TCL_SELECTION_TRACE_PASS',case=str(case),pdn_sha256=hashlib.sha256(text.encode()).hexdigest(),
      masters=len(masters),instances=len(instances),actual_phy_instances=sorted(all_phy),repaired_phy_instances=sorted(phy),preserved_phy_instances=sorted(set(all_phy)-set(phy)),old_grids_claiming_phy=old_owned,grids=grids)

def fail(method):raise ValueError(method)
if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('case',type=Path);a=ap.parse_args();print(json.dumps(trace(a.case),indent=2))
