"""Native VM local-clock kits consume source-pinned die pin grants exactly."""
import hashlib,json,pathlib,re,sys
R=pathlib.Path(__file__).resolve().parents[2];sys.path[:0]=[str(R/'tools'),str(R/'tools/ref_tile')]
import ref_tile as RT
import textbook_lint as TL
from hbm_vm_strap_kits import AUDIT
GRANT='results/arch/hbm_die_v15/vm_native_face_grants_1016.json'
slots=json.loads((R/GRANT).read_text())['slots']
base=json.loads((R/'physical/ref_tile/vm_strap_q0_ref/spec.json').read_text())
for q,slot in enumerate(slots):
 assert hashlib.sha256((R/slot['source']).read_bytes()).hexdigest()==slot['source_sha256']
 name=f'vm_face_q{q}_ref';hdrel=f'physical/hbm_vm_face_1016/q{q}';hd=R/hdrel;hd.mkdir(parents=True,exist_ok=True)
 s=json.loads(json.dumps(base));s.update(name=name,top=slot['cell'],sources=[slot['source'],'rtl/hbm_accel/generic/vm/static/ot_vms_bank_static_face_roots.sv','rtl/hbm_accel/generic/vm/static/ot_vms_ce_counter_pipe.sv','physical/asap7_memory_macros_v2/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2_bb.v'],outline=dict(slot['outline'],exact=True),params={},clock='hybrid_entries',clock_port='clk_ctrl',clock_ports=['clk_ctrl','clk_in_n','clk_in_e','clk_in_s','clk_in_w','clk_s1','clk_s2','clk_ecc','clk_out_n','clk_out_e','clk_out_s','clk_out_w','clk_ma','clk_mb','clk_mc'],clock_cts_roots=['clk_ctrl','clk_in_n','clk_in_e','clk_in_s','clk_in_w','clk_s1','clk_s2','clk_ecc','clk_out_n','clk_out_e','clk_out_s','clk_out_w'],clock_data_paths='related_same_frequency',clock_relationship={'kind':'same_pll_fixed_phase','ratio':[1,1],'phase_ps':0},contract={'file':GRANT,'slot':slot['name']},pins={f:[] for f in 'NSEW'},pin_ranges={},io_tcl=hdrel+'/io.tcl',orfs_vars={'POST_IO_PLACEMENT_TCL':hdrel+'/post_iop.tcl'})
 for k in ['spine_through_icg','spine','spine_steps','structural_change']:s.pop(k,None)
 s['layer_cap']=slot['layer_cap'];s['pg_layer']=slot['pg_layer'];s['layer_cap_grant']='H-DIE grant e7297d3d3 source0187d0f0b,270x313.2 M6PG/signalcap,M7parent;15literal face clocks, real20umchannels, no inherited hard view.'
 expected=[]
 for p in slot['pins']:
  stem=p['name'].split('[')[0];s['pins'][p['face']].append(stem);s['pin_ranges'][stem]=p['span_um'];m=re.search(r'\[(\d+):(\d+)\]',p['name']);n=int(m[1])+1 if m else 1;assert len(p['bit_centres_um'])==n
  for b,c in enumerate(p['bit_centres_um']):expected.append((f'{stem}[{b}]' if m else stem,p['face'],p['layer'],c))
 io=['# Authoritative native local-root die pin grant; exact actual-track centres.','source /src/physical/common_flow/assigned_pin_exact.tcl','set vm_expected {',*[' {%s %s %s %.9f}'%row for row in expected],'}','set vm_block [ord::get_db_block]','foreach bt [$vm_block getBTerms] {if {[$bt getSigType] in {POWER GROUND}} continue;foreach bp [$bt getBPins] {odb::dbBPin_destroy $bp}}','foreach item $vm_expected {lassign $item name face layer along;ot_assigned_pin_exact $name $layer $face $along}']
 (hd/'io.tcl').write_text('\n'.join(io)+'\n');(hd/'post_iop.tcl').write_text(f'source /src/{hdrel}/io.tcl\n'+AUDIT)
 dirs=TL.module_port_dirs(TL.rtl_modules([(R/slot['source']).read_text()])[slot['cell']])
 domains={('core' if p=='clk_ctrl' else p.removeprefix('clk_')):dict(ratio=[1,1],ports=[p],inputs=[],outputs=[]) for p in s['clock_ports']}
 faces={p['name'].split('[')[0]:p['face'].lower() for p in slot['pins']}
 for p,direction in dirs.items():
  if p in s['clock_ports']:continue
  if direction=='input':owner='core' if p in ['bid','sid','rst_n','rslot','rslot_v','wslot','wslot_v'] else 'in_'+faces[p]
  else:owner='out_'+faces[p]
  domains[owner]['inputs' if direction=='input' else 'outputs'].append(p)
 s['clock_entry_domains']=domains
 for i,m in enumerate(s['macros']):m.update(at=[47.52,[23.76,114.48,205.2][i]],inst='bank.u_'+['a','b','c'][i],clock_entry={'port':['clk_ma','clk_mb','clk_mc'][i],'pin':'clk','reference':'raw_liberty_clock_pin'})
 s['pin_regs']={'enable':False,'reason':'Actual pin capture and output launch flops retained at same data edges; only their clocks split by exact pin face. No wrapper data flops added. Literal component benches prove write3/read6 edges; io_flop_at_pins anchors the actual source flops.'}
 purpose='Measured9clock q0/1/2 CTS still Rmax471..565ps/spread170..244, input/regregTTnegative. Replace one four-face capture/output clock by N/E/S/W roots based on exact assigned ABI; preserve internal control/S1/S2/ECC roots and3rawmacroentries. Rebuild270x313.2 with20.232um SRAMchannels; same3write/6read edges, no added data/register state. Actual native clock/TT/FF/DRC and die adoption OPEN.'
 rg,wg=[(5,2),(4,2),(5,3),(5,3)][q]
 srcs=' '.join(['rtl/hbm_accel/generic/vm/static/ot_vms_ce_counter_pipe.sv','rtl/hbm_accel/generic/vm/static/ot_vms_bank_static_face_roots.sv','rtl/hbm_accel/generic/vm/static/ot_vms_bank_face_physical.sv','rtl/hbm_accel/generic/vm/static/physical/hfd_vms_bank_face_q*.sv','physical/asap7_memory_macros_v2/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v','rtl/hbm_accel/generic/vm/static/native_abi_1016/tb_hbm_vm_face_literal.sv'])
 def bench(mut):return f'iverilog -g2012 -s tb_hbm_vm_face_literal -Ptb_hbm_vm_face_literal.SID={q} -Ptb_hbm_vm_face_literal.RG={rg} -Ptb_hbm_vm_face_literal.WG={wg} -Ptb_hbm_vm_face_literal.MUT={mut} -o {{RUN}}/bench_{mut}.vvp {srcs} && vvp {{RUN}}/bench_{mut}.vvp'
 s['job']={'owner':'Codex H-SM native clock recovery','branch':'codex/hbm-vm-faces-0405','tag':'face1','purpose':purpose,'structural_change':purpose,'record_to':f'results/rtl/ref_tile/{name}','views_to':f'physical/ref_tile/{name}/views','extra_paths':['rtl/hbm_accel/generic/vm/static',hdrel,GRANT,'physical/common_flow/assigned_pin_exact.tcl'],'benches':[{'name':'native8bank_exact','cmd':bench(0),'expect':'pass','pass_regex':'VM_LOCAL_LITERAL PASS','threads':1,'peak_ram_gb':8},{'name':'actual_macro_clockdrop_mutant','cmd':bench(5),'expect':'fail','fail_regex':'FATAL: .*actual SRAM readback mismatch','threads':1,'peak_ram_gb':8}]}
 kd=R/'physical/ref_tile'/name;kd.mkdir(parents=True,exist_ok=True);(kd/'spec.json').write_text(json.dumps(s,indent=1)+'\n');RT.gen(str(kd/'spec.json'));print(name)
