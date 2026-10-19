#!/usr/bin/env python3
"""Generate a diagnostic INPUT boundary probe, never a numeric frame substitute."""
from pathlib import Path
import hashlib,json,re,subprocess
from head_local_contract import ROOT
base=ROOT/'results/rtl/s81_qf_producer_1019/sid6_vehicle'
die=Path('/tmp/s81-selected-ceaed19c4-die.v').read_bytes()
assert hashlib.sha256(die).hexdigest()=='61b683b697d17b7d6d1619352d302648d835822677c02097ce48639a0aa399b8'
lines=die.decode().splitlines();src=json.loads((base/'selected_input_return_cone.json').read_text())['lines']
frames=[r['text'] for r in src if ' col_h' in r['text']];assert len(frames)==6
stations=[r['text'] for r in src if ' st_x_' in r['text']];assert len(stations)==23
mxsource=subprocess.check_output(['git','show','ceaed19c4:rtl/dsrom_sys/s81_dv/frame_l4/col_h9_l4.sv']).decode()
mxlines=[l for l in mxsource.splitlines() if re.search(r'dsfd_dvrly_276_NS u_xo[0-3] ',l)];assert len(mxlines)==4
for k,l in enumerate(mxlines):
 for port,name in [('i','x'),('o','xo')]:
  body=re.search(r'\.'+port+r'\(\{([^}]+)\}\)',l).group(1)
  assert [v.strip() for v in body.split(',')]==[f'{name}[{i}]' for i in range(276*k+275,276*k-1,-1)]
 assert f'.ck(xk[{k}])' in l and '.rs(rst_n)' in l and f'.ck_o(xok[{k}])' in l
# Selected statements have simple named scalar/vector nets; reuse their exact declarations.
used=set(re.findall(r'\b(?:w_x_|r_x_|nx_|u_f_3)[A-Za-z0-9_]+', '\n'.join(stations+frames)))
used={n for n in used if not n.startswith('u_f_3') or n.endswith('_xok')}
decls=[];found=set()
for l in lines:
 if not l.strip().startswith('wire '):continue
 names=set(re.findall(r'\b[A-Za-z_][A-Za-z0-9_]*\b',l))&used
 if names:decls.append(l);found|=names
assert found==used,(used-found)
resets=sorted(set(re.findall(r'\b(?:rs_|rsg_)[A-Za-z0-9_]+','\n'.join(stations+frames))))
body=['module selected_input_cone(input wire clk,rst_n,input wire[1100:0]source_word,output wire[6605:0]observed,output wire[6599:0]observed_pins,output wire[5:0]pins_valid,output wire[5:0]faults);',
 'wire ck_cl3S=clk;wire[15:0]u_s_3S_ck_xc={16{clk}};wire[4415:0]xc;reg[1:0]mkq;',
 'always @(posedge clk or negedge rst_n)if(!rst_n)mkq<=0;else mkq<={mkq[0],1\'b1};',
 'wire[1103:0]xw4={source_word[1100:565],source_word[0],mkq[1],source_word[564:0],mkq[1]};',
 'generate for(genvar c=0;c<4;c++)begin:head ot_s81sl_rly #(.W(1104),.D(6))u_x(.clk(clk),.d(xw4),.q(xc[1104*c+:1104]));end endgenerate']
body+=decls
for r in resets:body.append(f'wire {r}=rst_n; // controlled logical reset assumption, native regional date NULL')
for copy,name in enumerate(['3L01','3R01','3L02','3R02']):
 for lane in range(4):body.append(f'assign w_x_f_{name}_l{lane}_src=xc[{1104*copy+276*lane}+:276];')
body+=stations
for i,line in enumerate(frames):
 name=re.search(r'\) (u_f_\w+) ',line).group(1)
 # Obtain exact real frame consumer bindings, then stop at its actual cfifo input boundary.
 port=lambda n:re.search(r'\.'+n+r'\(([^()]*)\)',line).group(1)
 body.append(f'wire[282:0]a_{i};wire[265:0]b_{i};wire[14:0]c_{i};wire[535:0]d_{i};')
 body.append(f'dsfd_cfifo_crs4 ingress_{name}(.cr(ck_cl3S),.cr_s(ck_cl3S),.rst({port("rst_n")}),.xk({port("xk")}),.lk({port("lk")}),')
 xparts=re.search(r'\.x\(\{([^}]+)\}\)',line).group(1).split(', ')
 for k in range(4):body.append(f'.xl{k}({xparts[3-k]}),')
 body.append(f'.ri(66\'d0),.st(2\'d0),.cc(c_{i}),.rd(),.rs(),.xa(a_{i}),.xb(b_{i}),.x2(d_{i}));')
 body.append(f'assign observed_pins[{1100*i}+:1100]={{a_{i},b_{i},c_{i},d_{i}}};assign pins_valid[{i}]=a_{i}[282]|c_{i}[1]|c_{i}[0];')
 body.append(f'assign observed[{1101*i}+:1101]=ingress_{name}.xw_;assign faults[{i}]=|ingress_{name}.flt;')
 if '_MX_' in line:
  out=re.search(r'\.xo\(\{([^}]+)\}\)',line).group(1)
  body.append(f'selected_mx_forwarder forward_{name}(.rst_n({port("rst_n")}),.xk({port("xk")}),.x({{{", ".join(xparts)}}}),.xo({{{out}}}),.xok({port("xok")}));')
body+=['endmodule','module selected_mx_forwarder(input wire rst_n,input wire[3:0]xk,input wire[1103:0]x,output wire[1103:0]xo,output wire[3:0]xok);']+mxlines+['endmodule']
out=base/'input_marker_sources';out.mkdir(exist_ok=True)
(out/'selected_input_cone.sv').write_text('\n'.join(body)+'\n')
rec=dict(scope='Diagnostic input boundary only, NOT numeric frame substitute',selected_die_SHA256=hashlib.sha256(die).hexdigest(),
 mx_source_path='rtl/dsrom_sys/s81_dv/frame_l4/col_h9_l4.sv',mx_source_ref='ceaed19c4',mx_source_sha256=hashlib.sha256(mxsource.encode()).hexdigest(),
 mx_extraction_sha256=hashlib.sha256(('\n'.join(mxlines)+'\n').encode()).hexdigest(),
 mx_equivalence='All4 original statements unmodified; exact x/xo bit lists and xk/ck_o/rst bindings checked; only independent xo/xok boundary cone. Full6numeric uses actual fullframes.',
 actual_input_stations=23,actual_MX_forwarder_stations=8,actual_input_lanes=24,actual_CFIFO=6,regional_reset_names=resets,
 source_word='actual proved raw→quantizer→XS xw_d; no fixture payload injection',
 controlled_diagnostic_assumptions=['Common logical root for clk/cr/cr_s, actual source clock polarity paths retained','Named regional resets share declared diagnostic rst_n; all physical dates NULL','CFIFO return-only ri/st tied0 outside observed input-cone scope'],
 CFIFO_consumer_control={'request':'NONE in actual dsfd_cfifo_crs4 interface','read':'unconditional cr capture, actual ring counters/strap K; no ready handshake',
  'clear':'rst→actual rsync_q→landing reset; rsync_s only return status','ri_st':'Only ri_q/sti/rr/return status, no dependency into xl/xw_/xa/xb/cc/x2'},
 no_added_input_gates=True,native_physical_phase=None,numeric_frame_timing_qualified=False)
(out/'contract.json').write_text(json.dumps(rec,indent=2)+'\n')
print('INPUT_CONE_EXTRACTED actual23+8stations/24lanes/6CFIFO; no numericframe/native proof')
