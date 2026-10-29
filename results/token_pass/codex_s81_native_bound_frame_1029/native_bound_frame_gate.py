import hashlib,json,pathlib,re,shutil,subprocess,sys
W=pathlib.Path('/srv/opentallas-scratch2/claude/wt/codex-s81-frame-sub-1028');R=pathlib.Path('/srv/opentallas-scratch2/claude/codex-tok-s81-1028/native_bound_frame');R.mkdir(exist_ok=True)
sys.path[:0]=[str(W/'tools/die_plan'),str(W/'tools/s81_dv'),str(W/'tools/s81_dv/tokfunc')]
import bind_elab as E
import bind as B
import gb_image_identity as G
import frame_cfg_identity as C
import frame_bound_images as I
import check_dense_xs_cap as CHECK
frame='u_f_0L01';top='col_h10_l4_lp_asb_x'
jpath=pathlib.Path('/srv/opentallas-scratch2/claude/codex-tok-s81-1028/fs_work/col_h10_x')/(top+'.json');js=json.loads(jpath.read_text());f=E.flatten(js,top);defaults={}
for c in f.cells:
 c.path=frame+'.'+c.path
 defaults[(c.ytype,c.module)]={k:E._pval(v)[0]for k,v in js['modules'].get(c.ytype,{}).get('parameter_default_values',{}).items()}
ab=json.loads((W/'physical/die_plan/s81/bind/asbuilt_b178_coll_s13pfunc.json').read_text());audit=B.instance_path_params(f.cells,defaults,ab['instance_path_params'])
ab['substitute_inst']=[r for r in ab['substitute_inst']if any(re.fullmatch(r['inst'],c.path)for c in f.cells)]
b=object.__new__(B.Binder);b.ab=ab;b.F=f;b.param_defaults=defaults;b.errors=[];b.extra_lib=[];b.variants=[];b.substitute_inst(str(W));assert not b.errors,b.errors
for c in f.cells:
 if c.module not in ('ot_v41_rom_elem_q_qxpq_w10_gb','ot_rom_4096x72_m8'):continue
 cn=c.path.removeprefix(frame+'.');target=js['modules'][top]['cells'][cn]
 if c.module=='ot_v41_rom_elem_q_qxpq_w10_gb':
  target['type']=c.module;target['connections'].pop('xs_sv',None);target['port_directions'].pop('xs_sv',None);target['parameters']['GO_BOUNDARY']=format(1,'032b')
 if c.module in ('ot_v41_rom_elem_q_qxpq_w10_gb','ot_rom_4096x72_m8'):
  assert json.loads(c.params['INSTANCE'])==c.path;target['parameters']['INSTANCE']=c.path
# Dormant BF image selectors follow the exact canonical parent calls; no global BF manifest adoption.
parent=C.bind_elab.module_body(W/'rtl/dsrom_sys/s81_dv/frame_lp/col_h10_l4_lp.sv','col_h10_l4_lp');refs={(c['module'],c['name']):c for c in G.calls(parent)}
for c in f.cells:
 if c.module in ('dsfd_bf_col','dsfd_bf_front_roots'):
  ref=refs[(c.module,c.path.rsplit('.',1)[1])];suffix=re.fullmatch(r'\{\s*INSTANCE\s*,\s*"([A-Za-z0-9_]+)"\s*\}',ref['params']['INSTANCE'][2])[1]
  js['modules'][top]['cells'][c.path.removeprefix(frame+'.')]['parameters']['INSTANCE']=frame+suffix
