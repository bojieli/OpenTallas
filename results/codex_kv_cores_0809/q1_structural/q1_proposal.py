import json,subprocess,pathlib,copy,hashlib
l=pathlib.Path('/srv/opentallas-scratch2/claude/codex-kv-cores-0809');out=l/'q1_proposal';out.mkdir(exist_ok=True)
p=json.load(open(l/'pd/cores/qkd_ectlk_q1_pins.json'));moves=[]
for q in p['pins']:
 if q['name'] in ('ck[0]','rst_n[0]'):
  before=q.copy();q['x']=round(q['x']+8.64,3);moves.append(dict(before=before,after=q.copy()))
assert len(moves)==2
p['source']+=' | CODEX structural SRAM pin-access repair: clock/reset entry +8.64x clears SRAM E pin halo; data pins unchanged'
(out/'qkd_ectlk_q1_pins.json').write_text(json.dumps(p,indent=1)+'\n')
s=json.loads(subprocess.check_output(['git','-C','/home/ubuntu/OpenTallas','show','18c72cf920:results/kv_core_slice_1/slices/qkd_ectlk_q1.json'],text=True));d=s['slice'];d['entry']['xy_um'][0]+=8.64
for j in (0,2):d['entry']['island_um'][j]+=8.64
for q in d['entry']['pins']:q['to'][1]+=8.64
L=203.04;tt=86.86+.8057*L;d['far_corner_um']=L;d['free_cell_corner_bound_um']=194.4
d['entry']['rule']='12.8a near-centre +8.64x for structural macro-pin-halo clearance (CLOCK-KV 09:xx accepted), not timing trim'
d['insertion_model'].update(L_max_um=L,pred_TT_ps=round(tt,2),pred_FF_ps=round(tt*.8118,2),band='IN',note='Original calibrated geometry predictor; target unchanged; actual free-cell corner bound194.4um below200')
s['plan_sha256']=hashlib.sha256((l/'pd/hm_r26.json').read_bytes()).hexdigest();s['applied_plan_sha256']=s['plan_sha256'];s['structural_delta']='Q1 macro pair +25.92y, clock/reset entry +8.64x, 0 RTL/boot/data cycles'
(out/'q1_slice.json').write_text(json.dumps(s,indent=1)+'\n')
macros=[dict(name=r'u_ref.u_leaf.u_a.u.u.g_static_rows.u_rows.g_data.g_macro\[0\].u_s',x=112.104,y=127.404,orient='R0'),dict(name=r'u_ref.u_leaf.u_a.u.u.g_static_rows.u_rows.g_data.g_macro\[1\].u_s',x=8.64,y=127.404,orient='R0'),dict(name=r'u_ref.u_leaf.u_b.u.g_static_rows.u_rows.g_data.g_macro\[0\].u_s',x=12.961,y=73.98,orient='MY'),dict(name=r'u_ref.u_leaf.u_b.u.g_static_rows.u_rows.g_data.g_macro\[1\].u_s',x=12.961,y=32.892,orient='R180')]
(out/'macro_delta.json').write_text(json.dumps(dict(module='qkd_ectlk_q1',outline_um=[216,172.8],pin_moves=moves,macro_width_um=94.824,macro_height_um=41.064,macros=macros,cycles_added=0,clock_island_um=d['entry']['island_um'],macro_E_pin_halo_um=4.32,clock_island_to_body_gap_um=4.535,lower_S_capture_band_um=32.892),indent=1)+'\n')
a=['# Fixed, data-flow-reviewed Q1 macro plan; lower SRAM pair shifted as one pinless-S/N stack.', 'proc q1_macro_site {name x y orient} {', ' set b [ord::get_db_block];set u [$b getDbUnitsPerMicron];set i [$b findInst $name]', ' if {$i eq "NULL"} {error "missing planned SRAM $name"}', ' $i setPlacementStatus PLACED;$i setOrient $orient;$i setLocation 0 0;set q [$i getBBox]', ' set xx [expr {int(round($x*$u))-[$q xMin]}];set yy [expr {int(round($y*$u))-[$q yMin]}]', ' $i setLocation $xx $yy;$i setPlacementStatus LOCKED', ' puts "Q1_PLANNED_SRAM $name $x $y $orient"', '}']
for q in macros:a.append('q1_macro_site {'+q['name']+'} '+str(q['x'])+' '+str(q['y'])+' '+q['orient'])
(out/'q1_macro_plan.tcl').write_text('\n'.join(a)+'\n');print('Q1_PROPOSAL',moves,'model',round(tt,2),round(tt*.8118,2))
