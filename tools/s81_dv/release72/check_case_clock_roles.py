#!/usr/bin/env python3
"""Checker-only replay of failed case clock roles. No GEN, GRT or STA outputs."""
import argparse,hashlib,json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tools/s81_dv')]
import die_port_bind as D
from clock_roles import contract_clock_nets,whole_spare_frame_clock_outputs,validate_spare_frame_source_guard
p=argparse.ArgumentParser();p.add_argument('--bind-dir',type=Path,required=True);p.add_argument('--table',type=Path,required=True);p.add_argument('--source-root',type=Path,required=True);p.add_argument('--git-dir',required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
t=json.load(open(a.table));pb=json.load(open(a.bind_dir/'port_bind.json'));pads=json.load(open(a.bind_dir/'pads.json'))
assert pb['verdict']=='PASS'
nets,ti,to,insts=D.parse_die(a.bind_dir/'die.v','dv_die');insts=[x for x in insts if x[0]!='__assign__']
defs=pb.get('defines',{});defs=defs if isinstance(defs,dict) else {x:'1' for x in defs}
# Exact selected paths recorded by strict bind, not a newly chosen RTL census.
idx={}
for module,row in pb['masters'].items():
 path=Path(row['rtl']);path=path if path.is_absolute() else a.source_root/path
 for m in D.parse_modules(D.preprocess(path.read_text(),dict(defs)),str(path)):
  if m.name==module:idx[module]=m
assert set(idx)==set(pb['masters'])
dirs={m:{n:row[0] for n,row in v.ports.items()}for m,v in idx.items()}
bits={name:{pn:D.expr_bits(expr,nets)for pn,expr in con.items()}for mst,name,pr,con in insts}
assert not any(v is None for row in bits.values()for v in row.values())
mapping={m.get('module'):k for k,m in t['masters'].items()if m.get('module')}
known={n for n in set(ti)|set(to)if n.startswith('ck_')}
for mst,name,pr,con in insts:
 if mst.startswith('dsfd_dvrlyh_')or mst.startswith('dsfd_dvrly_'):cps=['ck','ck_o']
 elif mst.startswith('dsfd_dvland_'):cps=['ck_f','ck']
 elif mst.endswith('_ASAP7_75t_R')and name.startswith('fwd_'):cps=['A','Y','CLK','GCLK']
 else:
  tm=t['masters'].get(mapping.get(mst,''),{});cps=[tm.get('clk')]+[q['port']for q in tm.get('clk_peer',[])]
 for cp in cps:
  known|={n for n,b in bits[name].get(cp,[])if n not in {'CONST','Z','UNDECL'}}
def load_ref(ref,path):
 r=subprocess.run(['git','--git-dir='+a.git_dir,'show',ref+':'+path],capture_output=True)
 return None if r.returncode else r.stdout.decode()
guard=t.get('selected72_spare_faces_g8',{})
validate_spare_frame_source_guard(guard,{m:v.path for m,v in idx.items()},insts,a.bind_dir/'die.v',pb,load_ref)
unused=whole_spare_frame_clock_outputs(insts,bits,t['masters'],mapping,dirs,t.get('rtl_widths',{}),pads,guard)
clocknets,inputs=contract_clock_nets(insts,bits,t['masters'],mapping,dirs,known,spare_frame_context=(t.get('rtl_widths',{}),pads,guard))
r={'status':'PASS','scope':'checker-only exact failed case; no GEN/GRT/STA','strict_die_sha256':pb['die_sha256'],'instances':len(insts),'clock_net_names':len(clocknets),'clock_input_ports':len(inputs),'whole_spare_outputs':sorted(unused),'selected_frame_sources':{m:hashlib.sha256(Path(idx[m].path).read_bytes()).hexdigest()for m in ('col_h9_l4_lp','col_h10_l4_lp')}}
a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
