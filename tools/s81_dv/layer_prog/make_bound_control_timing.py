#!/usr/bin/env python3
"""Publish measured local control stages plus exact pass-through wrapper proofs."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools/die_plan'))
import bind_elab as E


def pins(body,child,inst):
    m=re.search(r'\b'+re.escape(child)+r'\s*(?:#\(.*?\)\s*)?'+re.escape(inst)+r'\s*\((.*?)\);',body,re.S)
    if not m:raise ValueError('actual wrapper child absent '+child+'.'+inst)
    return {k:re.sub(r'\s+','',v) for k,v in re.findall(r'\.(\w+)\(([^()]*)\)',m[1])}


def build(root,run):
    source=['rtl/lib/ot_rst_relay.sv']+[f'rtl/dsrom_sys/s81_dv/slice/{n}.sv' for n in ('ot_s81sl_rstop','ot_s81sl_rstopt_xo','ot_s81sl_xrt')]
    models={};witness={}
    for ring in ('ot_s81sl_rstop','ot_s81sl_rstopt_xo'):
        for hb in (0,1):
            stem=f'{ring}_{hb}'
            text=(run/f'run_{stem}.log').read_text();bad=(run/f'age_mut_{stem}.log').read_text()
            if not re.search(r'BOUND_LOCAL hb='+str(hb)+r' jobs=384 checks=8448 age=7 errors=0',text) or '\nPASS\n' not in text:
                raise ValueError('local control measurement failed/missing: '+stem)
            if '\nFAIL\n' not in bad:raise ValueError('local wrong-age control not caught: '+stem)
            witness[stem]=dict(transactions=384,whole_word_checks=8448,errors=0,wrong_age_caught=True)
    for name,ring in [('ot_s81sl_xg','ot_s81sl_rstop'),('ot_s81sl_xgt_xo','ot_s81sl_rstopt_xo')]:
        path=f'physical/die_plan/s81/bind/source_modules/portfix178/{name}.sv'
        source.append(path);con=pins(E.module_body(root/path,name),ring,'u_r')
        for port in ('clk','rst_n','sid','ri_w','ri_e','ro_e','ro_w','vi','vo','dl_ev','dl_e','dl_wv','dl_w','dl_vv','dl_vb','ci_dir'):
            if con.get(port)!=port:raise ValueError('wrapper control pin changed '+name+'.'+port)
        if con.get('ci_b')!="{28'd0,ci_b}":raise ValueError('wrapper CI prefix changed '+name)
        models[name]=dict(source_path=path,measured_child=ring,wire_wrapper_proof='exact direct control pin expressions',
            edges=dict(vi_to_delivery=2,ri_e_to_delivery=2,ri_w_to_delivery=2,
                       ri_e_to_line=2,ri_w_to_line=2,ci_to_line=2))
    path='rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xrt.sv'
    for name,hb in [('ot_s81sl_xrt1',0),('ot_s81sl_xrt3',1)]:
        body=E.module_body(root/path,name);con=pins(body,'ot_s81sl_xrt','u')
        for port in ('clk','rst_n','sid','dl_ev','dl_e','dl_wv','dl_w','dl_vv','dl_vb','ci_dir','ci_b','c_v','c_d','sw_v','sw_a','sw_m','sw_d','cfg_v','cfg_d','is_v','is_d','x_go'):
            if con.get(port)!=port:raise ValueError('wrapper control pin changed '+name+'.'+port)
        if not re.search(r'\.HB\('+str(hb)+r'\)',body):raise ValueError('wrapper HB changed '+name)
        models[name]=dict(source_path=path,measured_child='ot_s81sl_xrt',measured_hb=hb,
            wire_wrapper_proof='exact direct control pin expressions',edges=dict(dl_ctl_to_ci=3,dl_ctl_to_command=3))
    define_scope=sorted({name for p in source for name in re.findall(r'^\s*`(?:ifdef|ifndef|elsif)\s+(\w+)',(root/p).read_text(),re.M)})
    for entry in models.values():entry.update(defines=[],define_scope=define_scope)
    return dict(schema='opentallas.s81.bound_control_local.v1',verdict='PASS',
        source_sha256={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in source},
        masters=models,witness=witness,edge_convention='source pin event after posedge; receiver samples next edge',
        scope='atomic ring/XRT stages only; inter-partition transport must come from strict current BoundDie routes')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=ROOT)
    p.add_argument('--run',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.out.exists():raise ValueError('preserve prior receipt; use a fresh output')
    j=build(a.root,a.run);a.out.write_text(json.dumps(j,indent=1)+'\n');print('BOUND_CONTROL_LOCAL PASS',len(j['masters']),'exact masters')
if __name__=='__main__':main()
