from pathlib import Path
import re,json,hashlib
r=Path('/srv/opentallas-scratch2/claude/qc-types-r/w0_lec_diag_1116');src=Path('/srv/opentallas-scratch2/claude/fable-fix-qc-cbglue/headseg44/group44/src_804_complete')
s=(src/'rtl/hdc/ot_hdc_sfu.sv').read_text();m=re.search(r'module ot_hdc_vline\b.*?endmodule',s,re.S);assert m
(r/'actual_vline.sv').write_text('`define OT_ARST(x) or negedge x\n'+m[0]+'\n')
exp=(src/'rtl/hdc/ot_hdc_sfu_q.sv').read_text();p=exp[exp.index('localparam integer T_N'):exp.index('localparam [31:0] K_MAX')]
assert 'T_R1 = T_K + LA' in p
wrapper='''module valid_flush(input wire clk,rst_n,v,input wire[7:0]nk,output wire safe,output wire consumer,output wire bit30);
localparam LA=4,LM=5;
'''+p+'''
wire [DEPTH:0] vd;
ot_hdc_vline #(.D(DEPTH)) u_v(.clk(clk),.rst_n(rst_n),.v(v),.vd(vd));
wire rawzero,ok;wire[31:0]lo_d;
table_chain u_data(.clk(clk),.rst_n(rst_n),.nk(nk),.ok(ok),.rawzero(rawzero),.lo_d(lo_d));
assign bit30=lo_d[30];assign consumer=vd[T_R1];assign safe=!(consumer && bit30);
endmodule
'''
(r/'valid_flush.v').write_text(wrapper);(r/'valid_flush_mutant.v').write_text(wrapper.replace('consumer=vd[T_R1]','consumer=vd[0]'))
for name in ['valid_flush','valid_flush_mutant']:
 ys=f'''read_verilog -sv /out/ot_hdc_delay.sv /out/table_chain.v /out/actual_vline.sv /out/{name}.v
hierarchy -check -top valid_flush
proc
flatten
async2sync
memory_map
opt_clean
sat -seq 20 -set rst_n 1 -set-at 1 rst_n 0 -prove safe 1 -prove-skip 1 -show-inputs -show-outputs
'''
 (r/(name+'.ys')).write_text(ys)
(r/'valid_guard_receipt_source.json').write_text(json.dumps(dict(scope='Exact actual EXP valid line and table/delay cone; arbitrary nk and arbitrary valid every clock; one asserted reset edge then release; no parent64edge assumption',actual_LA=4,actual_LM=5,source=(str(src/'rtl/hdc/ot_hdc_sfu_q.sv')),vline_sha256=hashlib.sha256(m[0].encode()).hexdigest(),parameters=p,mutant='Bypass actual T_R1 valid delay to vd0'),indent=2)+'\n')

induct=wrapper.replace('assign safe=!(consumer && bit30)','assign safe=!rst_n || !(consumer && bit30)')
(r/'valid_flush_induct.v').write_text(induct)
ys=(r/'valid_flush.ys').read_text().replace('/out/valid_flush.v','/out/valid_flush_induct.v').replace('sat -seq 20','sat -tempinduct -seq 6 -maxsteps 16').replace(' -prove-skip 1','')
(r/'valid_flush_induct.ys').write_text(ys)
