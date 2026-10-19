#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,re,subprocess
R=Path(__file__).resolve().parents[5]; O=Path(__file__).resolve().parent
rel='rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_att.sv'
old=subprocess.check_output(['git','-C',str(R),'show','53ccd5927:'+rel]).decode()
new=(R/rel).read_text()
assert 'parameter bit QMEM_SRAM = 0' in new
# Restore only packaging edits and demand full token-equivalent original source.
s=new.replace('parameter bit SRAM_MACRO = 0,\n    parameter bit QMEM_SRAM = 0                // opt-in: native 8x32x64, same capture edge','parameter bit SRAM_MACRO = 0')
s=s.replace('// QMEM_SRAM does not alter parser, GO, q_have or engine valid ages.','reg [D*16-1:0] qmem [0:H-1];')
s=s.replace('reg ej_v; reg eq_v; wire [D*16-1:0] eq_w;','reg ej_v; reg eq_v; reg [D*16-1:0] eq_w;')
a=s.index('    generate if (QMEM_SRAM)');b=s.index('    // ------------------------------------------------------------------ p store (SVCB:',a)
branch=s[a:b];s=s[:a]+s[b:]
s=s.replace('// q store\n\n','// q store\n        if (q_word) qmem[{f_hdr[448], f_idx[6:4]}] <= q_d;\n')
s=s.replace('// engine program inputs\n\n',"// engine program inputs\n        eq_w <= qmem[4'(rc - 10'd1)];\n")
def toks(x): return re.findall(r"[A-Za-z_$][A-Za-z0-9_$]*|[0-9]+|[^\s]",re.sub(r'//[^\n]*','',x))
assert toks(s)==toks(old),'default projection differs'
olddecl='    reg [D*16-1:0] qmem [0:H-1];'
oldwr='        if (q_word) qmem[{f_hdr[448], f_idx[6:4]}] <= q_d;'
oldrd="        eq_w <= qmem[4'(rc - 10'd1)];"
for x in (olddecl,oldwr,oldrd): assert x in old
ports='(input wire clk,q_word,input wire [511:0] f_hdr,q_d,input wire [11:0] f_idx,input wire [9:0] rc,output wire [511:0] eq_w);\n localparam integer D=32,H=16;\n'
body=branch.split('end else begin : g_qmem_legacy')[1].split('    end endgenerate')[0]
(O/'legacy_vehicle.sv').write_text('module legacy_vehicle '+ports+body+'endmodule\n')
(O/'reference_vehicle.sv').write_text('module reference_vehicle '+ports+olddecl+'\n reg [511:0] cap;\n always @(posedge clk) begin\n'+oldwr+'\n'+oldrd.replace('eq_w <=','cap <=')+'\n end\n assign eq_w=cap;\nendmodule\n')
src=(R/'rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_qmem8.sv').read_text()
variants=[]
for i in range(6):
 t=src.replace('module dsdv_svc_qmem8 (',f'module candidate_{i} (')
 if i==1:t=t.replace("{1'b0,rd_head}","{1'b0,4'(rd_head+4'd1)}")
 if i==2:t=t.replace("{1'b0,rd_head}","{1'b0,4'(rd_head-4'd1)}")
 if i==3:
  t=t.replace('    genvar b;','    wire [511:0] native_data;\n    reg [511:0] delayed;\n    always @(posedge clk) delayed <= native_data;\n    assign rd_data=delayed;\n    genvar b;').replace('.rd_out(rd_data[','.rd_out(native_data[')
 if i==4:
  t=t.replace('    genvar b;','    wire [511:0] native_data;\n    reg collision; reg [511:0] new_data;\n    always @(posedge clk) begin collision <= wr_v && wr_head==rd_head; new_data<=wr_data; end\n    assign rd_data=collision ? new_data : native_data;\n    genvar b;').replace('.rd_out(rd_data[','.rd_out(native_data[')
 if i==5:t=t.replace("{1'b0,wr_head}","{1'b0,4'(wr_head+4'd1)}")
 variants.append(t)
(O/'candidate_variants.sv').write_text('\n'.join(variants))
manifest=dict(parent_revision='53ccd5927',parent_sha256=hashlib.sha256(old.encode()).hexdigest(),default_projection='PASS_FULL_TOKEN_IDENTITY',legacy_assignment_bytes=[olddecl,oldwr,oldrd],native_revision='b65718325',native_sha256=hashlib.sha256((O/'native/ot_sram_1r1w_32x64_m1.v').read_bytes()).hexdigest(),mutants={'1':'wrong-head +1','2':'early/previous head -1','3':'extra capture edge','4':'same-address NEW bypass','5':'wrong write head +1'})
(O/'source_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('DEFAULT_PROJECTION_PASS and literal legacy assignment bytes preserved')

# Additional minimal source controller: retain q_have, GO admission and q valid/rc age.
fragments=["if (q_word && !start) q_have <= q_have + 1'b1;", "run <= 1'b1; rc <= 10'd1;", "eq_v <= rc <= 10'd16;", "rc <= rc + 1'b1;", "if (q_have != 5'd16) fc[9] <= 1'b1;", "if (rc >= 10'd16 && rc >= nbeat) run <= 1'b0;"]
for x in fragments: assert x in old,x
(O/'controller_vehicle.sv').write_text("""module controller_vehicle(input wire clk,rst_n,start,q_word,go,output reg eq_v,output reg [9:0] rc,output reg [4:0] q_have,output reg run,output reg [31:0] fc);
localparam [9:0] nbeat=0;
always @(posedge clk or negedge rst_n) begin
 if (!rst_n) begin q_have<=0; run<=0; rc<=0; eq_v<=0; fc<=0; end
 else begin
  if(start) q_have<=0;
  if (q_word && !start) q_have <= q_have + 1'b1;
  eq_v<=0;
  if(go) begin
   run <= 1'b1; rc <= 10'd1;
   if (q_have != 5'd16) fc[9] <= 1'b1;
  end else if(run) begin
   eq_v <= rc <= 10'd16;
   if (rc >= 10'd16 && rc >= nbeat) run <= 1'b0;
   rc <= rc + 1'b1;
  end
 end
end
endmodule
""")
