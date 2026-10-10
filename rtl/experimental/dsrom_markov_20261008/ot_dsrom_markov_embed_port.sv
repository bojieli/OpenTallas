// Opt-in MD6 component. Macro q is real paired 4096x274 payload q;
// 18 unused bits are not ECC. Fault-free ROM contract. No head integration claim.
module ot_dsrom_markov_embed_port #(
 parameter bit ENABLE=0, parameter integer ID_W=32
)(input wire clk, rst_n,
 input wire req_valid, output wire req_ready, input wire [16:0] req_token,
 input wire [ID_W-1:0] req_id,
 output reg fault_valid, output reg [ID_W-1:0] fault_id,
 output reg [252:0] bank_re, output reg [16*13-1:0] bank_addr,
 input wire [253*256-1:0] bank_q,
 output wire out_valid,input wire out_ready,output wire [255:0] out_data,
 output wire [ID_W-1:0] out_id,output wire [3:0] out_beat,output wire out_last);
 reg busy; reg [16:0] token; reg [ID_W-1:0] identity;
 reg [4:0] next_beat; reg [3:0] reserved,count;
 reg [2:0] wp,rp;
 reg [255:0] fifo_data[0:7];reg [3:0] fifo_beat[0:7];
 reg [4:0] v;
 reg [7:0] bank_pipe[0:4];reg [3:0] beat_pipe[0:4];
 reg [255:0] capture[0:252];reg [255:0] group_q[0:15];reg [255:0] final_q;
 wire issue=ENABLE && busy && next_beat<16 && reserved<8;
 wire take=out_valid&&out_ready;
 wire [20:0] address={token,next_beat[3:0]};
 wire [7:0] selected_bank=address[20:13];
 assign req_ready=ENABLE&&!busy;
 assign out_valid=count!=0;assign out_data=fifo_data[rp];
 assign out_beat=fifo_beat[rp];assign out_last=out_beat==15;
 assign out_id=identity;
 integer i,g,b;
 always @(posedge clk) begin
  if(!rst_n) begin
   busy<=0;token<=0;identity<=0;next_beat<=0;reserved<=0;count<=0;wp<=0;rp<=0;v<=0;
   bank_re<=0;bank_addr<=0;fault_valid<=0;fault_id<=0;
  end else begin
   fault_valid<=0; bank_re<=0;
   if(req_valid&&req_ready) begin
    if(req_token>=129280) begin fault_valid<=1;fault_id<=req_id;end
    else begin busy<=1;token<=req_token;identity<=req_id;next_beat<=0;end
   end
   if(issue) begin
    bank_re[selected_bank]<=1;
    for(g=0;g<16;g=g+1) bank_addr[g*13+:13]<=address[12:0];
    next_beat<=next_beat+1;
   end
   // v[0]: registered request at macro pins; v[1]: macro q now available;
   // v[2]: capture registers; v[3]: group-select registers; v[4]: final register.
   v<={v[3:0],issue};bank_pipe[0]<=selected_bank;beat_pipe[0]<=next_beat[3:0];
   for(i=1;i<5;i=i+1) begin bank_pipe[i]<=bank_pipe[i-1];beat_pipe[i]<=beat_pipe[i-1];end
   if(v[1]) for(b=0;b<253;b=b+1) capture[b]<=bank_q[b*256+:256];
   if(v[2]) for(g=0;g<16;g=g+1) begin
    group_q[g]<=0;
    for(b=0;b<16;b=b+1) if(g*16+b<253 && bank_pipe[2][3:0]==b)
      group_q[g]<=capture[g*16+b];
   end
   if(v[3]) final_q<=group_q[bank_pipe[3][7:4]];
   if(v[4]) begin fifo_data[wp]<=final_q;fifo_beat[wp]<=beat_pipe[4];wp<=wp+1;end
   if(take) begin rp<=rp+1;if(out_last) busy<=0;end
   case({issue,take}) 2'b10:reserved<=reserved+1;2'b01:reserved<=reserved-1;default:;endcase
   case({v[4],take}) 2'b10:count<=count+1;2'b01:count<=count-1;default:;endcase
  end
 end
endmodule

// Full-shape binding: 253 pairs, two real 4096x274 hard macros per pair.
// Macro images are named macro000..macro505.viamap.hex under OT_ROM_DIR.
module ot_dsrom_markov_embed_rom #(
 parameter bit ENABLE=0,parameter integer ID_W=32
)(input wire clk,rst_n,input wire req_valid,output wire req_ready,
 input wire[16:0] req_token,input wire[ID_W-1:0] req_id,
 output wire fault_valid,output wire[ID_W-1:0] fault_id,
 output wire out_valid,input wire out_ready,output wire[255:0] out_data,
 output wire[ID_W-1:0] out_id,output wire[3:0] out_beat,output wire out_last);
 wire[252:0] bank_re;wire[207:0] bank_addr;wire[64767:0] bank_q;
 ot_dsrom_markov_embed_port #(.ENABLE(ENABLE),.ID_W(ID_W)) port(.*);
 for(genvar b=0;b<253;b=b+1)begin:banks
  wire[12:0] a=bank_addr[(b/16)*13+:13];
  wire[273:0] q0,q1;reg sel;
  always @(posedge clk) if(bank_re[b]) sel<=a[12];
`ifdef SYNTHESIS
  ot_rom_4096x274_m8 m0(.clk(clk),.ce_in(bank_re[b]&&!a[12]),.addr_in(a[11:0]),.rd_out(q0));
  ot_rom_4096x274_m8 m1(.clk(clk),.ce_in(bank_re[b]&&a[12]),.addr_in(a[11:0]),.rd_out(q1));
`else
  ot_rom_4096x274_m8 #(.INSTANCE($sformatf("macro%03d",2*b))) m0(.clk(clk),.ce_in(bank_re[b]&&!a[12]),.addr_in(a[11:0]),.rd_out(q0));
  ot_rom_4096x274_m8 #(.INSTANCE($sformatf("macro%03d",2*b+1))) m1(.clk(clk),.ce_in(bank_re[b]&&a[12]),.addr_in(a[11:0]),.rd_out(q1));
`endif
  assign bank_q[b*256+:256]=sel?q1[255:0]:q0[255:0];
 end
endmodule
