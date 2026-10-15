#!/usr/bin/env python3
"""Real83-child /2278-FF source-specific nativeCTS diagnostic, no fake core macro."""
from pathlib import Path
import json,re,math,sys
sys.path[:0]=[str(Path(__file__).resolve().parents[2]/"tools/ref_tile"),str(Path(__file__).resolve().parents[2]/"tools")]
import ref_tile as RT
r=Path(__file__).resolve().parents[2];name='qfd_tile_nk_banked_v1';kit=r/'physical/ref_tile'/name;kit.mkdir(exist_ok=True)
p=json.loads((r/'physical/qwen_tile_glue_banks_1015/parent_plan_tx198.json').read_text());m=json.loads((r/'rtl/qwen_sys/tile_parent_banked_20261015/bank_manifest.json').read_text())
old=json.loads((r/'tools/ref_tile/specs_q_compute_native/qfd_tile_nk_native.json').read_text())
ren=lambda n:n.replace('u_tile.u_tile.u_logic.','u_logic.')
s=dict(old);s.update(name=name,top=name,params={},outline={'w':481.68,'h':1400.22},children=[],clock_ports=['ck'],clock_cts_roots=['ck'],clock='hybrid_entries',io_tcl=f'physical/ref_tile/{name}/assigned_pins.tcl',pins={'W':['n_a','n_b','n_y','t_out'],'E':['tap','tile_id','tie_hi','tie_lo','rst_n'],'ANY':['ck_bank','ck_reset','ck_child','ck']},pin_ranges={},child_lattice_um=.216)
for b in p['bodies']:
 n=b['inst'];view=b.get('view') or f"physical/ref_tile/{b['master']}/views/{b['master']}"
 s['children'].append({'view':view,'count':1,'inst':ren(n),'at':[b['x'],b['y']],'at_exact':True,'orient':b['orient']})
assert len(s['children'])==83
s['outline']['exact']=True
# Resolve the real M4/M6 pin-track lattice before freezing clock/data pads.
actual=RT.place_blocks(s,481.68,1400.22,RT.blocks_of(s))
assert all(x['offtrack']==0 for x in actual),[(x['inst'],x['offtrack'])for x in actual if x['offtrack']]
shift={}
for c,b in zip(s['children'],actual):
 shift[b['inst']]=[b['x']-c['at'][0],b['y']-c['at'][1]];c['at']=[b['x'],b['y']]
gap=min(max(b['x']-a['x']-a['w'],a['x']-b['x']-b['w'],b['y']-a['y']-a['h'],a['y']-b['y']-b['h'])for i,a in enumerate(actual)for b in actual[i+1:])
assert gap>5.0,gap
s['abut_plan']={'channel_um':round(gap,6),'edge_um':2.0,'why':'HELD diagnostic only: measure actual dense closed-bank pin/PG/channel access; no20um production-rule exception or merge credit'}
(kit/'actual_grid_geometry.json').write_text(json.dumps({'outline_um':[481.68,1400.22],'blocks':[{k:v for k,v in b.items()if not k.startswith('_')}for b in actual],'minimum_channel_um':gap,'shifts_um':shift,'status':'HELD_DIAGNOSTIC_NO_PHYSICAL_QUALIFICATION'},indent=2)+'\n')
src=json.loads((r/'tools/ref_tile/specs_q_compute_native/qfd_tile_nk_native.json').read_text())['sources'];src=[x for x in src if x!='rtl/physical/qfd_tile_nk_slot.sv']
src+=['rtl/qwen_sys/tile_parent_banked_20261015/'+x for x in ['ot_qwen_w12_matvec_part_banked_v1.sv','ot_qwen_rom_tile_logic_banked_v1.sv','qfd_tile_nk_banked_v1.sv']]+['rtl/qwen_sys/tile_glue_banks_20261015/ot_qwen_tx198.sv','physical/qwen_tile_glue_banks_1015/parent_banks_bb.v']
s['sources']=list(dict.fromkeys(src))
widths={'qkh_packet_v16':16,'qkh_packet_h256':256,'qkh_packet_v256':256,'qwen_glue_v514':514,'qwen_glue_v508':508}
(r/'physical/qwen_tile_glue_banks_1015/parent_banks_bb.v').write_text('\n'.join(f'(* blackbox *) module {n}(input clk,rst_n,input[{w-1}:0]d,output[{w-1}:0]q);endmodule' for n,w in widths.items())+'\n')
# Published actual child clock pads, no snapping or coordinate approximation.
roots={x['instance']:x for x in p['clock_roots']};hard={};pins=[];points={}
for n,port in [(z['inst'],z['clock_port'])for z in m['banks']]+[(n,f'ck_reset[{i}]')for i,n in enumerate(m['reset_nodes'])]+[(n,f'ck_child[{i}]')for i,n in enumerate(m['child_order'])]:
 root=roots[n];x,y=root['actual_clock_xy_um'];dx,dy=shift[ren(n)];x+=dx;y+=dy;s['clock_ports'].append(port);hard[port]=ren(n)+'/clk';points[port]={'layer':'M5','xy_um':[x,y],'basis':'exact transformed CLOSED child clock pad; M5 parent entry to child M4 pin'}
 s['clock_port']='ck'
