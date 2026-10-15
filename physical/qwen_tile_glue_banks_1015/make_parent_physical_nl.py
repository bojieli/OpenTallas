#!/usr/bin/env python3
"""qfd_tile_nl_banked_v1 physical model (r13 NL helper 2026-10-15): the NK banked geometry (parent_plan_tx198.json,
same 481.68 x 1400.22 outline, same CLOSED masters / origins / orientations / clock pads) MINUS the node leaf and the
five NK-only node banks (face_n_a/b/y, node_stage_n_a/b/y), PLUS the CLOSED qwen_glue_v514 'to_reg' (the node's TOREG
edge) inside the node leaf's former footprint (east part, MY: d east / q west, rows 635-700 = node t_d/t_out band).
Pins: the NK native pin plan without n_a / n_b / n_y; every other data pin and translation identical to NK banked.
Channel rule: macro-to-macro gaps < 20 um are BLOCKED (physical/common_flow/macro_channel_block.tcl) and repair
buffers on macros are re-placed (post_resize_relocate.tcl) -- the textbook 'widen or block' remedy, not a waiver."""
from pathlib import Path
import json,re,sys
sys.path[:0]=[str(Path(__file__).resolve().parents[2]/"tools/ref_tile"),str(Path(__file__).resolve().parents[2]/"tools")]
import ref_tile as RT
r=Path(__file__).resolve().parents[2];name='qfd_tile_nl_banked_v1';kit=r/'physical/ref_tile'/name;kit.mkdir(exist_ok=True)
p=json.loads((r/'physical/qwen_tile_glue_banks_1015/parent_plan_tx198.json').read_text())
m=json.loads((r/'rtl/qwen_sys/tile_parent_nl_banked_20261015/bank_manifest.json').read_text())
nkm=json.loads((r/'rtl/qwen_sys/tile_parent_banked_20261015/bank_manifest.json').read_text())
old=json.loads((r/'tools/ref_tile/specs_q_compute_native/qfd_tile_nk_native.json').read_text())
ren=lambda n:n.replace('u_tile.u_tile.u_logic.','u_logic.')
DROP={'face_n_a','face_n_b','face_n_y','node_stage_n_a','node_stage_n_b','node_stage_n_y'}
node=next(b for b in p['bodies'] if b['inst'].endswith('.u_node'))
TOR={'kind':'bank','master':'qwen_glue_v514','inst':'to_reg','x':round(node['x']+node['w']-21.6,6),'y':629.91,'w':21.6,'h':75.6,'orient':'MY'}
bodies=[b for b in p['bodies'] if b['inst'] not in DROP and b is not node]+[TOR]
assert len(bodies)==77,len(bodies)
s=dict(old);s.update(name=name,top=name,params={},outline={'w':481.68,'h':1400.22},children=[],clock_ports=['ck'],clock_cts_roots=['ck'],clock='hybrid_entries',io_tcl=f'physical/ref_tile/{name}/assigned_pins.tcl',pins={'W':['t_out'],'E':['tap','tile_id','tie_hi','tie_lo','rst_n'],'ANY':['ck_bank','ck_reset','ck_child','ck']},pin_ranges={},child_lattice_um=.216)
for b in bodies:
 view=b.get('view') or f"physical/ref_tile/{b['master']}/views/{b['master']}"
 s['children'].append({'view':view,'count':1,'inst':ren(b['inst']),'at':[b['x'],b['y']],'at_exact':True,'orient':b['orient']})
s['outline']['exact']=True
actual=RT.place_blocks(s,481.68,1400.22,RT.blocks_of(s))
assert all(x['offtrack']==0 for x in actual),[(x['inst'],x['offtrack'])for x in actual if x['offtrack']]
shift={}
for c,b in zip(s['children'],actual):
 shift[b['inst']]=[b['x']-c['at'][0],b['y']-c['at'][1]];c['at']=[b['x'],b['y']]
