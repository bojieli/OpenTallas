`default_nettype none
// One quadrant's eight dq banks. Compiler allocation, not response arbitration:
// sector = base + slot*32 + group*8 + bank. Base is aligned32 and the entire
// 2048-sector block remains in one main sid aperture (or one local mirror).
// start reserves 256 consecutive SRAM read slots; dq appears after each read
// edge. The VM samples dq on its following edge and commits three edges later.
module ot_hbm_svc_static_vm_delivery (
 input wire clk,rst_n,begin_v,begin_bank,input wire [15:0] begin_epoch,
 input wire [31:0] fill_v,fill_bank,input wire [191:0] fill_slot,
 input wire [511:0] fill_epoch,input wire [8191:0] fill_data,
 output wire [1:0] block_ready,
 input wire start,start_bank,input wire [15:0] start_epoch,start_base_sector,
 output wire [2247:0] dq,output wire busy,output wire fault
);
 reg [15:0] base_q;reg bad;
 wire aperture_ok=start_base_sector[4:0]==0 && start_base_sector[12:0]<=13'd6144 &&
                   (!start_base_sector[15] || start_base_sector[14:13]==0);
 wire ov,ob,landing_fault;wire [5:0] slot;wire [1:0] grp;
 wire [15:0] oe;wire [2047:0] data;
 assign fault=bad||landing_fault;
 always @(posedge clk or negedge rst_n)if(!rst_n)begin base_q<=0;bad<=0;end
 else if(start)begin
  if(!aperture_ok || busy)bad<=1;
  else base_q<=start_base_sector;
 end
 ot_hbm_svc_static_landing #(.READ_GROUPS(4)) u_landing (
 .clk(clk),.rst_n(rst_n),.begin_v(begin_v),.begin_bank(begin_bank),.begin_epoch(begin_epoch),
 .fill_v(fill_v),.fill_bank(fill_bank),.fill_slot(fill_slot),.fill_epoch(fill_epoch),.fill_data(fill_data),
 .block_ready(block_ready),.start(start && aperture_ok && !bad),.start_bank(start_bank),.start_epoch(start_epoch),
 .out_v(ov),.out_bank(ob),.out_slot(slot),.out_group(grp),.out_epoch(oe),.out_data(data),.busy(busy),.fault(landing_fault));
 genvar b;generate for(b=0;b<8;b=b+1)begin:bank
  wire [15:0] sector=base_q+{5'b0,slot,grp,3'b0}+b;
  assign dq[b*281+:281]={ov && !fault,sector,data[b*256+:256],8'hff};
 end endgenerate
endmodule
`default_nettype wire
