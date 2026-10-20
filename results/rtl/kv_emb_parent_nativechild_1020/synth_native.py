import pathlib,subprocess,json,re,hashlib
p=pathlib.Path.cwd();w=p/'synth_native';w.mkdir(exist_ok=True)
e='rtl/qwen_sys/static_embedding_20261014/'
files=[e+x for x in ['qkd_kvs_emb_ctx_n32child.sv','qkd_embedding_ctx_start_n32child.sv','qkd_embedding_static_join.sv','qkd_embedding_static_join_fan32.sv','qkd_embedding_static_join4.sv','qkd_embedding_static_join4_cal.sv','qkd_embedding_row_tx_ctx_native32.sv']]+['rtl/lib/ot_rst_relay.sv']
m='physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2'
cfg={'DESIGN_NICKNAME':'emb_parent_nativechild','DESIGN_NAME':'qkd_kvs_emb_ctx_n32child','PLATFORM':'asap7','VERILOG_FILES':' '.join('/src/'+f for f in files),'ADDITIONAL_LIBS':'/src/'+m+'_tt.lib','ADDITIONAL_LEFS':'/src/'+m+'.lef','SDC_FILE':'/work/constraint.sdc','DIE_AREA':'0 0 388.8 302.4','CORE_AREA':'2.16 2.16 386.64 300.24','PLACE_DENSITY':'0.5','CORNER':'WC','NUM_CORES':'4','LEC_CHECK':'0','SYNTH_CANONICALIZE_TCL':'/src/physical/common_flow/ot_keep_regs.tcl'}
(w/'config.mk').write_text(''.join('export '+k+' = '+v+'\n' for k,v in cfg.items()));(w/'constraint.sdc').write_text('create_clock -name ck -period 833.333 [get_ports ck]\n')
image=subprocess.check_output(['docker','image','inspect','openroad/orfs:latest','--format','{{.Id}}'],text=True).strip()
mount=['docker','run','--rm','--memory=16g','--memory-swap=16g','-v',str(p)+':/src:ro','-v',str(w)+':/work',image]
with (w/'synth.log').open('w') as f:r=subprocess.run(mount+['bash','-lc','source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; cd /OpenROAD-flow-scripts/flow; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base synth'],stdout=f,stderr=subprocess.STDOUT)
assert r.returncode==0,(w/'synth.log').read_text()[-3000:]
libs=sorted(set(re.findall(r'Executing Liberty frontend: (.+)',(w/'synth.log').read_text())))
assert libs,'no actual synthesis libraries found'
args=['python3','/src/tools/ref_tile/native_census.py','--netlist','/work/results/asap7/emb_parent_nativechild/base/1_2_yosys.v','--top','qkd_kvs_emb_ctx_n32child','--out','/work/native_census.json']
for lib in libs:args+=['--liberty',lib]
r=subprocess.run(mount+args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True);(w/'native.log').write_text(r.stdout)
(w/'provenance.json').write_text(json.dumps(dict(image=image,liberty=libs,source_files={f:hashlib.sha256((p/f).read_bytes()).hexdigest() for f in files},native_census_sha256=hashlib.sha256((p/'tools/ref_tile/native_census.py').read_bytes()).hexdigest()),indent=2)+'\n')
print(r.stdout,flush=True);raise SystemExit(r.returncode)
