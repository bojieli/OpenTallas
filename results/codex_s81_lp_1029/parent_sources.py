#!/usr/bin/env python3
"""Snapshot only the exact current strict-bound LP parent's selected RTL closure for synthesis."""
import argparse,json,sys,hashlib,re,shutil
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('bound',type=Path);p.add_argument('out',type=Path);a=p.parse_args()
s=a.source.resolve();b=a.bound.resolve();o=a.out.resolve();o.mkdir(parents=True,exist_ok=True)
sys.path[:0]=[str(s/'tools/s81_dv'),str(s/'tools/die_plan')]
from layer_prog.slice_source import manifest_selection
import bind_elab as E
name='s81p_dsdv_slice_lepw_mus_LP__t2';mf='physical/die_plan/s81/bind/asbuilt_b178_coll_s13pfunc.json'
sel=manifest_selection(s,mf);ab=sel[1]
files=[str(s/f) for f in ab['files']]+(b/'bind.f').read_text().splitlines();pr=list(sel[3])+(b/'bind.f').read_text().splitlines()
idx=E.module_index([],files,s);fs,miss=E.closure([name],idx,pr)
if miss:raise SystemExit('Missing selected modules: '+repr(miss))
chosen={n:E.pick(idx,n,pr)[0] for n in ('dsdv_mu_land','ot_s81sl_lep_mu_ab_tpr')}
# Selecting the whole source files retains all declarations/directives; no RTL transformations.
(o/'rtl').mkdir(exist_ok=True);staged=[];rows=[];macros={}
for j,f in enumerate(fs):
 q=Path(f);dst=o/'rtl'/('%03d_'%j+q.name);shutil.copyfile(q,dst);staged.append('/out/rtl/'+dst.name)
 rows.append(dict(path=str(q),snapshot=str(dst.relative_to(o)),sha256=hashlib.sha256(q.read_bytes()).hexdigest(),bytes=q.stat().st_size))
 for m in E.MOD_RE.finditer(E._strip(q.read_text())):
  n=m.group(1)
  if '/physical/asap7_memory_macros' in str(q):
   view=q.parent;lef=view/(n+'.lef');lib=view/(n+'_tt.lib')
   if not lef.is_file() or not lib.is_file():raise SystemExit('Physical macro view incomplete: '+n+' '+str(view))
   macros[n]=dict(source=str(q),lef=str(lef),liberty_tt=str(lib))
params={f'S_u_ln{i}_chb':1 for i in range(4)}
doc=dict(scope='Exact current strict-bound parent source, SYNTH census only; no physical/functional qualification',top=name,source_graph_commit='e4ad09a663275339e3078d0fd816aa662ca7acb0',manifest=mf,defines=ab.get('defines',[]),params=params,files=rows,macros=macros,selected_mu_land=chosen.get('dsdv_mu_land'),selected_lep=chosen.get('ot_s81sl_lep_mu_ab_tpr'),bound_provenance=json.loads((b/'provenance_bind.json').read_text()))
(o/'sources.json').write_text(json.dumps(doc,indent=1)+'\n');(o/'sources.f').write_text('\n'.join(staged)+'\n')
print(json.dumps(dict(top=name,files=len(fs),bytes=sum(r['bytes'] for r in rows),defines=doc['defines'],macros=macros,mu_land=doc['selected_mu_land'],lep=doc['selected_lep'])))