pairs=[(max(b['x']-a['x']-a['w'],a['x']-b['x']-b['w'],b['y']-a['y']-a['h'],a['y']-b['y']-b['h']),a['inst'],b['inst'])for i,a in enumerate(actual)for b in actual[i+1:]]
gap=min(pairs);assert gap[0]>5.0,gap
s['abut_plan']={'channel_um':round(gap[0],6),'edge_um':2.0,'why':'HELD diagnostic probe (as NK banked): channels < 20 um are BLOCKED by physical/common_flow/macro_channel_block.tcl (textbook util_channel remedy "or block the channel"), measured by the route; no rule exception'}
(kit/'actual_grid_geometry.json').write_text(json.dumps({'outline_um':[481.68,1400.22],'blocks':[{k:v for k,v in b.items()if not k.startswith('_')}for b in actual],'minimum_channel_um':gap[0],'shifts_um':shift,'status':'NO_PHYSICAL_QUALIFICATION'},indent=2)+'\n')
src=[x for x in old['sources'] if x not in ('rtl/physical/qfd_tile_nk_slot.sv','rtl/physical/bb/ot_qwen_tile_node_bb.v')]
src+=['rtl/qwen_sys/tile_parent_banked_20261015/ot_qwen_w12_matvec_part_banked_v1.sv','rtl/qwen_sys/tile_parent_nl_banked_20261015/ot_qwen_rom_tile_logic_nl_banked_v1.sv','rtl/qwen_sys/tile_parent_nl_banked_20261015/qfd_tile_nl_banked_v1.sv','rtl/qwen_sys/tile_glue_banks_20261015/ot_qwen_tx198.sv','physical/qwen_tile_glue_banks_1015/parent_banks_bb.v']
s['sources']=list(dict.fromkeys(src))
# clock pads: CLOSED child / bank pads transformed exactly as NK; to_reg pad = the v514 MY pad offset used by face_n_y
roots={x['instance']:x for x in p['clock_roots']}
fny=next(b for b in p['bodies'] if b['inst']=='face_n_y');off=[a-b for a,b in zip(roots['face_n_y']['actual_clock_xy_um'],[fny['x'],fny['y']])]
roots['to_reg']={'actual_clock_xy_um':[TOR['x']+off[0],TOR['y']+off[1]]}
hard={};points={}
ports=[(z['inst'],z['clock_port'])for z in m['banks']]+[(n,f'ck_reset[{i}]')for i,n in enumerate(nkm['reset_nodes'])]+[(n,f'ck_child[{i}]')for i,n in enumerate(nkm['child_order'][:13])]
assert not any(n.endswith('.u_node') for n,_ in ports)
for n,port in ports:
 x,y=roots[n]['actual_clock_xy_um'];dx,dy=shift[ren(n)];x+=dx;y+=dy;s['clock_ports'].append(port);hard[port]=ren(n)+'/clk'
 points[port]={'layer':'M5','xy_um':[round(x,6),round(y,6)],'basis':'exact transformed CLOSED child clock pad; M5 parent entry to child M4 pin'}
s['required_hybrid_roots']={'standard_cell_cts':['ck'],'hard_child_entry':hard}
ob=[(b['x']-1.08,b['y']-1.08,b['x']+b['w']+1.08,b['y']+b['h']+1.08)for b in actual]
cand=[]
for x in range(6,476,3):
 for y in range(6,1394,3):
  xx=.012+.048*round((x-.012)/.048);yy=.012+.048*round((y-.012)/.048)
  if not any(a<=xx<=c and b<=yy<=d for a,b,c,d in ob):cand.append(((xx-240.84)**2+(yy-700.11)**2,xx,yy))
_,x,y=min(cand);points['ck']={'layer':'M5','xy_um':[x,y],'basis':'standard-cell CTS input point in actual free space (same rule as NK banked)'}
delta={z['parent_face']:z['delta_xy_um'][1]for z in p['parent_face_ABI_changes']};delta['t_out']+=5.4;delta['rst_n']=-28.62
pat=re.compile(r'place_pin -pin_name \{([^}]+)\} -layer (\S+) -location \{([\d.]+) ([\d.]+)\}')
for line in (r/'physical/ref_tile/qfd_tile_nk_native/assigned_pins.tcl').read_text().splitlines():
 mm=pat.search(line)
 if not mm:continue
 port,layer,x,y=mm.groups();base=port.split('[')[0]
 if base.startswith('ck') or base in ('n_a','n_b','n_y'):continue
 x=float(x);y=float(y)+delta.get(base,0)
 if x>400:x+=32.4
 if layer=='M4':y=.012+.048*round((y-.012)/.048)
 if layer=='M5':x=.012+.048*round((x-.012)/.048)
 points[port]={'layer':layer,'xy_um':[round(x,6),round(y,6)],'basis':'NK banked pin (frozen bit ordering + same face translation/track rounding)'}
