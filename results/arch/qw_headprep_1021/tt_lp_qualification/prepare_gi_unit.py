from pathlib import Path
import importlib.util,subprocess,json,sys
r=Path(sys.argv[1]).resolve()
spec=importlib.util.spec_from_file_location('lp',r/'tools/landed_parent/lp.py');lp=importlib.util.module_from_spec(spec);spec.loader.exec_module(lp)
s=(r/'rtl/qwen_dv/headprep/qfd_tt_ctlm_dv_lpf_hp_parts.sv').read_text();m=lp.parse_module(lp.preprocess(s,[]),'qfd_tt_ctlm_dv_gi_hp')
p='rtl/qwen_dv/qfd_tt_ctlm_dv_lpf_parts.sv';base=subprocess.check_output(['git','show','d2c8e45a7:'+p]).decode()
base=base.replace('.cmd_user(c_user)','.cmd_user()').replace('.loc_emb(c_emb)','.loc_emb()').replace('    wire        c_u0 =','    assign c_user=$root.tb.cu;assign c_emb=$root.tb.ce;\n    wire        c_u0 =')
(r/'gi_original_cut.sv').write_text(base)
lines=['`timescale 1ns/1ps','module tb;','reg clk=0;always #0.5 clk=~clk; reg [1:0] cu=0;reg ce=0;integer ticks=0,checks=0;']
for p in m['ports']:
 n=p['name'];rg=p['range'] or ''
 if p['dir']=='in':lines.append(f'reg {rg} {n}=0;')
 else:
  lines.append(f'wire {rg} n_{n};')
  if n not in ('emb_position','emb_user'):lines.append(f'wire {rg} o_{n};')
lines+=['always @* ck=clk;']
params=json.loads((r/'tools/landed_parent/specs/qfd_tt_ctlm_dv_lpf_hp_h16z.json').read_text())['params'];params.pop('XPF_TRANSPORT_EDGES')
pars=', '.join(f'.{k}({v})' for k,v in params.items())
for typ,inst,prefix in [('qfd_tt_ctlm_dv_gi','old','o_'),('qfd_tt_ctlm_dv_gi_hp','dut','n_')]:
 con=', '.join(f'.{p["name"]}({p["name"] if p["dir"]=="in" else prefix+p["name"]})' for p in m['ports'] if typ.endswith('_hp') or p['name'] not in ('emb_position','emb_user'))
 lines.append(f'{typ} #({pars}) {inst}({con});')
outs=[p['name']for p in m['ports']if p['dir']=='out' and p['name'] not in ('emb_position','emb_user')]
lines.append('task tick; reg[17:0] et,ep;reg[1:0] eu;reg ev;begin\n@(negedge clk);#0.01;\net=dut.tok_b[cu];ep=dut.pos_b[cu];eu=cu;ev=ce;\n@(posedge clk);#0.01;ticks=ticks+1;\nif(rst_n)begin\n')
for n in outs:lines.append(f'if(n_{n} !== o_{n}) $fatal(1,"original-output differential {n}");')
lines.append('if(n_emb_start!==ev || n_emb_token!==et || n_emb_position!==ep || n_emb_user!==eu) $fatal(1,"actual pre-edge bank export mismatch user=%0d pos=%0d expected=%0d",cu,n_emb_position,ep);checks=checks+1;end\nend endtask')
lines.append('''integer u;reg[127:0]ctx;
initial begin

 repeat(4)tick();rst_n=1;repeat(4)tick();
 ctx=0;ctx[127:112]=16'h4d43;ctx[110:108]=7;
 for(u=1;u<4;u=u+1)begin ctx[36*(u-1)+:18]=18'(301+u*17);ctx[36*(u-1)+18+:18]=18'(1001+u*19);end
 ctx_x={1'b1,ctx};tick();ctx_x=0;repeat(4)tick();
 for(u=1;u<4;u=u+1)if(dut.pos_b[u] !==18'(301+u*17)||dut.tok_b[u]!==18'(1001+u*19))$fatal(1,"real context bank load");
 dh=0;dh[42]=1;dh[35:18]=18'd77;dh[17:0]=18'd101;tick();dh=0;repeat(3)tick();
 if(dut.pos_b[0]!==18'd101||dut.tok_b[0]!==18'd77)$fatal(1,"real HOST bank load");
 for(u=0;u<4;u=u+1)begin cu=2'(u);ce=1;tick();ce=0;tick();end
 // A same-edge RESULT write must preserve the pre-edge position in the export.
 cu=2;ce=1;ss5=0;ss5[24]=1;ss5[27:26]=2;ss5[17:0]=18'd2001;tick();ss5=0;tick();tick();ce=0;tick();
 if(dut.pos_b[2]!==18'd336||dut.tok_b[2]!==18'd2001)$fatal(1,"real RESULT bank update");
 cu=2;ce=1;repeat(3)tick();ce=0;repeat(3)tick();
 rst_n=0;repeat(3)tick();rst_n=1;repeat(3)tick();cu=0;ce=1;tick();
 $display("GI_OUTPUT_CUT_PASS ticks=%0d checks=%0d users=4 ctx/HOST/RESULT writes; forced calendar outputs only",ticks,checks);$finish;end
endmodule
''')
(r/'tb_gi.sv').write_text('\n'.join(lines))
s=s.replace('.cmd_user(c_user)','.cmd_user()').replace('.loc_emb(c_emb)','.loc_emb()').replace('    wire        c_u0 =','    assign c_user=$root.tb.cu;assign c_emb=$root.tb.ce;\n    wire        c_u0 =')
(r/'gi_actual_cut.sv').write_text(s)
(r/'gi_wrong_late_pos.sv').write_text(s.replace('emb_position <= pos_b[c_user];','emb_position <= st_pos;'))