s['required_hybrid_roots']={'standard_cell_cts':['ck'],'hard_child_entry':hard}
# Standard-cell entry: real RTL input in a demonstrably free parent point;
# no macro outline or guessed internal FF/clock characterization is assigned.
ob=[(b['x']-1.08,b['y']-1.08,b['x']+b['w']+1.08,b['y']+b['h']+1.08)for b in actual]
candidates=[]
for x in range(6,476,3):
 for y in range(6,1394,3):
  xx=.012+.048*round((x-.012)/.048);yy=.012+.048*round((y-.012)/.048)
  if not any(a<=xx<=c and b<=yy<=d for a,b,c,d in ob):candidates.append(((xx-240.84)**2+(yy-700.11)**2,xx,yy))
_,x,y=min(candidates);points['ck']={'layer':'M5','xy_um':[x,y],'basis':'new source-assigned standard-cell CTS input point in actual free space; residual FF positions/insertion measured by fresh gate, no invented84thmacro'}
# Preserve frozen actual parent data-bit ordering, applying source-selected
# face translations and explicit track rounding only to NEW parent pads.
delta={z['parent_face']:z['delta_xy_um'][1]for z in p['parent_face_ABI_changes']};delta['n_y']-=5.04;delta['t_out']+=5.4;delta['rst_n']=-28.62
pat=re.compile(r'place_pin -pin_name \{([^}]+)\} -layer (\S+) -location \{([\d.]+) ([\d.]+)\}')
for line in (r/'physical/ref_tile/qfd_tile_nk_native/assigned_pins.tcl').read_text().splitlines():
 mm=pat.search(line)
 if not mm:continue
 port,layer,x,y=mm.groups();base=port.split('[')[0]
 if base.startswith('ck'):continue
 x=float(x);y=float(y)+delta.get(base,0)
 if x>400:x+=32.4
 if layer=='M4':y=.012+.048*round((y-.012)/.048)
 if layer=='M5':x=.012+.048*round((x-.012)/.048)
 points[port]={'layer':layer,'xy_um':[round(x,6),round(y,6)],'basis':'frozen bit ordering + explicit new parent face ABI/track rounding'}
assert len(points)==2598-15+84,(len(points),2598-15+84)
tcl=[f'place_pin -pin_name {{{n}}} -layer {v["layer"]} -location {{{v["xy_um"][0]:.6f} {v["xy_um"][1]:.6f}}}'for n,v in points.items()]
(kit/'assigned_pins.tcl').write_text('\n'.join(tcl)+'\n');(kit/'assigned_pins.json').write_text(json.dumps({'schema':'qwen.compute.parent.actual_pins.v1','outline_um':[481.68,1400.22],'pins':points,'native_entries':83,'standard_cell_entries':1,'residual_soft_ff':954,'residual_pre_abc_source_ff':2278,'mapped_count_basis':'actual immutable85b373696 preGPL ODB e3082225523e3389dfc81748de8c3483e936895fc603a70bd4c3661f92f89e17','qualification':'PENDING_ACTUAL_CTS_NATIVE_PG_PIN_GATES'},indent=2)+'\n')
s['job']={'owner':'Codex:q_compute_elem','branch':'codex/q-compute-native-parents-1014','tag':'bp58b','purpose':'Actual58bank/84root successor nativeCTS: real fullRNE+954mapped residual FFs(2278preABC), exact83CLOSED masters/pins; no oldparent qualification','extra_paths':['physical/qwen_tile_glue_banks_1015','rtl/qwen_sys/tile_parent_banked_20261015','results/rtl/qwen_compute_native_glue_1014/parent_banked_v1'], 'views_to':f'physical/ref_tile/{name}/views','record_to':f'results/rtl/ref_tile/{name}','cycles_added':2,'benches':[]}
s['structural_change']='Actual oldNK15037sink longdata/reset/setup failures replaced by58 independent existing-edge data banks,11 actual three-edge reset tree roots,14unchangedCLOSED children. TX390→198 AFTER RNE, fulls2_x128 separate, tag167→4usedsplitbits. Balanced return+1/xdelay9, nodein+1/out+1. Original residual source2278FFs maps to954actual DFFs retained as stdcells in freearea; freshCTS measures actual clock/RNE/fanout, no invented residual macro. Complete3499word oldparent reference+3mutants PASS; source31507pin dependencies checked. Compiler candidate unselected until physical gates.'
s['job']['benches']=[{'name':'lint','expect':'pass','threads':1,'peak_ram_gb':4,'needs':['verilator'],'cmd':'verilator --lint-only -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -DSYNTHESIS -DOT_QWEN_LSL_FP1 --top-module '+name+' '+' '.join(s['sources'])+' && echo lint-ok'}]
s['job']['benches'].append({'name':'actual_parent_source_oracle','expect':'pass','threads':1,'peak_ram_gb':1,'cmd':'python3 physical/qwen_tile_glue_banks_1015/verify_parent_receipt.py','pass_regex':'^PASS exact real-parent numerical receipt44'})
s['job']['hold_merge']='HELD diagnostic dense-channel measurement; production20um channel/pin/PG proof and actual native gates remain required'
s['route'].update(threads=8,peak_ram_gb=32)
(r/f'tools/ref_tile/specs_q_compute_native/{name}.json').write_text(json.dumps(s,indent=2)+'\n')
print('actual native model83children/84roots', 'parentCK',points['ck'],'pins',len(points))

# Exact hardmacro d/q capture endpoints verified against the actual ODB.
# Shared hook must be published before admission; no allow_none fallback.
s.setdefault('orfs_vars',{})['OT_OFLOP_HARD_FACE_AUDIT']='/src/physical/qwen_tile_glue_banks_1015/hard_face_binding.tcl'
(r/f'tools/ref_tile/specs_q_compute_native/{name}.json').write_text(json.dumps(s,indent=2)+'\n')
