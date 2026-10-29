#!/usr/bin/env python3
"""Build selected TKM no-ID kit from the reviewed chain3 pin/clock profile.
Requires the canonical source emitted by build_split_tops' chain profile. It
preserves every live pin, native control relay and face stage; no P&R is run.
"""
import argparse,hashlib,importlib.util,json,re,shutil,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
R=HERE.parents[2]
spec=importlib.util.spec_from_file_location('face_shell',HERE/'face_shell.py');FS=importlib.util.module_from_spec(spec);spec.loader.exec_module(FS)
def save(p,j):p.write_text(json.dumps(j,indent=1)+'\n')
def convert(src,out,canonical):
 src,out,canonical=map(lambda x:Path(x).resolve(),(src,out,canonical));assert not out.exists()
 f=json.load(open(src/'freeze.json'));s=json.load(open(src/'face_shell.json'));assert f['rtl_top']=='ot_hgi_coll_tkm_tp192_tile_core'
 assert s['widths']['tile_tid']==6 and s['dirs']['tile_tid']=='input'
 cs=canonical.read_text();assert 'tile_tid' not in cs and 'always @(posedge tile_clk) tile_clr_o <= tile_clr;' in cs and 'assign tile_conv_o = tile_conv;' in cs
 old=f['module'];new=old+'__strap';core=new+'__fcore'
 shutil.copytree(src,out,ignore=shutil.ignore_patterns('run','views','lec','signoff','signoff_*','*.log','FAIL_*'))  # result dirs only: 'signoff*' also dropped the kit signoff.py (KITS-13 10-29)
 raw=out/'rtl'/s['core_def_file'];t=raw.read_text().replace(old,new)
 t,n=re.subn(r'(?m)^    input wire \[5:0\] tile_tid,?\n','',t);assert n==1
 t,n=re.subn(r'(?m)^        \.tile_tid\(tile_tid\),?\n','',t);assert n==1
 nr=raw.with_name(raw.name.replace(old,new));nr.write_text(t);raw.unlink();shutil.copyfile(canonical,out/'rtl'/canonical.name)
 widths={k:v for k,v in s['widths'].items() if k!='tile_tid'};dirs={k:v for k,v in s['dirs'].items() if k!='tile_tid'};keep={k:v for k,v in s['keep'].items() if k!='tile_tid'}
 ns=out/'rtl'/f'{new}__fshell.sv';ns.write_text(FS.emit_shell(new,core,{},widths,dirs,keep,set(s['passthrough']),s['clock'],scalars=set(s['scalars'])));(out/'rtl'/f'{old}__fshell.sv').unlink()
 q=out/'config.mk';q.write_text(q.read_text().replace(old,new))
 q=out/'rtl/portlist.txt'
 if q.exists():q.write_text(''.join(l for l in q.read_text().splitlines(True) if not l.rstrip().endswith(' tile_tid')))
 q=out/'io.tcl';q.write_text(''.join(l for l in q.read_text().splitlines(True) if 'tile_tid[' not in l))
 pins=json.load(open(out/'pins.json'));pins=[p for p in pins if p['bus']!='tile_tid'];assert len(pins)==f['pins']-6;save(out/'pins.json',pins)
 q=out/'sdc_lint.json';ctx=json.load(open(q));ctx['inputs'].remove('tile_tid')
 for k in ['io_floor_ps','port_latency_ps']:ctx.get(k,{}).pop('tile_tid',None)
 save(q,ctx)
 for n in ['straps.py','sdc_lint.py','face_guard.py','signoff.py','lec.py','selrange_gate.py','vclk_corner.tcl','postcts_gate.tcl','pinreg_measure.tcl']:shutil.copyfile(R/'tools/die_plan'/n,out/n)
 subprocess.run([sys.executable,'-I',str(R/'tools/die_plan/signoff.py'),'bundle',str(out)],check=True)
 sin=[k for k in widths if dirs[k]=='input' and k not in s['passthrough']];sout=[k for k in widths if dirs[k]=='output' and k not in s['passthrough']]
 s.update(module=new,core=core,core_def_file=nr.name,widths=widths,dirs=dirs,keep=keep,in_buses=len(sin),out_buses=len(sout),in_bits=sum(keep[k] for k in sin),out_bits=sum(widths[k] for k in sout),face_flops=sum(keep[k] for k in sin)+sum(widths[k] for k in sout),unread_kept=[],files=[ns.name,'ot_hbm_face_reg.sv']);save(out/'face_shell.json',s)
 oldhash=f.pop('kit_hash');f.update(module=new,design=new,view=new,pins=len(pins),pins_file=str(out/'pins.json'),pins_sha256=hashlib.sha256((out/'pins.json').read_bytes()).hexdigest(),sdc_lint=ctx,noid_profile={'source_kit_hash':oldhash,'removed_port':'tile_tid','removed_pin_bits':6,'removed_face_ff':6,'no_straps':True,'data_cycle_delta':0,'native_clr_core_cycles':1,'native_conv_core_cycles':0,'source_rule':'owner approved8b9ec6b43c plus existing chain3 native control relays'},rtl_overrides={canonical.name:{'path':str(canonical),'sha256':hashlib.sha256(canonical.read_bytes()).hexdigest()}},plan_delta_required='same __strap module names as selected no-ID plan, zero ID pins/straps; actual kit hash and clock cohort must bind')
 f['face_shell'].update(core=core,face_flops=s['face_flops'],unread_kept=0,plan_pins=len(pins));f['runtime_bundle']={n:hashlib.sha256((out/n).read_bytes()).hexdigest() for n in ['signoff.py','sdc_lint.py','face_guard.py','io_hold_qualification.py','pair_skew.tcl','clock_family.tcl','lec.py','vclk_corner.tcl','postcts_gate.tcl','pinreg_measure.tcl']};f['kit_hash']=hashlib.sha256(json.dumps(f,sort_keys=True).encode()).hexdigest()[:16];save(out/'freeze.json',f)
 sys.path.insert(0,str(R/'tools/die_plan'));import sdc_lint
 assert not sdc_lint.lint((out/'constraint.sdc').read_text(),**ctx)
 print(json.dumps(dict(kit=str(out),module=new,hash=f['kit_hash'],pins=len(pins),face_ff=s['face_flops'],clock=f['clocks'],data_cycle_delta=0)))
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('source');a.add_argument('output');a.add_argument('canonical');x=a.parse_args();convert(x.source,x.output,x.canonical)
