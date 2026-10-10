`default_nettype none
module ot_hbm_loader_service_boundary #(parameter integer ENABLE=0,ENABLE_NATIVE_BURST=0,NPC=32)(
 input wire clk,rst_n,input wire [NPC-1:0] normal_pending_write,
 input wire [NPC-1:0] normal_v,output wire [NPC-1:0] normal_rdy,input wire [NPC-1:0] normal_we,
 input wire [NPC*30-1:0] normal_addr,input wire [NPC*4-1:0] normal_len,input wire [NPC*17-1:0] normal_tag,
 input wire [NPC*256-1:0] normal_wdata,input wire [NPC*32-1:0] normal_wstrb,
 output wire [NPC-1:0] normal_rsp_v,input wire [NPC-1:0] normal_rsp_rdy,output wire [NPC*17-1:0] normal_rsp_tag,
 output wire [NPC*4-1:0] normal_rsp_beat,output wire [NPC*256-1:0] normal_rsp_data,
 input wire native_v,output wire native_rdy,input wire [4:0] native_pc,input wire [29:0] native_addr,input wire [15:0] native_tag,input wire [3:0] native_len,
 output wire native_rsp_v,input wire native_rsp_rdy,output wire [4:0] native_rsp_pc,output wire [15:0] native_rsp_tag,
 output wire [3:0] native_rsp_beat,output wire [255:0] native_rsp_data,
 output wire [NPC-1:0] k_v,input wire [NPC-1:0] k_rdy,output wire [NPC-1:0] k_we,output wire [NPC*30-1:0] k_addr,
 output wire [NPC*4-1:0] k_len,output wire [NPC*17-1:0] k_tag,output wire [NPC*256-1:0] k_wdata,output wire [NPC*32-1:0] k_wstrb,
 input wire [NPC-1:0] kr_v,output wire [NPC-1:0] kr_rdy,input wire [NPC*17-1:0] kr_tag,input wire [NPC*4-1:0] kr_beat,input wire [NPC*256-1:0] kr_data,
 input wire [NPC-1:0] k_wr_done,output wire [NPC-1:0] native_busy,output wire fault
);
 initial if(NPC!=32)$fatal(1,"production32-PC stack shape required");
 wire [NPC-1:0] nr,nrv,pfault;wire [NPC*16-1:0] nrt;wire [NPC*4-1:0] nrb;wire [NPC*256-1:0] nrd;
 reg active;reg[4:0]pc_q;reg[3:0]len_q;
 always @(posedge clk or negedge rst_n)if(!rst_n)begin active<=0;pc_q<=0;len_q<=1;end else begin
 if(native_v&&native_rdy)begin active<=1;pc_q<=native_pc;len_q<=ENABLE_NATIVE_BURST!=0?native_len:4'd1;end
 if(native_rsp_v&&native_rsp_rdy&&native_rsp_beat==len_q-1)active<=0;
 end
 assign native_rdy=ENABLE!=0&&!active&&nr[native_pc];
 assign native_rsp_v=active&&nrv[pc_q];assign native_rsp_pc=pc_q;
 assign native_rsp_tag=nrt[pc_q*16+:16];assign native_rsp_beat=nrb[pc_q*4+:4];assign native_rsp_data=nrd[pc_q*256+:256];
 assign fault=|pfault;
 for(genvar p=0;p<NPC;p=p+1)begin:pc
 ot_hbm_loader_pc_service_lease #(.ENABLE(ENABLE),.ENABLE_NATIVE_BURST(ENABLE_NATIVE_BURST)) u_lease(
 .clk(clk),.rst_n(rst_n),.normal_pending_write(normal_pending_write[p]),
 .normal_v(normal_v[p]),
 .normal_rdy(normal_rdy[p]),
 .normal_we(normal_we[p]),
 .normal_addr(normal_addr[p*30+:30]),
 .normal_len(normal_len[p*4+:4]),
 .normal_tag(normal_tag[p*17+:17]),
 .normal_wdata(normal_wdata[p*256+:256]),
 .normal_wstrb(normal_wstrb[p*32+:32]),
 .normal_rsp_v(normal_rsp_v[p]),
 .normal_rsp_rdy(normal_rsp_rdy[p]),
 .normal_rsp_tag(normal_rsp_tag[p*17+:17]),
 .normal_rsp_beat(normal_rsp_beat[p*4+:4]),
 .normal_rsp_data(normal_rsp_data[p*256+:256]),
 .native_v(native_v&&!active&&native_pc==p),.native_rdy(nr[p]),.native_addr(native_addr),.native_tag(native_tag),.native_len(native_len),
 .native_rsp_v(nrv[p]),.native_rsp_rdy(active&&pc_q==p&&native_rsp_rdy),.native_rsp_tag(nrt[p*16+:16]),
 .native_rsp_beat(nrb[p*4+:4]),.native_rsp_data(nrd[p*256+:256]),
 .k_v(k_v[p]),
 .k_rdy(k_rdy[p]),
 .k_we(k_we[p]),
 .k_addr(k_addr[p*30+:30]),
 .k_len(k_len[p*4+:4]),
 .k_tag(k_tag[p*17+:17]),
 .k_wdata(k_wdata[p*256+:256]),
 .k_wstrb(k_wstrb[p*32+:32]),
 .kr_v(kr_v[p]),
 .kr_rdy(kr_rdy[p]),
 .kr_tag(kr_tag[p*17+:17]),
 .kr_beat(kr_beat[p*4+:4]),
 .kr_data(kr_data[p*256+:256]),
 .k_wr_done(k_wr_done[p]),
 .native_busy(native_busy[p]),
 .fault(pfault[p]));
 end
endmodule
`default_nettype wire