want=2598-15-3*514+(53+11+13+1)
assert len(points)==want,(len(points),want)
nk_pins=json.loads((r/'physical/ref_tile/qfd_tile_nk_banked_v1/assigned_pins.json').read_text())['pins']
same=[k for k,v in points.items() if not k.startswith('ck') and k in nk_pins and nk_pins[k]['xy_um']==v['xy_um'] and nk_pins[k]['layer']==v['layer']]
assert len(same)==len([k for k in points if not k.startswith('ck')]),'NL data pins must equal NK banked pins'
(kit/'assigned_pins.tcl').write_text('\n'.join(f'place_pin -pin_name {{{n}}} -layer {v["layer"]} -location {{{v["xy_um"][0]:.6f} {v["xy_um"][1]:.6f}}}'for n,v in points.items())+'\n')
(kit/'assigned_pins.json').write_text(json.dumps({'schema':'qwen.compute.parent.actual_pins.v1','outline_um':[481.68,1400.22],'pins':points,'native_entries':77,'standard_cell_entries':1,'qualification':'PENDING_ACTUAL_CTS_NATIVE_PG_PIN_GATES'},indent=2)+'\n')
s['orfs_vars']={'OT_OFLOP_HARD_FACE_AUDIT':'/src/physical/qwen_tile_glue_banks_1015/hard_face_binding_nl.tcl',
 'POST_IO_PLACEMENT_TCL':'physical/common_flow/macro_channel_block.tcl','POST_RESIZE_TCL':'physical/common_flow/post_resize_relocate.tcl',
 'OT_CHANNEL_BLOCK_UM':'20','OT_ROW_MIN_UM':'6'}
s['job']={'owner':'Claude:q_compute_elem r13 NL helper','branch':'claude/q15-nl-banked','tag':'nl53a','purpose':'NODE-LESS tile local clock-root partition: 53 CLOSED banks/11 reset/13 CLOSED children/1 residual, same geometry/pins as NK banked minus node; first native CTS gate','extra_paths':['physical/qwen_tile_glue_banks_1015','rtl/qwen_sys/tile_parent_banked_20261015','rtl/qwen_sys/tile_parent_nl_banked_20261015','results/rtl/qwen_compute_native_glue_1014/parent_nl_banked_v1','physical/common_flow'],'views_to':f'physical/ref_tile/{name}/views','record_to':f'results/rtl/ref_tile/{name}','cycles_added':2,'benches':[]}
s['structural_change']='Old flat NL (14,006 sinks one glue root, boundary R 991 ps, spread 182 ps, TT -299 RPAIR2->south RQR) replaced by the NK banked local clock-root partition: 53 independent CLOSED data banks (to_reg = the TOREG edge as a bank), 11 three-edge reset roots, 13 unchanged CLOSED children; ROM return +1 / xdelay9 / TX198 shared with NK; t_out age identical to NK. Channels < 20 um blocked, repair buffers off macros.'
s['reroute_reason']={'kind':'rtl_change','source':'rtl/qwen_sys/tile_parent_nl_banked_20261015/qfd_tile_nl_banked_v1.sv','cell':name,'why':'new banked source (local clock roots); no prior route of this cell'}
s['job']['benches']=[{'name':'lint','expect':'pass','threads':1,'peak_ram_gb':4,'needs':['verilator'],'cmd':'verilator --lint-only -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -DSYNTHESIS -DOT_QWEN_LSL_FP1 --top-module '+name+' '+' '.join(s['sources'])+' && echo lint-ok'},
 {'name':'actual_parent_source_oracle','expect':'pass','threads':1,'peak_ram_gb':1,'cmd':'python3 physical/qwen_tile_glue_banks_1015/verify_parent_receipt_nl.py','pass_regex':'^PASS exact real NL parent numerical receipt'}]
s['job']['hold_merge']='PROBE like NK bp58c: sub-20um channels are hard-blocked by macro_channel_block.tcl but ref_tile floorplan_checks does not yet credit blocked channels; merge only after that rule/tool decision and native gates'
s['route'].update(threads=8,peak_ram_gb=32)
(r/f'tools/ref_tile/specs_q_compute_native/{name}.json').write_text(json.dumps(s,indent=2)+'\n')
print('NL physical model',len(actual),'bodies, min gap',gap,'pins',len(points),'parent ck',points['ck'])
