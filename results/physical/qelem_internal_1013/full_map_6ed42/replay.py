from pathlib import Path
import subprocess,json,hashlib,re
base=Path('/srv/opentallas-scratch/codex/q-full-map-6ed42'); out=base/'output';out.mkdir(exist_ok=True);src=base/'src'
files=['rtl/v41rom/ot_v41_rom_elem_q_w10.sv', 'rtl/v41rom/ot_v41_rom_elem_q_qp_w10.sv', 'rtl/v41rom/ot_v41_rom_elem_w10.sv', 'rtl/v41rom/ot_v41_rom_elem_qx_w10.sv', 'rtl/v41rom/ot_v41_rom_elem_q_qx_w10.sv', 'rtl/v41rom/ot_v41_rom_elem_qx_pq_w10.sv', 'rtl/v41rom/ot_v41_rom_elem_q_qxpq_w10.sv', 'rtl/v41rom/ot_v41_elem_pq_tags.sv', 'rtl/v41rom/ot_v41_kreg.sv', 'rtl/v41rom/ot_v41_chain3.sv', 'rtl/v41rom/ot_v41_bterm.sv', 'rtl/v41rom/ot_v41_chain.sv', 'rtl/v41rom/ot_v41_segtree.sv', 'rtl/v41rom/ot_v41_bf16_lanes.sv', 'rtl/v41rom/ot_v41_fadd.sv', 'rtl/v41rom/ot_v41_bmul2.sv', 'rtl/v41rom/ot_v41_bterm2_w10.sv', 'rtl/v41rom/ot_v41_chain2.sv', 'rtl/v41rom/ot_v41_segtree2.sv', 'rtl/v41rom/ot_v41_bf16_lanes2.sv', 'rtl/v41rom/ot_v41_bterm3_w10.sv', 'rtl/v41rom/ot_v41_bterm4_w10.sv', 'rtl/v41rom/ot_v41_bterm5_w10.sv', 'rtl/v41rom/ot_v41_segtree3.sv', 'rtl/v41rom/ot_v41_segtree4.sv', 'rtl/v41rom/ot_v41_segtree5.sv', 'rtl/v41rom/ot_v41_segtree6.sv', 'rtl/v41rom/ot_v41_chain4.sv', 'rtl/v41rom/ot_v41_fadd2.sv', 'rtl/hdc/ot_hdc_fpu.sv', 'rtl/hdc/ot_hdc_fp32_mul_pipe.sv', 'rtl/hdc/ot_hdc_delay.sv', 'rtl/hdc/ot_hdc_cg.sv', 'rtl/common/ot_prefix.sv', 'rtl/proto/ot_fp32_add_rne_pipe.sv', 'physical/asap7_memory_macros/ot_rom_4096x274_m8/ot_rom_4096x274_m8_bb.v', 'physical/asap7_memory_macros/ot_rom_8192x274_m8/ot_rom_8192x274_m8_bb.v']
ys='read_liberty -lib /srv/opentallas-scratch/codex/q-full-map-6ed42/libs/merged.lib\nread_verilog -sv -DSYNTHESIS /srv/opentallas-scratch/codex/q-full-map-6ed42/src/rtl/v41rom/ot_v41_rom_elem_q_w10.sv /srv/opentallas-scratch/codex/q-full-map-6ed42/src/rtl/v41rom/ot_v41_rom_elem_q_qp_w10.sv /srv/opentallas-scratch/codex/q-full-map-6ed42/src/rtl/v41rom/ot_v41_rom_elem_w10.sv /srv/opentallas-scratch/codex/q-full-map-6ed42/src/rtl/v41rom/ot_v41_rom_elem_qx_w10.sv /srv/opentallas-scratch/codex/q-full-map-6ed42/src/rtl/v41rom/ot_v41_rom_elem_q_qx_w10.sv /srv/opentallas-scratch/codex/q-full-map-6ed42/src/rtl/v41rom/ot_v41_rom_elem_qx_pq_w10.sv /srv/opentallas-scratch/codex/q-full-map-6ed42/src/rtl/v41rom/ot_v41_rom_elem_q_qxpq_w10.sv /srv/opentallas-scratch/codex/q-full-map-6ed42/src/rtl/v41rom/ot_v41_elem_pq_tags.sv /srv/opentallas-scratch/codex/q-full-map-6ed42/src/rtl/v41rom/ot_v41_kreg.sv /srv/opentallas-scratch/codex/q-full-map-6ed42/src/rtl/v41rom/ot_v41_chain3.sv /srv/opentallas-scratch/codex/q-full-map-6ed42/src/rtl/v41rom/ot_v41_bterm.sv /srv/opentallas-scratch/codex/q-full-map-6ed42/src/rtl/v41rom/ot_v41_chain.sv /srv/opentallas-scratch/codex/q-full-map-6ed42/src/rtl/v41rom/ot_v41_segtree.sv /srv/opentallas-scratch/codex/q-full-map-6ed42/src/rtl/v41rom/ot_v41_bf16_lanes.sv /srv/opentallas-scratch/codex/q-full-map-6ed42/src/rtl/v41rom/ot_v41_fadd.sv /srv/opentallas-scratch/codex/q-full-map-6ed42/src/rtl/v41rom/ot_v41_bmul2.sv /srv/opentallas-scratch/codex/q-full-map-6ed42/src/rtl/v41rom/ot_v41_bterm2_w10.sv /srv/opentallas-scratch/codex/q-full-map-6ed42/src/rtl/v41rom/ot_v41_chain2.sv /srv/opentallas-scratch/codex/q-full-map-6ed42/src/rtl/v41rom/ot_v41_segtree2.sv /srv/opentallas-scratch/codex/q-full-map-6ed42/src/rtl/v41rom/ot_v41_bf16_lanes2.sv /srv/opentallas-scratch/codex/q-full-map-6ed42/src/rtl/v41rom/ot_v41_bterm3_w10.sv /srv/opentallas-scratch/codex/q-full-map-6ed42/src/rtl/v41rom/ot_v41_bterm4_w10.sv /srv/opentallas-scratch/codex/q-full-map-6ed42/src/rtl/v41rom/ot_v41_bterm5_w10.sv /srv/opentallas-scratch/codex/q-full-map-6ed42/src/rtl/v41rom/ot_v41_segtree3.sv /srv/opentallas-scratch/codex/q-full-map-6ed42/src/rtl/v41rom/ot_v41_segtree4.sv /srv/opentallas-scratch/codex/q-full-map-6ed42/src/rtl/v41rom/ot_v41_segtree5.sv /srv/opentallas-scratch/codex/q-full-map-6ed42/src/rtl/v41rom/ot_v41_segtree6.sv /srv/opentallas-scratch/codex/q-full-map-6ed42/src/rtl/v41rom/ot_v41_chain4.sv /srv/opentallas-scratch/codex/q-full-map-6ed42/src/rtl/v41rom/ot_v41_fadd2.sv /srv/opentallas-scratch/codex/q-full-map-6ed42/src/rtl/hdc/ot_hdc_fpu.sv /srv/opentallas-scratch/codex/q-full-map-6ed42/src/rtl/hdc/ot_hdc_fp32_mul_pipe.sv /srv/opentallas-scratch/codex/q-full-map-6ed42/src/rtl/hdc/ot_hdc_delay.sv /srv/opentallas-scratch/codex/q-full-map-6ed42/src/rtl/hdc/ot_hdc_cg.sv /srv/opentallas-scratch/codex/q-full-map-6ed42/src/rtl/common/ot_prefix.sv /srv/opentallas-scratch/codex/q-full-map-6ed42/src/rtl/proto/ot_fp32_add_rne_pipe.sv /srv/opentallas-scratch/codex/q-full-map-6ed42/src/physical/asap7_memory_macros/ot_rom_4096x274_m8/ot_rom_4096x274_m8_bb.v /srv/opentallas-scratch/codex/q-full-map-6ed42/src/physical/asap7_memory_macros/ot_rom_8192x274_m8/ot_rom_8192x274_m8_bb.v\nchparam -set EARLY 1 -set FAST 1 -set MTP 1 -set NB 2 -set PP 1 -set PQ 1 -set QM 5 -set QPIPE 1 -set QP_CAP 0 -set QP_CSAM 10 -set QP_P1 1 -set QP_XS 1 -set QS 6 -set QTIMING_FIX 1 -set QW 0 -set QX 10 -set QY 1 -set QZ 1 -set QZ_NE 4 -set QZ_NS 8 -set QH 1 ot_v41_rom_elem_q_qxpq_w10\nsynth -top ot_v41_rom_elem_q_qxpq_w10 -flatten -noabc\nstat\nwrite_json /srv/opentallas-scratch/codex/q-full-map-6ed42/output/generic.json\n'
(out/'generic.ys').write_text(ys)
image='sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29'
cmd=['docker','run','--rm','-v',str(base)+':'+str(base),image,'/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys','-s',str(out/'generic.ys')]
with (out/'generic.log').open('w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
print('GENERIC',r.returncode,flush=True)
if r.returncode:raise SystemExit(r.returncode)

import pathlib,gzip
libs=base/'libs';libs.mkdir(exist_ok=True)
subprocess.run(['docker','run','--rm','-v',str(libs)+':/out','sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29','bash','-lc','cp /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_TT* /out/'],check=True)
blocks=[]; templates={}
for p in sorted(libs.glob('asap7*')):
 s=gzip.open(p,'rt').read() if p.suffix=='.gz' else p.read_text()
 for m in re.finditer(r'\b(?:cell|lu_table_template|power_lut_template)\s*\([^)]*\)\s*\{',s):
  start=m.start();i=m.end();n=1
  while n:
   if s[i]=='{':n+=1
   if s[i]=='}':n-=1
   i+=1
  if m.group(0).startswith("cell"): blocks.append(s[start:i])
  else: templates[m.group(0)]=s[start:i]
lib=libs/'merged.lib';lib.write_text('library (s81_inventory_tt) {\ntime_unit:"1ps"; capacitive_load_unit (1,ff); voltage_unit:"1V"; current_unit:"1mA";\n'+ '\n'.join(templates.values())+'\n'+'\n'.join(blocks)+'\n}\n')

top='ot_v41_rom_elem_q_qxpq_w10'
mapped='read_json {out}/generic.json\ndffunmap\ndfflibmap -liberty {lib}\nabc -liberty {lib}\nstat -liberty {lib}\nwrite_json {out}/mapped.json\n'.format(out=out,lib=lib)
(out/'mapped.ys').write_text(mapped)
with (out/'mapped.log').open('w') as f:r=subprocess.run(['docker','run','--rm','-v',str(base)+':'+str(base),image,'/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys','-s',str(out/'mapped.ys')],stdout=f,stderr=subprocess.STDOUT)
print('MAPPED',r.returncode,flush=True)
if r.returncode:raise SystemExit(r.returncode)
mods=json.loads((out/'mapped.json').read_text())['modules'];types={};flops=0
clock_pins={}
def walk(m):
 global flops
 for c in mods[m].get('cells',{}).values():
  t=c['type']
  if t in mods and not mods[t].get('attributes',{}).get('blackbox'):walk(t)
  else:
   types[t]=types.get(t,0)+1
   if t.startswith('DFF'):flops+=1
walk(top)
log=(out/'mapped.log').read_text();areas=re.findall(r"Chip area for (?:top )?module '[^']*': ([\d.]+)",log)
rec={'schema':'opentallas.s81.q_full.mapped_inventory.v1','source_commit':'6ed42d12c','top':top,'params':{'EARLY': 1, 'FAST': 1, 'MTP': 1, 'NB': 2, 'PP': 1, 'PQ': 1, 'QM': 5, 'QPIPE': 1, 'QP_CAP': 0, 'QP_CSAM': 10, 'QP_P1': 1, 'QP_XS': 1, 'QS': 6, 'QTIMING_FIX': 1, 'QW': 0, 'QX': 10, 'QY': 1, 'QZ': 1, 'QZ_NE': 4, 'QZ_NS': 8, 'QH': 1},'mapped_std_area_um2':float(areas[-1]),'clock_sink_flop_cells':flops,'cells_by_type_hierarchical':types,'actual_macro_counts':{k:v for k,v in types.items() if k.startswith('ot_rom_')},'ports':{k:{'direction':v['direction'],'bits':len(v['bits'])} for k,v in mods[top]['ports'].items()},'physical_admission':False,'qualification':'Complete physical source PQ1 inventory only. Functional full native PQ1 program, five source-level partitions, CTS/pins/clocks/SSFF/routed closure remain open.','source_sha256':{x:hashlib.sha256((src/x).read_bytes()).hexdigest() for x in files},'tool_image':subprocess.check_output(['docker','image','inspect','--format','{{.Id}}',image],text=True).strip(),'library_sha256':{x.name:hashlib.sha256(x.read_bytes()).hexdigest() for x in libs.iterdir() if x.is_file()},'log_sha256':{x.name:hashlib.sha256(x.read_bytes()).hexdigest() for x in out.glob('*.log')}}
(out/'receipt.json').write_text(json.dumps(rec,indent=2)+'\n');print(json.dumps({'sinks':flops,'area_um2':rec['mapped_std_area_um2']}),flush=True)