(R/'frame.selected.json').write_text(json.dumps(js))
(R/'write.ys').write_text(f'read_json {R}/frame.selected.json\nwrite_verilog -noattr -norename {R}/frame.selected.sv\n')
with(R/'yosys.log').open('w')as log:subprocess.run(['yosys','-Q','-T','-s',str(R/'write.ys')],stdout=log,stderr=subprocess.STDOUT,check=True)
tb=(W/'tools/s81_dv/tokfunc/tb_dense_xs_cap_gb.sv').read_text().replace('always #0.5 clk','always #0.4165 clk').replace('col_h10_l4_lp_asb_x #(.INSTANCE(`GB_FRAME))','col_h10_l4_lp_asb_x')
(R/'tb.sv').write_text(tb)
src=(W/'tools/s81_dv/frame_bench.f').read_text().splitlines();script=(W/'tools/s81_dv/tokfunc/run_dense_xs_cap_gb.sh').read_text();extra=re.search(r"src \+= '''(.*?)'''\.splitlines",script,re.S)[1].splitlines();src+=extra+['rtl/common/landed_parent/ot_pl_land.sv']
src=[p for p in dict.fromkeys(src)if p.strip()and not p.startswith('#')and p!='tools/s81_dv/tokfunc/tb_dense_xs_cap_gb.sv']+[str(R/'frame.selected.sv'),str(R/'tb.sv')]
missing=[p for p in src if not p.startswith('+')and not pathlib.Path(p if p.startswith('/')else W/p).is_file()];assert not missing,missing
(R/'sources.f').write_text('\n'.join(src)+'\n')
# Original fixture oracle and programme are unchanged; append only aliases selected by the actual bound source audit.
for name,source in [('vec_pos','vec_pos'),('vec_wrong','vec_swap')]:
 v=pathlib.Path('/srv/opentallas-scratch2/claude/tok15-gb')/source;o=R/name;shutil.copytree(v,o,dirs_exist_ok=True)
 meta=json.loads((v/'meta.json').read_text());material={p.name:p.read_text()for p in v.glob(frame+'_*.viamap.hex')};out=I.alias_material(material,top,frame,meta['pairs'],audit,W)
 for key,text in out.items():(o/key).write_text(text)
defs=['-D'+d for d in ab['defines']]
with(R/'build.log').open('w')as log:subprocess.run(['verilator','--binary','--timing','-O1','-Wno-fatal','-Werror-MODDUP','-Wno-WIDTH','-Wno-TIMESCALEMOD','-Wno-lint','-Wno-style','-Wno-MULTIDRIVEN',*defs,'--top-module','tb_dense_xs_cap_gb','-Mdir',str(R/'obj'),'-f',str(R/'sources.f'),'--build-jobs','8','-MAKEFLAGS','OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0'],cwd=W,stdout=log,stderr=subprocess.STDOUT,check=True)
T=json.loads((R/'vec_pos/dense_program.json').read_text())['cycles'];binary=R/'obj/Vtb_dense_xs_cap_gb'
for name,vec,mut in [('run_mut0','vec_pos',0),('run_mut1','vec_pos',1),('run_wrongimg','vec_wrong',0)]:
 with(R/(name+'.log')).open('w')as log:subprocess.run([str(binary),f'+OT_ROM_DIR={R/vec}',f'+T={T}',f'+mut={mut}'],stdout=log,stderr=subprocess.STDOUT)
prog=json.loads((R/'vec_pos/dense_program.json').read_text());pin=prog['calibrated_common_shift_model']+CHECK.XS4_PATH_EDGES
positive=CHECK.check(R/'vec_pos',R/'run_mut0.log',pin);mutant=CHECK.check(R/'vec_pos',R/'run_mut1.log',pin);wrong=CHECK.check(R/'vec_wrong',R/'run_wrongimg.log',pin)
rec=dict(source_commit=subprocess.check_output(['git','-C',str(W),'rev-parse','HEAD'],text=True).strip(),scope='Actual current source frame JSON emitted with real binder QX variants and full-leaf image selectors; actual XS4→one frame→CAP component, uniform833ps phase, fixture gather oracle, no die transports/clock/provisioning qualification',positive=positive,input_mutant=mutant,wrong_loaded_image=wrong,pass_=positive['status']=='PASS'and mutant['status']=='FAIL'and wrong['status']=='FAIL',clock_ps=833,full_frame_provider_qualified=False,full_token=False,actual_source_json_sha256=hashlib.sha256(jpath.read_bytes()).hexdigest(),generated_frame_sha256=hashlib.sha256((R/'frame.selected.sv').read_bytes()).hexdigest())
(R/'check.json').write_text(json.dumps(rec,indent=1)+'\n');print('NATIVE_BOUND_FRAME',rec['pass_'],positive['status'],positive['errors'][:5],mutant['status'],wrong['status'],flush=True)
sys.exit(0 if rec['pass_'] else 1)
