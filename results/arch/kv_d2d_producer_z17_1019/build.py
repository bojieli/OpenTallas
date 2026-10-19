from pathlib import Path
import re, hashlib,json
R=Path(__file__).resolve().parents[3]; O=Path(__file__).resolve().parent
src=R/'rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_dies.sv'; text=src.read_text(); original=text[text.index('module qkd_d2d_static #'):]; assert original.endswith('endmodule\n')
clone=original.replace('module qkd_d2d_static #','module qkd_d2d_static_z17 #',1).replace('parameter integer MUT = 0,','parameter integer Z17 = 0, parameter integer MUT = 0,',1).replace('    input  wire ck,','    output wire [16:0] rx_zero17,\n    input  wire ck,',1)
block='''    // PRIVATE Z17: same producer capture as q_rx_payload; deliberately no reset/enable.
    generate if (Z17 && PR) begin : g_z17
        reg [16:0] q_zero17;
        integer z;
        always @(posedge ck) begin
            q_zero17[0] <= |c_rx_payload[31:19];
            q_zero17[1] <= |c_rx_payload[31:5];
            for (z=1; z<=15; z=z+1)
                q_zero17[z+1] <= |c_rx_payload[32*z +: 32];
        end
        assign rx_zero17 = q_zero17;
    end else begin : g_no_z17
        assign rx_zero17 = 17'b0;
    end endgenerate
'''
clone=clone.replace('    assign rx_payload = PR ? q_rx_payload : c_rx_payload;','    assign rx_payload = PR ? q_rx_payload : c_rx_payload;\n'+block,1)
recover=clone.replace(block,'').replace('    assign rx_payload = PR ? q_rx_payload : c_rx_payload;\n\n','    assign rx_payload = PR ? q_rx_payload : c_rx_payload;\n',1).replace('module qkd_d2d_static_z17 #','module qkd_d2d_static #',1).replace('parameter integer Z17 = 0, ','',1).replace('    output wire [16:0] rx_zero17,\n','',1)
assert recover==original
(R/'rtl/qwen_sys/d2d_static_20261015/qkd_d2d_static_z17.sv').write_text('`timescale 1ns/1ps\n'+clone)
header=original[:original.index(');')]; ports=[]
for direction,width,name in re.findall(r'\b(input|output)\s+wire\s*(\[[^\]]+\])?\s*(\w+)',header): ports.append((direction,width,name))
outs=[p for p in ports if p[0]=='output']; bench=(R/'rtl/test/qwen_split/tb_qwen_d2d_dies.sv').read_text(); inst=re.search(r'    qkd_d2d_static #.*?\n.*?\.fault\(k_f\)\);',bench,re.S).group()
extra='\n'; checks=[]
for mode in (0,1):
    shadow=inst.replace('qkd_d2d_static #(','qkd_d2d_static_z17 #(.Z17(%d), '%mode,1).replace(' u_k (',' u_z%d ('%mode,1)
    for _,width,name in outs:
        width=width.replace('NL','2'); wire=f'z{mode}_{name}'; extra+=f'wire {width} {wire};\n'; shadow=re.sub(r'\.'+name+r'\([^)]*\)',f'.{name}({wire})',shadow)
        checks.append(f'if (u_k.{name} !== {wire}) $fatal(1,"Z17_EQ_FAIL mode{mode} {name} cycle%0d",cyc);')
    extra+=f'wire [16:0] pred{mode};\n'+shadow.replace('.ck(ck)',f'.rx_zero17(pred{mode}), .ck(ck)',1)+'\n'
extra+='always @(negedge ck) begin\n'+'\n'.join(checks)+'\nend\n'
extra+='''reg [16:0] expected; integer zi; integer checked=0;
always @(posedge ck) begin
    expected[0] = |u_z1.c_rx_payload[31:19];
    expected[1] = |u_z1.c_rx_payload[31:5];
    for(zi=1;zi<=15;zi=zi+1) expected[zi+1]=|u_z1.c_rx_payload[32*zi+:32];
    #0.01;
    if(pred1 !== (PR ? expected : 17'd0)) $fatal(1,"Z17_PRED_FAIL cycle%0d",cyc);
    if(pred0 !== 17'd0) $fatal(1,"Z17_DEFAULT_FAIL");
    checked=checked+1;
end
final $display("Z17_EQ_PRED_PASS edges=%0d outputs=52 modes=2 PR=%0d",checked,PR);
'''
bench=bench.replace('endmodule',extra+'\nendmodule'); (O/'tb_z17_equiv.sv').write_text(bench)
# Boundary oracle exercises every included/excluded bit during reset and active state.
decl='module tb_z17_boundary; reg ck=0; always #1 ck=~ck; reg rst_n=0; reg [547:0] stimulus; wire [16:0] z;\n'
con=[]
for d,w,n in ports:
    con.append('.%s(%s)'%(n, n if n in ('ck','rst_n') else ("'0" if d=='input' else '')))
decl+='qkd_d2d_static_z17 #(.Z17(1), .TXDP(32\'h03030403)) dut('+','.join(con)+',.rx_zero17(z));\n'
decl+='''reg [16:0] expect_z; integer b,j,phase;
initial begin
force dut.c_rx_payload=stimulus;
for(phase=0;phase<2;phase=phase+1) begin
rst_n=phase;
for(b=-1;b<548;b=b+1) begin
@(negedge ck); stimulus=0; if(b>=0) stimulus[b]=1;
expect_z[0]=|stimulus[31:19]; expect_z[1]=|stimulus[31:5];
for(j=1;j<=15;j=j+1) expect_z[j+1]=|stimulus[32*j+:32];
@(posedge ck); #0.01;
if(z !== expect_z || dut.q_rx_payload !== stimulus) $fatal(1,"Z17_BOUNDARY_FAIL reset%0d bit%0d",phase,b);
end end
$display("Z17_BOUNDARY_PASS vectors=1098 reset_and_active=1"); $finish;
end endmodule
'''; (O/'tb_z17_boundary.sv').write_text(decl)
(O/'constructor.json').write_text(json.dumps({'selected_sha256':hashlib.sha256(text.encode()).hexdigest(),'clone_recovery_exact':True,'original_output_ports':len(outs),'ports':ports,'scope':'Private module clone only; public source unchanged; 17 FF at PR producer edge; reset/startup authority remains open'},indent=2)+'\n')
