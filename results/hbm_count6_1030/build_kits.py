#!/usr/bin/env python3
import hashlib,json,pathlib,re,shutil,sys
D=pathlib.Path(__file__).resolve().parent;M=json.load(open(D/(sys.argv[1] if len(sys.argv)>1 else 'source_manifest.json')));jobs=[]
for row in M['selected']:
 inst=row['instance'];K=D/'tc'/inst;K.mkdir(parents=True,exist_ok=True);assert not(K/'count_result.json').exists(),'Refuse to overwrite a completed attempt';(K/'rtl').mkdir(exist_ok=True);(K/'macros').mkdir(exist_ok=True);macros=[];files=[];providers=[]
 for name,src in row['closure'].items():
  if src.get('MISSING'):raise RuntimeError('BLOCKED missing source '+name)
  if name.startswith('ot_sram_'):
   source=pathlib.Path(src['source']);modeldir=source.parent
   need=[modeldir/(name+'_bb.v'),modeldir/(name+'.lef'),modeldir/(name+'_tt.lib'),modeldir/(name+'_ff.lib')]
   if not all(p.exists()for p in need):
    canonical=pathlib.Path('/srv/opentallas-scratch2/claude/wt/codex-hbm-su-native-1030/physical/asap7_memory_macros')/name
    model=canonical/(name+'.v')
    assert model.exists() and hashlib.sha256(model.read_bytes()).hexdigest()==src['file_sha256'],'BLOCKED realprovider functionalbody differs from actualnative'
    modeldir=canonical;need=[modeldir/(name+'_bb.v'),modeldir/(name+'.lef'),modeldir/(name+'_tt.lib'),modeldir/(name+'_ff.lib')]
   if not all(p.exists()for p in need):raise RuntimeError('BLOCKED missing real macro provider '+str(need))
   for p in need:shutil.copy(p,K/'macros'/p.name)
   providers.append(dict(module=name,files={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in need},source=str(modeldir)));macros.append(name);files.append('/work/macros/'+name+'_bb.v')
  else:shutil.copy(D/'native'/(name+'.sv'),K/'rtl'/(name+'.sv'));files.append('/work/rtl/'+name+'.sv')
 top='current_native_count_'+inst;P=row['ports'];params=', '.join('.'+n+'('+str(len(row['actual_parameter_bits'][n]))+"'b"+row['actual_parameter_bits'][n]+')'for n in row['params'])
 wrapper='module '+top+'(\n'+',\n'.join(v['direction']+' wire '+(f"[{v['width']-1}:0] "if v['width']>1 else'')+n for n,v in P.items())+'\n);\n'+row['module']+(' #('+params+')'if params else'')+' u_current('+','.join('.'+n+'('+n+')'for n in P)+');\nendmodule\n';(K/'rtl/whole_native_wrapper.sv').write_text(wrapper);files.append('/work/rtl/whole_native_wrapper.sv')
 defines=M['native_defines'];assert len(defines)==7
 (K/'pre.ys').write_text('read_verilog -sv '+' '.join('-D'+d for d in defines)+' '+' '.join(files)+'\nhierarchy -check -top '+top+'\nproc\nmemory_collect\nwrite_json /work/pre.json\n')
 clks=[n for n,v in P.items()if v['direction']=='input'and(n=='clk'or n.startswith('clk_')or n.endswith('_clk'))]
 (K/'count.sdc').write_text(('create_clock -name core -period 833 [get_ports {'+' '.join(clks)+'}]\n')if clks else'')
 cfg='export PLATFORM = asap7\nexport DESIGN_NAME = '+top+'\nexport VERILOG_FILES = '+' '.join(files)+'\nexport SDC_FILE = /work/count.sdc\nexport VERILOG_DEFINES = '+' '.join(['-DSYNTHESIS']+['-D'+d for d in defines])+'\nexport CORNERS = tc bc\nexport DEFAULT_CORNER = tc\nexport ABC_CLOCK_PERIOD_IN_PS = 833\nexport SYNTH_HIERARCHICAL = 0\n'
 cfg+='export TC_LIB_FILES = $(TC_NLDM_LIB_FILES) '+' '.join('/work/macros/'+n+'_tt.lib'for n in macros)+'\nexport BC_LIB_FILES = $(BC_NLDM_LIB_FILES) '+' '.join('/work/macros/'+n+'_ff.lib'for n in macros)+'\noverride export LIB_FILES = $(TC_LIB_FILES)\n'
 if macros:cfg+='export ADDITIONAL_LEFS = '+' '.join('/work/macros/'+n+'.lef'for n in macros)+'\n'
 (K/'config.mk').write_text(cfg);(K/'source.json').write_text(json.dumps(dict(instance=inst,module=row['module'],top=top,params=row['params'],ports=P,defines=defines,actual_plan=row['actual_plan'],whole_native_no_face_shell=True,qualified_providers=providers,source_hashes={n:r['export_sha256']for n,r in row['closure'].items()},macro_allowlist=macros),indent=1)+'\n')
 for name in ['run_inside.py','run_count.sh']:shutil.copy(D/name,K/name)
 jobs.append(dict(instance=inst,module=row['module'],params=row['params'],path=str(K),source_status='READY',defines=defines,extra_face_shell_cycles=0,PNR=False,LEC=False))
(D/('launch_'+pathlib.Path(sys.argv[1]).stem+'_tc.json' if len(sys.argv)>1 else 'launch_manifest_tc.json')).write_text(json.dumps(dict(status='READY_FOR_NATIVE_WHOLE_SYNTH_COUNT_ONLY',jobs=jobs),indent=1)+'\n');print('READY',[(r['instance'],r['module'])for r in jobs],flush=True)
