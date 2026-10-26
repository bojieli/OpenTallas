`timescale 1ns/1ps
// Consumer non-interference proof. Two complete sets of the 32 actual v15 VM
// banks receive equal valid writes and independent invalid payload/address/masks.
// Reads use the real SRAM/SECDED paths after a reset which preserves memory.
module tb_vm_delivery_invalid_payload;
parameter integer MUT=0;
reg clk=0;always #5 clk=~clk;
reg rst_n=0,do_write=0,do_read=0;
integer row=0,cyc=0,reads=0,writes=0,checks=0,invalid_samples=0;
reg [279:0] noise_a[0:3][0:7],noise_b[0:3][0:7];
wire [256:0] rr_a[0:3][0:7],rr_b[0:3][0:7];
wire [17:0] status_a[0:3][0:7],status_b[0:3][0:7];
wire done_a[0:3][0:7],done_b[0:3][0:7];
integer read_count[0:3][0:7],write_count[0:3][0:7];
function automatic [255:0] pattern(input integer q,input integer b,input integer r);
 for(integer k=0;k<8;k=k+1)pattern[k*32+:32]=32'h9e3779b9*(q*8192+b*1024+r*8+k+1);
endfunction
function automatic [15:0] sector(input integer q,input integer b,input integer r);
 sector={1'b0,2'(q),10'(r),3'(b)};
endfunction
for(genvar q=0;q<4;q=q+1)begin:Q
 for(genvar b=0;b<8;b=b+1)begin:B
  localparam RG=q==0?5:q==1?4:6,WG=q<2?1:3;
  wire [280:0] dq_a=do_write?{1'b1,sector(q,b,row),pattern(q,b,row),8'hff}:{1'b0,noise_a[q][b]};
  wire [280:0] dq_b=do_write?(dq_a^((MUT==1&&q==0&&b==0)?281'h100:281'd0)):
      {(MUT==2&&q==0&&b==0),noise_b[q][b]};
  wire [RG*17-1:0] rq={{(RG-1)*17{1'b0}},do_read,sector(q,b,row)};
  wire [RG*257-1:0] resp_a,resp_b;
  assign rr_a[q][b]=resp_a[256:0];assign rr_b[q][b]=resp_b[256:0];
  ot_vms_bank_static #(.RG(RG),.WG(WG)) a(.clk(clk),.rst_n(rst_n),.bid(3'(b)),.sid(2'(q)),
   .rslot_v(do_read),.rslot(3'd0),.wslot_v(1'b1),.wslot(3'(WG+4)),.rq(rq),.rr(resp_a),
   .wq({WG*281{1'b0}}),.wq_done(),.dq(dq_a),.dq_done(done_a[q][b]),.kq(281'd0),.kq_done(),
   .xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),.eg(),.pq(285'd0),.pr(),.status(status_a[q][b]));
  ot_vms_bank_static #(.RG(RG),.WG(WG)) b_dut(.clk(clk),.rst_n(rst_n),.bid(3'(b)),.sid(2'(q)),
   .rslot_v(do_read),.rslot(3'd0),.wslot_v(1'b1),.wslot(3'(WG+4)),.rq(rq),.rr(resp_b),
   .wq({WG*281{1'b0}}),.wq_done(),.dq(dq_b),.dq_done(done_b[q][b]),.kq(281'd0),.kq_done(),
   .xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),.eg(),.pq(285'd0),.pr(),.status(status_b[q][b]));
 end
end
always @(posedge clk)begin
 #1;
 if(rst_n)for(integer q=0;q<4;q=q+1)for(integer b=0;b<8;b=b+1)begin
  checks=checks+1;
  if(status_a[q][b]!==0||status_b[q][b]!==0||rr_a[q][b]!==rr_b[q][b]||done_a[q][b]!==done_b[q][b])
   $fatal(1,"VM_INVALID_DQ mismatch cycle=%0d q=%0d b=%0d status=%h/%h",cyc,q,b,status_a[q][b],status_b[q][b]);
  if(done_a[q][b])begin writes=writes+1;write_count[q][b]=write_count[q][b]+1;end
  if(rr_a[q][b][256])begin
   if(rr_a[q][b][255:0]!==pattern(q,b,read_count[q][b]))$fatal(1,"VM_INVALID_DQ expected data mismatch q=%0d b=%0d row=%0d",q,b,read_count[q][b]);
   reads=reads+1;read_count[q][b]=read_count[q][b]+1;
  end
 end
end
task automatic tick;
 begin
  for(integer q=0;q<4;q=q+1)for(integer b=0;b<8;b=b+1)begin
   for(integer w=0;w<9;w=w+1)begin
    noise_a[q][b][w*31+:31]=$random;
    noise_b[q][b][w*31+:31]=$random;
   end
   noise_a[q][b][279]=$random;noise_b[q][b][279]=$random;
   if(!do_write)invalid_samples=invalid_samples+1;
  end
  @(negedge clk);cyc=cyc+1;
 end
endtask
initial begin
 for(integer q=0;q<4;q=q+1)for(integer b=0;b<8;b=b+1)begin read_count[q][b]=0;write_count[q][b]=0;noise_a[q][b]=0;noise_b[q][b]=0;end
 repeat(3)tick();rst_n=1;repeat(8)tick();
 for(integer r=0;r<128;r=r+1)begin row=r;do_write=1;tick();do_write=0;repeat(3)tick();end
 repeat(10)tick();rst_n=0;repeat(3)tick();rst_n=1;repeat(8)tick();
 for(integer r=0;r<128;r=r+1)begin row=r;do_read=1;tick();end
 do_read=0;repeat(10)tick();
 for(integer q=0;q<4;q=q+1)for(integer b=0;b<8;b=b+1)
  if(read_count[q][b]!=128||write_count[q][b]!=128)$fatal(1,"VM_INVALID_DQ vacuous bank q=%0d b=%0d r=%0d w=%0d",q,b,read_count[q][b],write_count[q][b]);
 $display("VM_INVALID_DQ PASS checks=%0d writes=%0d reads=%0d invalid_samples=%0d banks=64 real_srams=192",checks,writes,reads,invalid_samples);$finish;
end
endmodule
