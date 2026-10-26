#!/usr/bin/env python3
"""Harden the four missing production A2F masters; existing field/control views stand."""
import json,pathlib,sys,subprocess,hashlib
ROOT=pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
import die_port_bind as D
VM='rtl/dsrom_sys/s81_ph/vm/'
OUT='physical/s81_vm_a2f_parent_0310'
SPEC='tools/ref_tile/specs_s81vm_a2f_parent_0310'
def sites(l,layer):
 out=[]
 for k in range(int(l/.048)+2):
  x=round(.012+.048*k,3)
  if x<4.32 or x>l-4.32:continue
  if layer=='M5' and .18<=x%5.4<=.74:continue
  if not out or x-out[-1]>=.144-1e-6:out.append(x)
 return out

def main():
 for key in sys.argv[1:] or ['header','payload','fault','rsched']:
  assert json.load(open('/home/ubuntu/claude-takeover-20261007/COORDINATOR.lock'))['owner']=='codex'
  if key=='rsched':
   s=json.load(open(ROOT/'tools/ref_tile/specs_s81vm_l16/dsfd_vm_static_rsched_p_native_1015_l16.json'))
   s['top']='dsfd_vm_a2f_rsched_p';s['sources']=[VM+'dsfd_vm_a2f_rsched.sv'];s.pop('reroute_reason',None)
   s['params']={'REL':8}
  else:
   top={'header':'s81_a2_w0_header','payload':'s81_a2_w0_payload','fault':'s81_a2f_fault_join4'}[key]
   src='tools/s81_vm/'+('area_a2f.sv' if key=='fault' else 'area_a2_controlled.sv')
   faces={'header':dict(N=['i_v','i_row','i_tag'],S=['o_v','o_row','o_tag','o_epoch'],W=['ck','rst_n']),
    'payload':dict(N=['i_data'],S=['o_data'],W=['i_mask','ck','rst_n'],E=['o_mask','o_epoch']),
    'fault':dict(W=['ck','rst_n','i_fault'],E=['fault'])}[key]
   w,h={'header':(216,86.4),'payload':(1166.4,86.4),'fault':(21.6,21.6)}[key]
   s=dict(top=top,sources=[src],clock_port='ck',reset_ports=['rst_n'],outline=dict(w=w,h=h,exact=True),pins=faces,
    macros=[],route=dict(pd=.4,threads=8,peak_ram_gb=16,period_ps=770,hold_margin_ns=.03,
      cts_sink=dict(size=24,diameter_um=30,extra='-distance_between_buffers 15')),recipe=3,
    io_flop_at_pins=dict(cols=4,allow_none=True),inhold=True,outhold=True,keep_pin_regs=True,pin_reg_split=True,
    hold_pad=dict(cell='HB2xp67_ASAP7_75t_R',out_cell='HB1xp67_ASAP7_75t_R'),io_budget={'in':.55,'out':.55})
  s['name']=s['top']+'_native_0310_r1';s['kind']='tile'
  s['pin_regs']=dict(enable=False,reason='Actual production RTL already registers input data and outputs; wrapper stages change the proven static calendar. Preserve actual flops and audit native launch/capture.')
  s['structural_change']='First physical view of exact production A2F '+key+' master, already composed in parent 8849603a6. Independent root, unchanged full source width and fixed calendar. REL8 read release replaces REL10; no clock or SDC relaxation.'
  s['slot_change_request']=dict(contract='S81 VM A2F parent',version='0310',why='Missing production hard view; M4 W/E and M5 N/S pins within existing outline. Parent actual-pin rebind owed before adoption.')
  src=ROOT/s['sources'][0];mod=next(m for m in D.parse_modules(src.read_text(),str(src)) if m.name==s['top']);env=mod.env(s.get('params',{}));width={n:mod.width(n,env) for n in mod.ports}
  w,h=s['outline']['w'],s['outline']['h'];pins=[];tcl=[]
  for f,names in s['pins'].items():
   layer='M5' if f in 'NS' else 'M4';ss=sites(w if f in 'NS' else h,layer)
   bits=[(n,i) for n in names for i in range(width[n])];assert len(ss)>=len(bits),(key,f,len(ss),len(bits))
   # Centre the clock within its face to avoid the legacy corner entry.
   if any(n=='ck' for n,i in bits):
    b=[x for x in bits if x[0]!='ck'];b.insert(len(b)//2,('ck',0));bits=b
   for j,(n,i) in enumerate(bits):
    q=ss[int((j+.5)*len(ss)/len(bits))];x,y=(q,h if f=='N' else 0) if f in 'NS' else (w if f=='E' else 0,q)
    port=n if width[n]==1 else f'{n}[{i}]';sz='.024 .192' if layer=='M5' else '.192 .024'
    tcl.append(f'place_pin -pin_name {{{port}}} -layer {layer} -location {{{x} {y}}} -pin_size {{{sz}}} -force_to_die_boundary')
    pins.append(dict(port=port,face=f,layer=layer,x_um=x,y_um=y))
  assert len(pins)==sum(width.values())
  out=ROOT/OUT;out.mkdir(parents=True,exist_ok=True);pinfile=f'{OUT}/{s["top"]}.tcl';(ROOT/pinfile).write_text('\n'.join(tcl)+'\n');s['io_tcl']=pinfile
  (out/(s['top']+'.pins.json')).write_text(json.dumps(dict(master=s['top'],outline_um=[w,h],source=s['sources'][0],source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),pins=pins),indent=1)+'\n')
  deps=s['sources']+['tools/s81_vm/a2f_hardleaf_gate.py','tools/die_port_bind.py',VM+'dsfd_vm_static_rsched.sv',pinfile]
  s['job']=dict(owner='codex:S81 parent leaves',branch='claude/s81-vm-a2f-parent-0200',tag='p1',extra_paths=deps,
   purpose='Four missing A2F production masters, exact actual RTL and cycle oracle with observed output/tap mutant.',cycles_added=0,
   benches=[dict(name=key+'_'+kind,cmd=f'python3 tools/s81_vm/a2f_hardleaf_gate.py {key}'+(' --mutant' if kind=='mutant' else ''),expect='fail' if kind=='mutant' else 'pass',threads=1,peak_ram_gb=2,needs=['iverilog'],**({'fail_regex':f'LEAF FAIL {key}'} if kind=='mutant' else {'pass_regex':f'LEAF PASS {key}'})) for kind in ['gold','mutant']])
  d=ROOT/SPEC;d.mkdir(parents=True,exist_ok=True);p=d/(key+'.json');p.write_text(json.dumps(s,indent=1)+'\n')
  subprocess.run(['python3','tools/ref_tile/ref_tile.py','gen',str(p)],cwd=ROOT,check=True)
  print(key,s['name'],len(pins))
if __name__=='__main__':main()
