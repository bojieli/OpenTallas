`timescale 1ns/1ps
// Actual CDC and registered reduction of independently exported HOST debt.
// Source quiet pins are observations, never native issue enables. They must be
// held stable after admission closes for the compiler-priced drain interval.
// Each quiet source has two capture flops; then PC, 8-PC group, and root flops.
// Worst observation age: 5 ck edges from source pin, plus source export age.
module qkd_host_native_quiet(
 input wire ck,rst_n,
 input wire[127:0]station_quiet,queue_quiet,boot_quiet,
 input wire[5:0]upstream_quiet,input wire admission_quiet,source_fault,
 output reg host_quiet
);
 (* async_reg="true" *)reg[383:0]quiet_meta,quiet_sync;
 (* async_reg="true" *)reg[5:0]upstream_meta,upstream_sync;
 (* async_reg="true" *)reg[1:0]admission_sync,fault_sync;
 reg[127:0]pc_quiet;reg[15:0]group_quiet;
 genvar p,g;
 generate for(p=0;p<128;p=p+1)begin:G_PC
  always @(posedge ck or negedge rst_n)
   if(!rst_n)pc_quiet[p]<=0;
   else pc_quiet[p]<=quiet_sync[p]&&quiet_sync[128+p]&&quiet_sync[256+p];
 end
 for(g=0;g<16;g=g+1)begin:G_GROUP
  always @(posedge ck or negedge rst_n)
   if(!rst_n)group_quiet[g]<=0;
   else group_quiet[g]<=&pc_quiet[g*8+:8];
 end endgenerate
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin quiet_meta<=0;quiet_sync<=0;upstream_meta<=0;upstream_sync<=0;admission_sync<=0;fault_sync<=0;host_quiet<=0;end
  else begin
   quiet_meta<={boot_quiet,queue_quiet,station_quiet};quiet_sync<=quiet_meta;
   upstream_meta<=upstream_quiet;upstream_sync<=upstream_meta;
   admission_sync<={admission_sync[0],admission_quiet};fault_sync<={fault_sync[0],source_fault};
   host_quiet<=(&group_quiet)&&(&upstream_sync)&&admission_sync[1]&&!fault_sync[1];
  end
 end
endmodule
