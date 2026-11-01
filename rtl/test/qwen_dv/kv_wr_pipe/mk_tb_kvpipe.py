import sys,re
src,dst=sys.argv[1:3]
s=open(src).read()
s=s.replace('module tb_s8_memalign;','module tb_kvpipe;')
s=s.replace('qfd_dv_lane_h_safe2 #(.MEMORY_ALIGNMENT(0)) u_ref','qfd_dv_lane_h_safe2 #(.MEMORY_ALIGNMENT(3), .KV_WR_PIPE(0)) u_ref')
s=s.replace('qfd_dv_lane_h_safe2 #(.MEMORY_ALIGNMENT(3)) u_new','qfd_dv_lane_h_safe2 #(.MEMORY_ALIGNMENT(3), .KV_WR_PIPE(1)) u_new')
i=s.index('.wrom_q(wrom_q),'); s=s[:i]+'.wrom_q(wrd[1]),'+s[i+len('.wrom_q(wrom_q),'):]
i=s.index('.crom_q(crom_q),'); s=s[:i]+'.crom_q(crd[2]),'+s[i+len('.crom_q(crom_q),'):]
assert '.wrom_q(wrom_q)' not in s and s.count('.KV_WR_PIPE(')==2
s=s[:s.index('reg [87:0] op_history')]
outs=sorted(set(re.findall(r'wire\s+(?:\[\d+:0\]\s+)?ref_(\w+), new_\1;',s)))
cat=lambda p: '{'+','.join(p+o for o in outs)+'}'
s+=f'''wire [4095:0] ref_all = {cat('ref_')};
wire [4095:0] new_all = {cat('new_')};
integer cycle=0,checked=0,mismatch=0,kvw=0,kvz=0,kvsub=0,kvsat=0,kvnorm=0;
reg [31:0] rnd;
always @(posedge clk) begin crd[0]<=crom_q;crd[1]<=crd[0];crd[2]<=crd[1];wrd[0]<=wrom_q;wrd[1]<=wrd[0]; end
function automatic [31:0] rf(input [31:0] r, input [31:0] c);  // random fp32 around the fp8 subnormal..saturation range
  rf = {{r[31], 8'(8'd100 + (r[29:24] % 6'd50)), r[22:0] ^ c[22:0]}};
endfunction
always @(negedge clk) begin
 cycle=cycle+1;
 rst_n=(cycle>8);
 live=(cycle>128 && cycle%256<32);emit0=live;i=cycle%256;i_last_r=(i==31);fin_th=32;
 cura0=0;curb0=0;curc0=0;curd0=0;rrow=32;asi=1;bsi=1;csi=1;dsi=1;
 asrc=(cycle/768)%2;bsrc=(cycle/256)%2;csrc=!bsrc;mc=1;md=(cycle/512)%2;
 red=0;dst=(cycle/256)%3==2 ? 2'd1 : 2'd2;ad=0;ma=0;mb=0;cls=0;accept=0;redsq=0;imm1=32'h3f800000;imm2=0;
 rnd=$random; va_q=rf(rnd, cycle*131); rnd=$random; vb_q=rf(rnd, cycle*173); rnd=$random; vc_q=rf(rnd, cycle*197);
 crom_q={{$random,$random}};
 wrom_q={{16{{16'h3f80 | (16'(cycle)&16'h003f)}}}};
 if(cycle>8)begin
  checked=checked+1;
  if(new_all!==ref_all)begin mismatch=mismatch+1;if(mismatch<6)$display("KVPIPE mismatch cycle%0d kv ref %b %h %h new %b %h %h",cycle,ref_kv_we,ref_kv_waddr,ref_kv_wdata,new_kv_we,new_kv_waddr,new_kv_wdata);end
  if(ref_kv_we)begin kvw=kvw+1;
   if(ref_kv_wdata[30:0]==0) kvz=kvz+1; else if(ref_kv_wdata[30:23]==8'd135 && ref_kv_wdata[22:20]==3'b110) kvsat=kvsat+1;
   else if(ref_kv_wdata[30:23]<=8'd121) kvsub=kvsub+1; else kvnorm=kvnorm+1; end
 end
 if(cycle==40000)begin
  $display("KVPIPE checked=%0d kv_writes=%0d (zero %0d sub/min %0d sat %0d normal %0d) mismatches=%0d outputs_compared=%0d bits",checked,kvw,kvz,kvsub,kvsat,kvnorm,mismatch,$bits(ref_all));
  if(mismatch==0 && kvw>1000)$display("KVPIPE PASS");else $display("KVPIPE FAIL");
  $finish;
 end
end
endmodule
'''
open(dst,'w').write(s)
print(len(outs),'outputs')
