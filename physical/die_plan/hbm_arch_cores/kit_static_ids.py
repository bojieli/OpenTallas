#!/usr/bin/env python3
"""Convert only the selected TKM common/terminal kit to owner option-B static ID pins.
No arithmetic/control RTL changes. All live data/control face registers are retained.
The caller must update the plan's module/pin/typed-parent-strap declaration and prove
constant-ID equivalence after the old input-register warmup before routing.
"""
import argparse, hashlib, importlib.util, json, re, shutil, sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
sys.path.insert(0,str(REPO/'tools/die_plan'))
import straps as STR
spec=importlib.util.spec_from_file_location('face_shell',HERE/'face_shell.py')
FS=importlib.util.module_from_spec(spec);spec.loader.exec_module(FS)
def save(p,j):p.write_text(json.dumps(j,indent=1)+'\n')
def convert(src,out):
 src,out=Path(src).resolve(),Path(out).resolve()
 if out.exists():raise ValueError(f'output already exists: {out}')
 f=json.load(open(src/'freeze.json'));s=json.load(open(src/'face_shell.json'))
 if f['rtl_top']!='ot_hgi_coll_tkm_tp192_tile_core':raise ValueError('only selected TKM tile RTL master supported')
 if s['widths'].get('tile_tid')!=6 or s['dirs'].get('tile_tid')!='input':raise ValueError('expected one six-bit input tile_tid')
 if s.get('params') or s.get('mutant'):raise ValueError('unexpected parameters/mutant in source kit')
 old=f['module'];new=old+'__strap';core=new+'__fcore';port='strap_tile_tid'
 shutil.copytree(src,out,ignore=shutil.ignore_patterns('run','views','signoff*','lec*','face_shell_work','*.log','FAIL_*'))
 # The engine files are unchanged. Rename only the outer wrapper API and its connection RHS.
 raw=out/'rtl'/s['core_def_file'];t=raw.read_text().replace(old,new)
 t=re.sub(r'(?<!\.)\btile_tid\b',port,t)
 assert '.tile_tid(strap_tile_tid)' in t
 newraw=out/'rtl'/raw.name.replace(old,new);newraw.write_text(t);raw.unlink()
 widths={port if k=='tile_tid' else k:v for k,v in s['widths'].items()}
 dirs={port if k=='tile_tid' else k:v for k,v in s['dirs'].items()}
 keep={port if k=='tile_tid' else k:v for k,v in s['keep'].items()}
 passthrough=set(s['passthrough'])|{port}
 scalars=set(s['scalars']);scalars.discard('tile_tid')
 oldshell=out/'rtl'/f'{old}__fshell.sv';newshell=out/'rtl'/f'{new}__fshell.sv'
 newshell.write_text(FS.emit_shell(new,core,{},widths,dirs,keep,passthrough,s['clock'],scalars=scalars));oldshell.unlink()
 assert 'u_bin_strap_tile_tid' not in newshell.read_text()
 cfg=(out/'config.mk').read_text().replace(old,new)
 (out/'config.mk').write_text(cfg)
 for name in ['io.tcl','face_flops.tcl','face_flops_release.tcl','face_keep.tcl','face_keep_release.tcl']:
  p=out/name
  if p.exists():p.write_text(re.sub(r'\btile_tid\b',port,p.read_text()))
 # Static ID pins have no register to place; exclude only this declared port from the face-flop placement hook.
 p=out/'face_flops.tcl';t=p.read_text()
 t,n=re.subn(r'(?m)^(set ff_skip_re \{)(.*)(\}\s*)$',lambda m:m[1]+'(?:'+m[2]+')|^strap_tile_tid$'+m[3],t)
 if n!=1:raise ValueError('face placement skip anchor not unique')
 p.write_text(t)
 pins=json.load(open(out/'pins.json'))
 for p in pins:
  if p['bus']=='tile_tid':p['bus']=port
 assert sum(p['bus']==port for p in pins)==6
 save(out/'pins.json',pins)
 # Current shared gate support; no exemptions on undeclared ports.
 for name in ['straps.py','sdc_lint.py','face_guard.py','signoff.py','lec.py']:
  shutil.copyfile(REPO/'tools/die_plan'/name,out/name)
 shutil.copyfile(HERE/'face_guard_core.py',out/'face_guard_core.py')
 STR.write_kit(out,[port],source='METHODOLOGY 1.8 owner B; selected TKM tile_tid6 alias only')
 ctx=json.load(open(out/'sdc_lint.json'))
 ctx['inputs']=[port if x=='tile_tid' else x for x in ctx['inputs']];ctx['straps']=[port]
 for k in ['io_floor_ps','port_latency_ps']:
  ctx[k]={port if x=='tile_tid' else x:v for x,v in ctx.get(k,{}).items()}
 save(out/'sdc_lint.json',ctx)
 p=out/'constraint.sdc';p.write_text(p.read_text()+f'\n# Declared parent ID constant, owner option B\nset_false_path -from [get_ports {{{port}}}]\n')
 sin=[k for k in widths if dirs[k]=='input' and k not in passthrough]
 sout=[k for k in widths if dirs[k]=='output' and k not in passthrough]
 s.update(module=new,core=core,core_def_file=newraw.name,passthrough=sorted(passthrough),widths=widths,dirs=dirs,keep=keep,
          scalars=sorted(scalars),in_buses=len(sin),out_buses=len(sout),in_bits=sum(keep[k] for k in sin),out_bits=sum(widths[k] for k in sout),
          face_flops=sum(keep[k] for k in sin)+sum(widths[k] for k in sout),files=[newshell.name,'ot_hbm_face_reg.sv'],
          unread_kept=[x for x in s['unread_kept'] if not x.startswith('tile_tid[')],static_id_ports=[port])
 save(out/'face_shell.json',s)
 f['face_shell'] = dict(core=core, in_cycles=s['latency']['in_cycles'], out_cycles=s['latency']['out_cycles'],
        face_flops=s['face_flops'], dropped=len(s['dropped']), unread_kept=len(s['unread_kept']),
        const_out_bits=s['const_out_bits'], dup_out_bits=s['dup_out_bits'], plan_pins=f['pins'], static_id_ports=[port])
 f['sdc_lint'] = ctx
 oldhash=f.pop('kit_hash')
 f.update(module=new,design=new,view=new,pins_file=str(out/'pins.json'),pins_sha256=hashlib.sha256((out/'pins.json').read_bytes()).hexdigest(),
          static_id_conversion=dict(source_kit_hash=oldhash,source_module=old,port=port,width=6,removed_id_face_ff=6,data_cycle_delta=0,
           rule='quasi-static parent ID, no pin FF, declared false path; exactness after old ID warmup required'),
          plan_delta_required='module/pin table plus typed parent straps[].port=strap_tile_tid width6 valueID; actual tie cells at parent')
 f['kit_hash']=hashlib.sha256(json.dumps(f,sort_keys=True).encode()).hexdigest()[:16]
 save(out/'freeze.json',f)
 import sdc_lint
 errors=sdc_lint.lint((out/'constraint.sdc').read_text(),**ctx)
 if errors:raise ValueError(errors)
 return dict(kit=str(out),module=new,kit_hash=f['kit_hash'],pins=f['pins'],face_flops=s['face_flops'],strap=port,data_cycle_delta=0)
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('source');a.add_argument('output');v=a.parse_args();print(json.dumps(convert(v.source,v.output)))
