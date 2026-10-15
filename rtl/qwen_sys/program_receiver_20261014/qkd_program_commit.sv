`timescale 1ns/1ps
// Decode the exact two 64x512 SRAM write interfaces. The ledger samples this
// combinational observation on the SAME edge on which the macros consume it.
// Disabled-bank masks are immaterial; an enabled bank must write one full64 slice.
module qkd_program_pw_observer(
 input wire [1:0] macro_ce,input wire [11:0] macro_row,
 input wire [1023:0] macro_data,macro_mask,
 output wire consumed_v,output reg [9:0] consumed_addr,
 output reg [63:0] consumed_data,output reg full_word);
 integer b,s,count; reg [63:0] mask;
 assign consumed_v=|macro_ce;
 always @* begin
  consumed_addr=0;consumed_data=0;full_word=1;count=0;mask=0;
  if(macro_ce==2'b11)full_word=0;
  for(b=0;b<2;b=b+1)if(macro_ce[b])begin
   for(s=0;s<8;s=s+1)begin
    mask=macro_mask[512*b+64*s +:64];
    if(mask!=0)begin
     count=count+1;
     if(mask!=64'hffffffffffffffff)full_word=0;
     consumed_addr={macro_row[6*b +:6],1'(b),3'(s)};
     consumed_data=macro_data[512*b+64*s +:64];
    end
   end
  end
  if(count!=1)full_word=0;
 end
endmodule

// Dense receiver profile: exactly1024 PW followed8 DW, all full64 writes.
// begin/auth metadata arrives independently through the actual authorized
// transport. No digest, epoch, write or completion is inferred from host time.
// There is no ready output on the program write path and no schedule stall.
module qkd_program_commit(
 input wire ck,rst_n,execution_active,control_stores_ready,
 input wire begin_v,input wire[15:0]begin_epoch,
 input wire[10:0]expected_pw,input wire[3:0]expected_dw,
 input wire auth_v,input wire[15:0]auth_epoch,input wire[63:0]auth_digest,
 input wire pw_v,input wire[9:0]pw_addr,input wire[63:0]pw_data,input wire pw_full_word,
 input wire dw_v,input wire[2:0]dw_addr,input wire[63:0]dw_data,input wire dw_full_word,
 output reg commit_v,ready,fault,installed_fusedcap,output reg[15:0]commit_epoch,
 output reg[63:0]commit_digest);
 localparam IDLE=0,WAIT_AUTH=1,WRITES=2,VERIFIED=3,READY=4;
 reg[2:0]state;reg footer_cap;reg[10:0]count;reg[15:0]epoch;
 reg[63:0]digest,authorized_digest;
 wire event_desc=dw_v;
 wire[9:0]event_addr=dw_v?{7'd0,dw_addr}:pw_addr;
 wire[63:0]event_data=dw_v?dw_data:pw_data;
 wire[63:0]next_digest={digest[56:0],digest[63:57]}^event_data^{53'd0,event_desc,event_addr};
 wire bad_write=(pw_v&&dw_v)||(pw_v&&(!pw_full_word||count>=1024||{1'b0,pw_addr}!=count))
  ||(dw_v&&(!dw_full_word||count<1024||count>=1032||{8'd0,dw_addr}!=count-11'd1024));
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin state<=IDLE;count<=0;epoch<=0;digest<=0;authorized_digest<=0;
   commit_v<=0;ready<=0;fault<=0;installed_fusedcap<=0;footer_cap<=0;commit_epoch<=0;commit_digest<=0;end
  else begin
   commit_v<=0;
   if(!fault)begin
    if(begin_v)begin
     ready<=0;installed_fusedcap<=0;footer_cap<=0;
     if(execution_active||state==WAIT_AUTH||state==WRITES||state==VERIFIED||auth_v||pw_v||dw_v||expected_pw!=1024||expected_dw!=8)begin fault<=1;installed_fusedcap<=0;state<=IDLE;end
     else begin state<=WAIT_AUTH;epoch<=begin_epoch;count<=0;digest<=64'h51484f5354505247;end
    end else if(auth_v)begin
     if(execution_active||state!=WAIT_AUTH||auth_epoch!=epoch||pw_v||dw_v)begin fault<=1;installed_fusedcap<=0;ready<=0;state<=IDLE;end
     else begin authorized_digest<=auth_digest;state<=WRITES;end
    end else if(pw_v||dw_v)begin
     if(execution_active||state!=WRITES||bad_write)begin fault<=1;installed_fusedcap<=0;ready<=0;state<=IDLE;end
     else begin
      count<=count+1'b1;digest<=next_digest;
      if(pw_v&&pw_addr==1023)footer_cap<=pw_data[63:32]==32'h58504631&&pw_data[1:0]==2&&pw_data[31:13]==0&&pw_data[5:2]>=1&&pw_data[5:2]<=4&&pw_data[12];
      if(count==1031)begin
       if(next_digest!=authorized_digest)begin fault<=1;installed_fusedcap<=0;ready<=0;state<=IDLE;end
       else begin commit_epoch<=epoch;commit_digest<=next_digest;state<=VERIFIED;end
      end
     end
    end
   end else ready<=0;
   if(!fault&&state==VERIFIED&&!begin_v&&!auth_v&&!pw_v&&!dw_v)begin
    if(control_stores_ready)begin commit_v<=1;ready<=1;installed_fusedcap<=footer_cap;state<=READY;end
   end
   if(fault)installed_fusedcap<=0;
  end
 end
endmodule

// Join independently observed physical program copies. Every participating copy
// has its own ledger; a source-side receipt cannot stand in for a sink. All pins
// here must already be synchronous to ck (clock crossing belongs to the route).
module qkd_program_commit_join #(parameter integer SINKS=2)(
 input wire ck,rst_n,begin_v,auth_v,execution_active,control_stores_ready,
 input wire[15:0]auth_epoch,input wire[63:0]auth_digest,
 input wire[SINKS-1:0]sink_ready,sink_fault,sink_fusedcap,
 input wire[16*SINKS-1:0]sink_epoch,input wire[64*SINKS-1:0]sink_digest,
 output reg commit_v,ready,fault,installed_fusedcap,
 output reg[15:0]commit_epoch,output reg[63:0]commit_digest);
 reg armed,complete,begin_pending;reg[15:0]epoch;reg[63:0]digest;
 reg[SINKS-1:0]seen_empty;reg mismatch;integer i;
 always @*begin
  mismatch=0;
  for(i=0;i<SINKS;i=i+1)if(sink_ready[i]&&seen_empty[i])
   mismatch=mismatch||(sink_epoch[16*i+:16]!=epoch)||(sink_digest[64*i+:64]!=digest);
 end
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin commit_v<=0;ready<=0;fault<=0;installed_fusedcap<=0;
   commit_epoch<=0;commit_digest<=0;armed<=0;complete<=0;begin_pending<=0;seen_empty<=0;epoch<=0;digest<=0;end
  else begin
   commit_v<=0;
   if(!fault)begin
    if(begin_v)begin
     ready<=0;installed_fusedcap<=0;armed<=0;complete<=0;begin_pending<=1;seen_empty<=0;
     if(execution_active||auth_v||armed||begin_pending)fault<=1;
    end else begin
     seen_empty<=seen_empty|~sink_ready;
     if(auth_v)begin
      if(execution_active||armed||complete||!begin_pending)begin fault<=1;ready<=0;installed_fusedcap<=0;end
      else begin armed<=1;begin_pending<=0;epoch<=auth_epoch;digest<=auth_digest;end
     end
     // A completed receipt is valid only while all actual sinks retain it.
     // A lost seal revokes it without re-arming; only fresh BEGIN/AUTH can install.
     if(complete&&(!(&sink_ready)||!control_stores_ready||installed_fusedcap!=(&sink_fusedcap)))begin
      ready<=0;installed_fusedcap<=0;if(execution_active)fault<=1;
     end
     if((|sink_fault)||((armed||complete)&&mismatch))begin fault<=1;ready<=0;installed_fusedcap<=0;armed<=0;end
     else if(armed&&(&seen_empty)&&(&sink_ready)&&control_stores_ready&&!auth_v)begin
      commit_v<=1;ready<=1;installed_fusedcap<=&sink_fusedcap;
      commit_epoch<=epoch;commit_digest<=digest;armed<=0;complete<=1;
     end
    end
   end
  end
 end
endmodule
