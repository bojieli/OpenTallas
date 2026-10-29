import hashlib,json,pathlib,shutil,subprocess,sys,types,re
W=pathlib.Path('/srv/opentallas-scratch2/claude/wt/codex-s81-frame-sub-1028')
R=pathlib.Path('/srv/opentallas-scratch2/claude/codex-tok-s81-1028/qx_alias_native');R.mkdir(exist_ok=True)
sys.path[:0]=[str(W/'tools/die_plan'),str(W/'tools/s81_dv')]
import bind_elab as E
import bind as B
import frame_qx_identity as Q
import frame_cfg_identity as C
p=pathlib.Path('/srv/opentallas-scratch2/claude/codex-tok-s81-1028/fs_work/col_h10_x/col_h10_l4_lp_asb_x.json')
js=json.loads(p.read_text());f=E.flatten(js,'col_h10_l4_lp_asb_x')
defaults={}
for c in f.cells:
 c.path='u_f_0L01.'+c.path
 defaults[(c.ytype,c.module)]={k:E._pval(v)[0]for k,v in js['modules'].get(c.ytype,{}).get('parameter_default_values',{}).items()}
oldempty=[c.path for c in f.cells if c.module==Q.OLD and c.params.get('INSTANCE',defaults[(c.ytype,c.module)].get('INSTANCE'))=='""']
assert len(oldempty)==12
rules=[dict(module=Q.OLD,param='INSTANCE')]
audit=B.instance_path_params(f.cells,defaults,rules)
assert len(audit)==12
ab=json.loads((W/'physical/die_plan/s81/bind/asbuilt_b178_coll_s13func.json').read_text())
ab['substitute_inst']=[r for r in ab['substitute_inst']if any(re.fullmatch(r['inst'],c.path)for c in f.cells)]
b=object.__new__(B.Binder);b.ab=ab;b.F=f;b.param_defaults=defaults;b.errors=[];b.extra_lib=[];b.variants=[]
b.substitute_inst(str(W));assert not b.errors,b.errors
actual=[c for c in f.cells if c.module==Q.NEW];assert len(actual)==12
for c in actual:assert json.loads(c.params['INSTANCE'])==c.path and c.params['INSTANCE']!='""'
report={'instance_path_params':audit}
(R/'actual_frame_selectors.json').write_text(json.dumps(dict(old_empty=oldempty,assigned=audit,post_substitution=[dict(inst=c.path,module=c.module,INSTANCE=c.params['INSTANCE'],CGR=c.params.get('CGR'),GO_BOUNDARY=b.param_defaults[(c.ytype,c.module)].get('GO_BOUNDARY'))for c in actual]),indent=1)+'\n')
images=pathlib.Path('/srv/opentallas-scratch2/claude/tok17-gb/slice/vec/u_f_0L01')
for p in images.glob('u_f_0L01_e*.viamap.hex'):shutil.copyfile(p,R/p.name)
parent=C.bind_elab.module_body(W/'rtl/dsrom_sys/s81_dv/frame_lp/col_h10_l4_lp.sv','col_h10_l4_lp')
band=C.bind_elab.module_body(W/'rtl/dsrom_sys/s81_dv/frame_lp/plan/col_h10_l4_lp_plan_kit.sv','col_h10_l4_lp_r0')
try:Q.emit_bound_aliases(parent,band,'u_f_0L01','u_r0',{},R)
except ValueError as e:assert 'missing actual bound'in str(e)
else:raise AssertionError('old empty selector audit admitted')
rows=Q.emit_bound_aliases(parent,band,'u_f_0L01','u_r0',report,R)
assert len(rows)==16
wrong=next(x for x in rows if x['image_sha256']!=rows[0]['image_sha256'])
tb=['`timescale 1ns/1ps','module tb;','reg clk=0;always #0.4165 clk=~clk;','reg [11:0] addr=0;integer mut=0;','wire[273:0]r[0:15],c[0:15],wrong;']
for i,row in enumerate(rows):
 for kind,key in (('r','image'),('c','alias')):
  name=row[key].removesuffix('.viamap.hex');tb.append(f'ot_rom_4096x274_m8 #(.INSTANCE("{name}")) {kind}{i}(clk,1\'b1,addr,{kind}[{i}]);')
name=wrong['alias'].removesuffix('.viamap.hex');tb.append(f'ot_rom_4096x274_m8 #(.INSTANCE("{name}")) wrongleaf(clk,1\'b1,addr,wrong);')
tb+=['initial begin void\'($value$plusargs("MUT=%d",mut));','for(integer n=0;n<4096;n=n+1)begin @(negedge clk);addr=12\'(n);@(posedge clk);#0.001;','for(integer k=0;k<16;k=k+1)if((mut && k==0 ? wrong:c[k])!==r[k])$fatal(1,"QX_BOUND_ALIAS_DIFF addr%0d bank%0d mutant%0d",n,k,mut);','end $display("QX_BOUND_ALIAS_PASS 65536words 274bits 833ps");$finish;end endmodule']
(R/'tb.sv').write_text('\n'.join(tb)+'\n')
with(R/'build.log').open('w')as log:subprocess.run(['verilator','--binary','--timing','-Wno-fatal','--top-module','tb','-j','2','--Mdir',str(R/'obj'),str(W/'physical/asap7_memory_macros_v2/ot_rom_4096x274_m8/ot_rom_4096x274_m8.v'),str(R/'tb.sv')],stdout=log,stderr=subprocess.STDOUT,check=True)
for m in (0,1):
 with(R/f'run{m}.log').open('w')as log:result=subprocess.run([str(R/'obj/Vtb'),f'+MUT={m}',f'+OT_ROM_DIR={R}'],stdout=log,stderr=subprocess.STDOUT)
 text=(R/f'run{m}.log').read_text();assert(result.returncode==0 and'QX_BOUND_ALIAS_PASS'in text)if m==0 else(result.returncode!=0 and'QX_BOUND_ALIAS_DIFF'in text),text
rec=dict(scope='Actual one-frame source flatten through real binder selector assignment and _gb substitution, plus first-band native weight ROM runtime; no frame arithmetic/provider/current die qualification',actual_frame='u_f_0L01',source_commit=subprocess.check_output(['git','-C',str(W),'rev-parse','HEAD'],text=True).strip(),actual_qx=12,initial_empty_selectors=12,unique_post_substitution_selectors=12,first_band_aliases=16,native_words=65536,bits=274,clock_ps=833,wrong_leaf_mutant='CAUGHT',empty_audit_control='CAUGHT',full_frame_qualified=False)
(R/'check.json').write_text(json.dumps(rec,indent=1)+'\n');print('QX_BOUND_ALIAS_NATIVE PASS 65536x274 actual12QX selectors,16aliases;wrongleaf+emptyaudit CAUGHT',flush=True)
