`timescale 1ns/1ps
// Opt-in source-owned capture; RD64 producer has NO READY. No sum/codec/tree changes.
// VM_ALWAYS_ACCEPT=1 ONLY when actual selected VM writes every valid port on edge.
// Otherwise reserve the entire declared per-root phase BEFORE field GO.
module ot_dsrom_rd64_vm_capture #(
 parameter integer ENABLE=0, ROOTS=128, CAPACITY=1, VM_AW=19,
 parameter integer VM_ALWAYS_ACCEPT=0
)(
 // rst_n is coordinated COLD reset only: all producer/VM copies must be fenced.
 // Warm reset quarantines without clearing records or accepted debt.
 input wire clk,rst_n,input wire reset_request,
 input wire phase_valid,output wire phase_ready,
 input wire [46:0] phase_identity,input wire [9:0] phase_id,
 input wire [ROOTS*19-1:0] phase_root_rows,
 input wire [29:0] phase_obase,phase_ops,input wire [2:0] phase_np,
 input wire [1:0] phase_fmt,input wire [15:0] phase_rsplit,
 input wire phase_fp32_low,phase_fp32_high,
 // Real NOREADY root pulses and original payload/fault bits.
 input wire [ROOTS-1:0] r_valid,r_error,
 input wire [ROOTS*16-1:0] r_row,r_bf16,
 input wire [ROOTS*3-1:0] r_pos,input wire [ROOTS*32-1:0] r_fp32,
 // Captured row held through ACTUAL VM positive write acceptance.
 output wire [ROOTS-1:0] vm_valid,input wire [ROOTS-1:0] vm_accept,
 output wire [ROOTS*30-1:0] vm_addr,output wire [ROOTS*32-1:0] vm_data,
 output wire [ROOTS*16-1:0] vm_row,output wire [ROOTS*3-1:0] vm_pos,
 output wire [46:0] held_identity,output wire [9:0] held_phase,
 output wire phase_live,phase_idle,phase_drained,output wire fault
);
 localparam integer PW=(CAPACITY<=1)?1:$clog2(CAPACITY);
 localparam integer CW=$clog2(CAPACITY+1);
 reg active,sticky_fault,drained;
 reg [46:0] identity;reg [9:0] phase;
 reg [29:0] obase,ops;reg [2:0] np;reg [1:0] fmt;
 reg [15:0] rsplit;reg fp32_low,fp32_high;
 reg [18:0] expected[0:ROOTS-1],received[0:ROOTS-1],committed[0:ROOTS-1];
 reg [CW-1:0] count[0:ROOTS-1];
 reg [PW-1:0] rdptr[0:ROOTS-1],wrptr[0:ROOTS-1];
 reg [67:0] records[0:ROOTS-1][0:CAPACITY-1];
 wire [ROOTS-1:0] push,pop,invalid;
 reg reserve_ok,nonempty,all_done;
 integer k;
 always @*begin
  reserve_ok=1;nonempty=0;all_done=1;
  for(integer v=0;v<ROOTS;v=v+1)begin
   if(VM_ALWAYS_ACCEPT==0 && phase_root_rows[v*19 +:19]>CAPACITY)reserve_ok=0;
   if(phase_root_rows[v*19 +:19]!=0)nonempty=1;
   if(count[v]!=0||received[v]!=expected[v]||committed[v]!=expected[v])all_done=0;
  end
 end
 wire enabled=(ENABLE!=0)&&rst_n;
 assign phase_ready=enabled&&!reset_request&&!active&&!sticky_fault&&reserve_ok&&nonempty&&phase_fmt!=3&&!(|r_valid)&&!(|vm_accept);
 assign held_identity=identity;assign held_phase=phase;
 assign phase_live=enabled&&active;assign phase_idle=enabled&&!reset_request&&!active&&!sticky_fault;
 assign phase_drained=enabled&&!reset_request&&drained&&!sticky_fault;
 assign fault=ENABLE!=0&&(sticky_fault||reset_request||(|invalid));
 genvar g;generate for(g=0;g<ROOTS;g=g+1)begin:root_capture
  wire [67:0] head=records[g][rdptr[g]];
  wire [15:0] row=head[15:0];wire [2:0] pos=head[18:16];
  wire [31:0] data=head[50:19];wire [15:0] bf=head[66:51];
  wire [33:0] address={4'b0,obase}+{18'b0,row}+({31'b0,pos}*{4'b0,ops});
  wire range_error=(address>=(34'b1<<VM_AW));
  assign vm_valid[g]=enabled&&!reset_request&&active&&!sticky_fault&&count[g]!=0&&!head[67]&&!range_error;
  assign vm_addr[g*30 +:30]=address[29:0];
  assign vm_data[g*32 +:32]=(fmt==1||(fmt==0&&(row<rsplit?fp32_low:fp32_high)))?data:{bf,16'b0};
  assign vm_row[g*16 +:16]=row;assign vm_pos[g*3 +:3]=pos;
  assign pop[g]=vm_valid[g]&&vm_accept[g];
  assign push[g]=enabled&&!reset_request&&active&&!sticky_fault&&r_valid[g]&&(count[g]<CAPACITY||pop[g]);
  assign invalid[g]=enabled&&(
   (r_valid[g]&&(!active||sticky_fault||r_error[g]||received[g]>=expected[g]||r_pos[g*3 +:3]>np||
    (count[g]==CAPACITY&&!pop[g])))||
   (active&&count[g]!=0&&(head[67]||range_error))||
   (vm_accept[g]&&!vm_valid[g])||
   (VM_ALWAYS_ACCEPT!=0&&vm_valid[g]&&!vm_accept[g]));
 end endgenerate
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   // Authoritative coordinated cold fence proves zero accepted capture debt.
   active<=0;sticky_fault<=0;drained<=1;identity<=0;phase<=0;
   obase<=0;ops<=0;np<=0;fmt<=0;rsplit<=0;fp32_low<=0;fp32_high<=0;
   for(k=0;k<ROOTS;k=k+1)begin expected[k]<=0;received[k]<=0;committed[k]<=0;count[k]<=0;rdptr[k]<=0;wrptr[k]<=0;end
  end else if(ENABLE!=0)begin
   if(reset_request||(|invalid))sticky_fault<=1;
   if(phase_valid&&phase_ready)begin
    active<=1;drained<=0;identity<=phase_identity;phase<=phase_id;
    obase<=phase_obase;ops<=phase_ops;np<=phase_np;fmt<=phase_fmt;
    rsplit<=phase_rsplit;fp32_low<=phase_fp32_low;fp32_high<=phase_fp32_high;
    for(k=0;k<ROOTS;k=k+1)begin
     expected[k]<=phase_root_rows[k*19 +:19];received[k]<=0;committed[k]<=0;
     count[k]<=0;rdptr[k]<=0;wrptr[k]<=0;
    end
   end else if(active&&!sticky_fault&&!reset_request)begin
    for(k=0;k<ROOTS;k=k+1)begin
     case({push[k],pop[k]})
      2'b10:count[k]<=count[k]+1'b1;
      2'b01:count[k]<=count[k]-1'b1;
      default:count[k]<=count[k];
     endcase
     if(push[k])begin
      records[k][wrptr[k]]<={r_error[k],r_bf16[k*16 +:16],r_fp32[k*32 +:32],r_pos[k*3 +:3],r_row[k*16 +:16]};
      received[k]<=received[k]+1'b1;
      wrptr[k]<=(wrptr[k]==CAPACITY-1)?0:wrptr[k]+1'b1;
     end
     if(pop[k])begin
      committed[k]<=committed[k]+1'b1;
      rdptr[k]<=(rdptr[k]==CAPACITY-1)?0:rdptr[k]+1'b1;
     end
    end
    if(all_done&&!(|invalid))begin active<=0;drained<=1;end
   end
  end
 end
 initial begin
  if(ROOTS<1||ROOTS>128||CAPACITY<1||VM_AW<1||VM_AW>30)$fatal(1,"source capture geometry");
 end
endmodule
