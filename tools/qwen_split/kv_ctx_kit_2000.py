"""Actual OVL context leaf kits; no inherited scalar body or physical view."""
from pathlib import Path
import json, re, hashlib
ROOT=Path(__file__).resolve().parents[2]
TOP='qkd_kvn_ctx_ovl_rope'
SRC='rtl/qwen_sys/d2d_static_20261015/qkd_kvn_ctx_ovl_rope.sv'
def gen(tag,size):
 kit=Path('physical/ref_tile')/(TOP+'_'+tag); k=ROOT/kit;k.mkdir(parents=True,exist_ok=True)
 head=[f'head_record[{i}]' for i in range(552)]
 controls=['ck','rst_n']+[f'ovl_users[{i}]' for i in range(4)]+[f'calrx[{i}]' for i in range(4)]+['adm_done','reseed']
 outputs=[f'compiled_identity[{i}]' for i in range(59)]+[f'compiled_generation[{i}]' for i in range(2)]+['fault']
 faces=dict(W=head[:138],N=head[138:207]+controls+head[207:276],S=head[276:414],E=head[414:]+outputs)
 seen=[];lines=['# Actual OVL context pins: M4 H / M5 V origin .012 pitch .048 minimum width .024.']
 plan={}
 for face,names in faces.items():
  plan[face]=dict(pins=len(names),span=size-4.416,pins_per_um=len(names)/(size-4.416))
  assert plan[face]['pins_per_um']<6
  for i,n in enumerate(names):
   pos=.012+round((2.208+(size-4.416)*(i+.5)/len(names)-.012)/.048)*.048
   layer='M4' if face in 'WE' else 'M5'
   x,y=(.042 if face=='W' else size-.042,pos) if face in 'WE' else (pos,.042 if face=='S' else size-.042)
   dx,dy=(.084,.024) if layer=='M4' else (.024,.084)
   lines.append(f'place_pin -pin_name {{{n}}} -layer {layer} -location {{{x:.6f} {y:.6f}}} -pin_size {{{dx:.6f} {dy:.6f}}}')
   seen.append(n)
 assert len(seen)==len(set(seen))==626
 (k/'assigned_pins.tcl').write_text('\n'.join(lines)+'\n');(k/'pin_geometry_plan.json').write_text(json.dumps(plan,indent=2)+'\n')
 benches=[]
 for variant in ('good','wrong_user','stale'):
  item=dict(name='actual_context_'+variant,cmd=f'bash tools/qwen_kv_die/rope_ovl/run_kvn_ctx_physical_2000.sh {{RUN}}/bench/{variant} {variant}',expect='pass' if variant=='good' else 'fail',threads=2,peak_ram_gb=4,needs=['verilator'])
  if variant=='good':item['pass_regex']='KVN_CTX_OVL_PASS'
  else:item.update(fail_regex='WRONG_USER_NOT_REJECTED|OWNER_FAIL',fail_witness=f'results/rtl/kv_ctx_2000/component/{variant}.log')
  benches.append(item)
 spec=dict(name=TOP+'_'+tag,top=TOP,kind='tile',sources=[SRC],params=dict(MUT_USER=0,MUT_STALE=0),clock_port='ck',reset_ports=['rst_n'],outline=dict(w=size,h=size,exact=True),layer_cap='M5',macros=[],children=[],inter=[],pins={'ANY':['ck','rst_n','head_record','ovl_users','calrx','adm_done','reseed','compiled_identity','compiled_generation','fault']},io_tcl=str(kit/'assigned_pins.tcl'),pin_regs=dict(enable=False,reason='Actual RTL captures head/user/calrx/admission once, owner/stage update and output capture separately; reset_first/reset_last land rst_n in two ck edges. No flow-inserted stage or scalar context substitution.'),keep_pin_regs=True,inhold=True,outhold=True,io_flop_at_pins=dict(cols=4,allow_none=True),route=dict(pd=.5,threads=4,peak_ram_gb=8,pin_min_tracks=3,m5_pg_pitch=2.7,hold_margin_ns=.03,macro_halo_um=5.4,period_ps=770),job=dict(owner='Codex:CODEX-KV-CTX-2000',branch='codex/kv-ctx-2000',tag=tag,purpose='Actual recurring OVL Ckind12 owner/stage authority; exact de062 source and MUT0 params. Conservative standard833.333ps characterization is 1fs tighter than actual parent833.334ps; no completed parent clock contract or closed scalar view transfer.',benches=benches,extra_paths=['tools/qwen_kv_die/rope_ovl/run_kvn_ctx.sh','tools/qwen_kv_die/rope_ovl/run_kvn_ctx_physical_2000.sh','tools/qwen_kv_die/rope_ovl/tb_kvn_ctx_ovl.sv','tools/qwen_kv_die/rope_ovl/tb_kvn_ctx_physical_2000.sv','tools/qwen_kv_die/rope_ovl/tb_kvn_ctx_copy_equiv.sv','tools/qwen_kv_die/rope_ovl/reference/qkd_kvn_ctx_de062_ref.sv'],views_to=str(kit/'views'),record_to='results/rtl/ref_tile/'+TOP+'_'+tag),recipe=3,pin_reg_split=True,hold_pad=dict(cell='HB2xp67_ASAP7_75t_R'),structural_change='Authentic real OVL context source,626 declared ports,61 KVI bits plus fault EAST; existing86.4 diagnostic frame is not a view. Head capture/update/output are three sampled local edges, unchanged.')
 (k/'spec.json').write_text(json.dumps(spec,indent=2)+'\n')
 (k/'README.md').write_text(f'# {TOP}_{tag}\n\nReal de062539e predecessor plus grouped same-edge selector/write/reset control copies, MUT_USER0/MUT_STALE0. Original max260 native failure preserved; current source hash is bound by the frame receipt. No scalar body/view transfer.\n\nSAFE DESIGN: pins use existing RTL capture/output stages; reset_first/reset_last provide two source ck captures. Reach all pins within {size} square, before measured gate. Native fanout/depth must pass before layout; four61b owner banks plus four6b stage counters and sampled HEAD are below2kb, no SRAM needed. No hard macros, full standard-cell band, aspect1. All626 literal pins fit full faces under6/um on M4/M5 preferred grid. Clock north midpoint, actual parent clk_core_c833.334ps (CORE_HALF0.416667ns); existing supported profile characterizes833.333ps,1fs tighter, route770ps,60/25ps uncertainty,30ps hold margin. Exact completed parent clock contract remains pending. Schedule unchanged: raw edge0 capture,edge1 state update,edge2 output register. Admission/reseed parent relay is not covered by the existing four-user component bench (admission held1/reseed0). Native, placed access, clocks and route acceptance remain OPEN.\n')
 return kit
if __name__=='__main__':
 for tag,size in [('cm3',43.2),('cf3',64.8)]:print(gen(tag,size))
