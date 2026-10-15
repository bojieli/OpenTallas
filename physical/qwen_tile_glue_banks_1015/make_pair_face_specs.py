#!/usr/bin/env python3
"""PM-H-S face masters (r13 NL helper 2026-10-15): qwen_glue_x1028 (NK paired W face) and qwen_glue_w514 (NL t_out).
Exact interleaved M4 pin plan from the coordinator's frozen tile-level plan: local y = 5.292 + 0.096 s.
 x1028 32.4 x 110.16 R0: W x=0.096 oq[k] s=2k, id[k] s=2k+1; E x=32.304 od[k] s=2k, iq[k] s=2k+1;
       clk_o W M4 (0.096,1.308), clk_i W M4 (0.096,2.412; the requested 2.388 is off the 0.048 M4 lattice); rst_o_n / rst_i_n S M5 (9.708 / 11.628, 0.096).
 w514  21.6 x 110.16 R0: W x=0.096 q[k] s=2k; E x=21.504 d[k] s=2k; clk W M4 (0.096,1.308); rst_n S M5 (9.708,0.096).
M5 PG pitch 2.7 (v514 final).  Parent origins: TB y 699.84 / YA y 591.84, x 5.4 -> W pins land on tile slots."""
import json
from pathlib import Path
r=Path(__file__).resolve().parents[2]
y=lambda s:round(5.292+0.096*s,6)
def emit(name,W,H,ports,scalars,pins,top_src,extra):
 kit=r/'physical/ref_tile'/name;kit.mkdir(parents=True,exist_ok=True)
 positions={};tcl=[]
 for port,x,slots in ports:
  pts=[[x,y(s)] for s in slots];positions[port]=dict(layer='M4',xy_um=pts)
  tcl+=[f'place_pin -pin_name {{{port}[{b}]}} -layer M4 -location {{{px:.6f} {py:.6f}}}' for b,(px,py) in enumerate(pts)]
 for port,x,yy,layer in scalars:
  positions[port]=dict(layer=layer,xy_um=[[x,yy]]);tcl.append(f'place_pin -pin_name {{{port}}} -layer {layer} -location {{{x:.6f} {yy:.6f}}}')
 allxy=[(p['layer'],tuple(xy)) for p in positions.values() for xy in p['xy_um']];assert len(set(allxy))==len(allxy)
 for p in positions.values():
  for xx,yy in p['xy_um']:assert 0<xx<W and 0<yy<H and (p['layer']!='M4' or abs((yy-.012)/.048-round((yy-.012)/.048))<1e-6)
 (kit/'assigned_pins.tcl').write_text('\n'.join(tcl)+'\n')
 (kit/'assigned_pins.json').write_text(json.dumps(dict(schema='opentallas.qwen.full-face-pins.v1',name=name,outline_um=[W,H],positions=positions,
   tile_plan='PM-H-S (main 48fab3baf / c75914db1): local y = 5.292 + 0.096 s; parent origin x 5.4, y 699.84 (TB) / 591.84 (YA)',
   pg_rule='M5 PG 2.7 um pitch; clocks W/M4 below data 5.292; resets S/M5'),indent=2)+'\n')
 s=json.load(open(r/'physical/qwen_head_bank_pins_1015/packet_template.json'))
 s.update(name=name,top=name,params={},sources=['rtl/qwen_sys/head_staging_20261015/ot_qkh_packet_stage.sv','rtl/lib/ot_rst_relay.sv',top_src],
          outline=dict(w=W,h=H),pins=pins,io_tcl=f'physical/ref_tile/{name}/assigned_pins.tcl',
          pin_ranges={p:[sl[0],sl[-1]] for p,sl in ((port,[y(s) for s in slots]) for port,_,slots in ports)})
 s['route']['m5_pg_pitch']=2.7
 s['job'].update(owner='Claude:q15_compute_elem',tag='pm1',branch='claude/q15-nl-banked',
   purpose='PM-H-S straight-wired interleaved W-face master',extra_paths=['physical/qwen_tile_glue_banks_1015','rtl/test/qwen_head_staging'],
   views_to=f'physical/ref_tile/{name}/views',record_to=f'results/rtl/ref_tile/{name}')
 s.update(extra)
 (r/'tools/ref_tile/specs_q_compute_native'/(name+'.json')).write_text(json.dumps(s,indent=2)+'\n');print(name,len(tcl),'pins')
