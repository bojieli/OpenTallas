#!/usr/bin/env python3
import ast,json,re,sys,hashlib,subprocess,shutil
from pathlib import Path
HERE=Path(__file__).resolve().parent
def apply(k,w):
 k,w=Path(k),Path(w)
 helper=(HERE/'parameter_helper_source.py').read_text()
 tree=ast.parse(helper)
 names={'_mask','_integer','_close','_defaults','fixed_child_sources'}
 ns=dict(ast=ast,json=json,re=re,Path=Path)
 for node in tree.body:
  if isinstance(node,ast.FunctionDef) and node.name in names:
   exec(compile(ast.Module(body=[node],type_ignores=[]),str(HERE/'parameter_helper_source.py'),'exec'),ns)
 cfg=(k/'config.mk').read_text()
 oldline=re.search(r'^export VERILOG_FILES = (.+)$',cfg,re.M).group(0)
 sources=[x.replace('/work/','') for x in oldline.split(' = ',1)[1].split()]
 views={}
 specs={}
 for name,ref in [('ot_s81_cfg7_seq','s81coll_cfg7_seq_pr'),('ot_s81_cfg7_seq_bfp','s81coll_cfg7_seq_bfp_pr')]:
  base='physical/ref_tile/'+ref
  raw=subprocess.check_output(['git','-C',str(w),'show','HEAD:'+base+'/spec.json'])
  sp=k/base/'spec.json';sp.parent.mkdir(parents=True,exist_ok=True)
  selected=json.loads(raw)
  if name=='ot_s81_cfg7_seq':
   native=(k/'rtl/ot_s81_cfg7_seq.sv').read_text()
   assert 'parameter integer CW = 3 * NSEG + 1' in native
   assert 'parameter integer AW = $clog2(CW << PHW)' in native
   derived_cw=3*8+1;derived_aw=((derived_cw<<10)-1).bit_length()
   assert derived_cw==25 and derived_aw==15
   selected['params']['AW']=derived_aw
  sp.write_text(json.dumps(selected,indent=2))
  views[base+'/views/'+name+'.lef']={'master':name}
  specs[name]=dict(spec_sha256=hashlib.sha256(raw).hexdigest(),params=json.loads(raw)['params'],qualification='CFG7 SIGNED actual cs7; BFP provisional legacy view, NOT SIGNED')
 out=k/'rtl_fixed_parameters';out.mkdir(exist_ok=True)
 retained,replaced=ns['fixed_child_sources'](dict(top='s81p_col_h10_r0_p4__t1',sources=sources),k,views,out)
 # The actual PINREG=1 binding is semantically significant: reject its wrong-phase mutant.
 text=(k/'rtl/s81p_col_h10_r0_p4__t1_bound.sv').read_text()
 bad=text.replace('.PINREG(1)) u_u_r0_u_s5','.PINREG(0)) u_u_r0_u_s5')
 assert bad!=text
 tmp=k/'parameter_negative';(tmp/'rtl').mkdir(parents=True,exist_ok=True)
 for source in sources:
  dest=tmp/source;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(k/source,dest)
 (tmp/'rtl/s81p_col_h10_r0_p4__t1_bound.sv').write_text(bad)
 for key in views:
  sp=Path(key).parent.parent/'spec.json';dest=tmp/sp;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(k/sp,dest)
 try:ns['fixed_child_sources'](dict(top='s81p_col_h10_r0_p4__t1',sources=sources),tmp,views,tmp/'out')
 except ValueError as e:
  assert 'actual parameters' in str(e) and 'differ' in str(e)
  negative=str(e)
 else:raise RuntimeError('wrong PINREG mutant was accepted')
 def mount(x):
  p=Path(x)
  return '/work/'+str(p.relative_to(k) if p.is_absolute() else p)
 newline='export VERILOG_FILES = '+' '.join(mount(x) for x in retained)
 (k/'config.before_fixed_params.mk').write_text(cfg)
 (k/'config.mk').write_text(cfg.replace(oldline,newline))
 receipt=dict(rule='existing exact fixed-child parameter validation; no RTL/port/cycle/clock/plan change',source_helper_sha256=hashlib.sha256(helper.encode()).hexdigest(),source_plan='5489dced4e37cde0f775b93b12840348cf67aea91f1caae0cd07697b9017e313',views=specs,replaced=replaced,negative_PINREG0=negative,generated_files={str(x.relative_to(k)):hashlib.sha256(x.read_bytes()).hexdigest() for x in out.glob('*')})
 (k/'fixed_parameter_binding.json').write_text(json.dumps(receipt,indent=2))
 print(json.dumps(receipt,indent=2))
if __name__=='__main__':apply(*sys.argv[1:])