def benches(which,n):
 b=[dict(name=f'{which}_m0',cmd=f'bash physical/qwen_tile_glue_banks_1015/bench_pair.sh {{RUN}}/bench/{which}_0 {which} 0',expect='pass',threads=1,peak_ram_gb=1,needs=['iverilog'],pass_regex=f'^PASS {n}')]
 for m in (1,2):b.append(dict(name=f'{which}_m{m}',cmd=f'bash physical/qwen_tile_glue_banks_1015/bench_pair.sh {{RUN}}/bench/{which}_{m} {which} {m}',expect='fail',threads=1,peak_ram_gb=1,needs=['iverilog'],fail_regex=f'^FAIL {n}'))
 return b
K=range(514)
x={'clock':'multiple_cts_roots','clock_port':'clk_o','clock_ports':['clk_o','clk_i'],'reset_ports':['rst_o_n','rst_i_n'],
   'clock_entry_domains':{'core':{'ratio':[1,1],'ports':['clk_o'],'inputs':['od','rst_o_n'],'outputs':['oq']},
                          'inner':{'ratio':[1,1],'ports':['clk_i'],'inputs':['id','rst_i_n'],'outputs':['iq']}},
   'structural_change':'New PM-H-S paired W-face master: the two qwen_glue_v514 face captures of a facing tree-word pair in one straight-wired body with bit-interleaved M4 pins (0.096 um apart); two independent 514-sink roots, zero added edges.',
   'reroute_reason':{'kind':'rtl_change','source':'rtl/qwen_sys/tile_glue_banks_20261015/qwen_glue_x1028.sv','cell':'qwen_glue_x1028','why':'new master, no prior route'}}
emit('qwen_glue_x1028',32.4,110.16,[('oq',.096,[2*k for k in K]),('id',.096,[2*k+1 for k in K]),('od',32.304,[2*k for k in K]),('iq',32.304,[2*k+1 for k in K])],
     [('clk_o',.096,1.308,'M4'),('clk_i',.096,2.412,'M4'),('rst_o_n',9.708,.096,'M5'),('rst_i_n',11.628,.096,'M5')],
     {'W':['oq','id','clk_o','clk_i'],'E':['od','iq'],'S':['rst_o_n','rst_i_n']},'rtl/qwen_sys/tile_glue_banks_20261015/qwen_glue_x1028.sv',x)
w={'reset_ports':['rst_n'],'clock_port':'clk',
   'structural_change':'New PM-H-S NL t_out face master: qwen_glue_v514 RTL with pins on the even interleaved TB slots (0.192 um pitch, W=q); zero added edges.',
   'reroute_reason':{'kind':'rtl_change','source':'rtl/qwen_sys/tile_glue_banks_20261015/qwen_glue_w514.sv','cell':'qwen_glue_w514','why':'new master, no prior route'}}
emit('qwen_glue_w514',21.6,110.16,[('q',.096,[2*k for k in K]),('d',21.504,[2*k for k in K])],[('clk',.096,1.308,'M4'),('rst_n',9.708,.096,'M5')],
     {'W':['q','clk'],'E':['d'],'S':['rst_n']},'rtl/qwen_sys/tile_glue_banks_20261015/qwen_glue_w514.sv',w)
for n,wh,pat in (('qwen_glue_x1028','x1028','qwen_glue_x1028'),('qwen_glue_w514','w514','qkh_packet_stage W=514')):
 p=r/'tools/ref_tile/specs_q_compute_native'/(n+'.json');s=json.loads(p.read_text());s['job']['benches']=benches(wh,pat);p.write_text(json.dumps(s,indent=2)+'\n')
