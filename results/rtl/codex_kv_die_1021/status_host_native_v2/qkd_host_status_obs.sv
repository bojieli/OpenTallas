`timescale 1ns/1ps
// Opt-in STATUS-only HOST reader. Real AXI4-Lite pass-through and atomic CSR snapshot.
module qkd_host_status_obs #(
    parameter integer MUT = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    input wire status_obs_v,
    input wire[15:0] status_obs_epoch16,
    input wire[207:0] status_obs_payload,
    // upstream: from the packet AXI master
    input  wire          u_awvalid, output wire u_awready, input wire [12:0] u_awaddr,
    input  wire          u_wvalid,  output wire u_wready,  input wire [31:0] u_wdata, input wire [3:0] u_wstrb,
    output wire          u_bvalid,  input  wire u_bready,  output wire [1:0] u_bresp,
    input  wire          u_arvalid, output wire u_arready, input wire [12:0] u_araddr,
    output wire          u_rvalid,  input  wire u_rready,  output wire [31:0] u_rdata, output wire [1:0] u_rresp,
    // downstream: to the CSR slave
    output wire          d_awvalid, input  wire d_awready, output wire [12:0] d_awaddr,
    output wire          d_wvalid,  input  wire d_wready,  output wire [31:0] d_wdata, output wire [3:0] d_wstrb,
    input  wire          d_bvalid,  output wire d_bready,  input  wire [1:0] d_bresp,
    output wire          d_arvalid, input  wire d_arready, output wire [12:0] d_araddr,
    input  wire          d_rvalid,  output wire d_rready,  input  wire [31:0] d_rdata, input wire [1:0] d_rresp
);
    localparam integer NB=293,NW=10;
    wire[3:0] rn;
    genvar rg;
    for(rg=0;rg<4;rg=rg+1)begin:g_reset
      qkd_status_obs_reset u_reset(.ck(clk),.rst_n(rst_n),.out_n(rn[rg]));
    end
    reg alive;
    always @(posedge clk or negedge rn[0])if(!rn[0])alive<=0;else alive<=1;
    wire schema_good;
    ot_qwen_status_obs_v1_valid u_schema(.x(status_obs_payload),.good(schema_good));
    wire accept=alive&&status_obs_v&&schema_good;
    reg ev_q,bad_q;
    reg[15:0]ep_q;wire[15:0]receipt_epoch;
    reg[31:0]count_q;wire[31:0]previous_count,delta;
    reg overflow_q,seen;
    reg[3:0]errors;
    always @(posedge clk)begin ep_q<=status_obs_epoch16;count_q<=status_obs_payload[92:61];overflow_q<=status_obs_payload[93];end
    always @(posedge clk or negedge rn[3])
      if(!rn[3])begin ev_q<=0;bad_q<=0;seen<=0;errors<=0;end
      else begin
        ev_q<=accept;bad_q<=alive&&status_obs_v&&!schema_good;
        if(bad_q)errors[3]<=1;
        if(ev_q)begin
          seen<=1;
          if(seen&&ep_q==receipt_epoch&&count_q<previous_count)errors[0]<=1;
          if(overflow_q)errors[1]<=1;
          if(seq_full_lo)errors[2]<=1;
        end
      end
    wire[31:0]delta_d=MUT==3?{31'd0,|count_q}:(!seen||ep_q!=receipt_epoch)?count_q:
                    count_q>=previous_count?count_q-previous_count:32'd0;
    qkd_status_obs_capture #(.W(16)) u_epoch(.ck(clk),.event_v(ev_q),.active(alive),.d(ep_q),.q(receipt_epoch));
    genvar md;
    for(md=0;md<2;md=md+1)begin:g_metadata
      qkd_status_obs_capture #(.W(16)) u_previous(.ck(clk),.event_v(ev_q),.active(alive),.d(count_q[16*md+:16]),.q(previous_count[16*md+:16]));
      qkd_status_obs_capture #(.W(16)) u_delta(.ck(clk),.event_v(ev_q),.active(alive),.d(delta_d[16*md+:16]),.q(delta[16*md+:16]));
    end
    reg[15:0]seq_lo,seq_hi;
    wire seq_full_lo,seq_full_hi;
    ot_qwen_status_obs_full32 u_full_lo(.lo(seq_lo),.hi(seq_hi),.full(seq_full_lo));
    ot_qwen_status_obs_full32 u_full_hi(.lo(seq_lo),.hi(seq_hi),.full(seq_full_hi));
    always @(posedge clk or negedge rn[1])
      if(!rn[1])seq_lo<=0;else if(ev_q&&!seq_full_lo)seq_lo<=seq_lo+16'd1;
    always @(posedge clk or negedge rn[2])
      if(!rn[2])seq_hi<=0;else if(ev_q&&(&seq_lo)&&!seq_full_hi)seq_hi<=seq_hi+16'd1;
    wire[NB-1:0]fields={seen,errors,delta,seq_hi,seq_lo,receipt_epoch,status_obs_payload};

    wire aw_win=u_awaddr[12]&&u_awaddr[11:9]==3'b100;
    wire ar_win=u_araddr[12]&&u_araddr[11:9]==3'b100;
    reg o_bvalid,o_rvalid,rd_busy,d_rpend,d_wpend;
    reg[2:0]rd_ph;
    reg[6:0]idx_r;
    reg data_r;
    reg[31:0]ctl_r;wire[31:0]o_rdata,local_rdata;
    reg[1:0]o_rresp;
    reg snapshot_valid,cap_q;
    wire wr_go=alive&&u_awvalid&&u_wvalid&&aw_win&&!o_bvalid&&!d_wpend;
    wire rd_go=alive&&u_arvalid&&ar_win&&!o_rvalid&&!rd_busy&&!d_rpend;
    wire cap=wr_go&&u_awaddr[8:2]==0&&u_wstrb[0]&&u_wdata[0]&&MUT!=1;
    wire data_req=u_araddr[8]&&u_araddr[7:6]==0&&u_araddr[5:2]<NW;
    wire[3:0]read_idx=u_araddr[5:2]+(MUT==2?4'd1:4'd0);
    assign d_awvalid=u_awvalid&&!aw_win&&!o_bvalid;
    assign d_wvalid=u_wvalid&&!aw_win&&!o_bvalid;
    assign d_awaddr=u_awaddr;assign d_wdata=u_wdata;assign d_wstrb=u_wstrb;
    assign d_bready=u_bready;
    assign d_arvalid=u_arvalid&&!ar_win&&!o_rvalid&&!rd_busy;
    assign d_araddr=u_araddr;assign d_rready=u_rready;
    assign u_awready=aw_win?wr_go:(d_awready&&!o_bvalid);
    assign u_wready=aw_win?wr_go:(d_wready&&!o_bvalid);
    assign u_bvalid=o_bvalid|d_bvalid;assign u_bresp=o_bvalid?2'b00:d_bresp;
    assign u_arready=ar_win?rd_go:(d_arready&&!o_rvalid&&!rd_busy);
    assign u_rvalid=o_rvalid|d_rvalid;
    assign u_rdata=MUT==4?o_rdata:local_rdata;
    assign u_rresp=o_rvalid?o_rresp:d_rresp;
    wire[31:0]part[0:(NB+15)/16];
    assign part[0]=0;
    genvar g;
    for(g=0;g<(NB+15)/16;g=g+1)begin:g_words
      localparam integer LO=16*g,W=(LO+16<=NB)?16:NB-LO;
      wire[15:0]read_half;
      qkd_status_obs_slice #(.W(W),.LIVE(LO<208),.WORD(g/2)) u_word(
        .ck(clk),.event_v(accept),.d(fields[LO+:W]),.cap(cap),
        .rd_go(rd_go&&data_req),.rd_idx(read_idx),.rd_data(read_half));
      assign part[g+1]=part[g]|({16'd0,read_half}<<(16*(g%2)));
    end
    always @(posedge clk or negedge rn[0])
      if(!rn[0])begin
        o_bvalid<=0;o_rvalid<=0;rd_busy<=0;d_rpend<=0;d_wpend<=0;
        rd_ph<=0;idx_r<=0;data_r<=0;o_rresp<=0;snapshot_valid<=0;cap_q<=0;
      end else begin
        cap_q<=cap;if(cap_q)snapshot_valid<=1;
        if(d_arvalid&&d_arready)d_rpend<=1;
        if(d_rvalid&&d_rready)d_rpend<=0;
        if(d_awvalid&&d_awready)d_wpend<=1;
        if(d_bvalid&&d_bready)d_wpend<=0;
        if(o_bvalid&&u_bready)o_bvalid<=0;
        if(wr_go)o_bvalid<=1;
        if(o_rvalid&&u_rready)o_rvalid<=0;
        rd_ph<={rd_ph[1:0],rd_go};
        if(rd_go)begin
          rd_busy<=1;idx_r<={u_araddr[8],u_araddr[7:2]};
          o_rresp<=data_req&&!snapshot_valid?2'b10:2'b00;
        end
        data_r<=idx_r[6]&&idx_r[5:0]<NW&&snapshot_valid;
        if(rd_ph[1])begin o_rvalid<=1;rd_busy<=0;end
      end
    always @(posedge clk)begin
      ctl_r<=idx_r[6]?32'd0:idx_r[5:0]==0?{8'h53,8'd1,8'd10,7'd0,snapshot_valid}:
             idx_r[5:0]==1?{16'd208,16'd293}:32'd0;

    end    wire[31:0]read_d=data_r?part[(NB+15)/16]:ctl_r;
    genvar rp;
    for(rp=0;rp<2;rp=rp+1)begin:g_response
      qkd_status_obs_response #(.W(16)) u_response(.ck(clk),.rst_n(rn[0]),.start(rd_ph[1]),.active(rd_busy),.ready(u_rready),
        .d(read_d[16*rp+:16]),.down(d_rdata[16*rp+:16]),.raw(o_rdata[16*rp+:16]),.out(local_rdata[16*rp+:16]));
    end

endmodule

// Real per16-bit payload/snapshot/read partitions. All data are invalid until
// accepted STATUS and an explicit CAPTURE; data flops deliberately stay unreset.
(* keep_hierarchy=1 *)module qkd_status_obs_slice #(
 parameter integer W=16,LIVE=1,WORD=0
)(input wire ck,event_v,cap,rd_go,input wire[W-1:0]d,input wire[3:0]rd_idx,
 output reg[15:0]rd_data);
 reg[W-1:0]pending,live,snapshot;
 reg valid_q,cap_q,read_q;
 reg[3:0]idx_q;
 always @(posedge ck)begin
   pending<=d;valid_q<=event_v;cap_q<=cap;read_q<=rd_go;idx_q<=rd_idx;
   if(LIVE&&valid_q)live<=pending;
   if(cap_q)snapshot<=LIVE?live:d;
   if(read_q)rd_data<=idx_q==WORD?{{(16-W){1'b0}},snapshot}:16'd0;
 end
endmodule
(* keep_hierarchy=1 *)module qkd_status_obs_reset(input wire ck,rst_n,output wire out_n);
 reg a,b;
 always @(posedge ck or negedge rst_n)if(!rst_n)begin a<=0;b<=0;end else begin a<=1;b<=a;end
 assign out_n=b;
endmodule

// Each metadata partition owns a real capture enable. The kept gate prevents
// mapping the shared event into every data mux; no event or data edge is added.
(* keep_hierarchy=1 *)module qkd_status_obs_capture_enable(input wire a,b,output wire y);
 assign y=a&&b;
endmodule
(* keep_hierarchy=1 *)module qkd_status_obs_capture #(parameter integer W=16)(
 input wire ck,event_v,active,input wire[W-1:0]d,output reg[W-1:0]q);
 wire en;
 qkd_status_obs_capture_enable u_en(.a(event_v),.b(active),.y(en));
 always @(posedge ck)if(en)q<=d;
endmodule
// This partition owns response data and valid together. Its private response
// state selects its own AXI data half and clears on the actual read handshake.
(* keep_hierarchy=1 *)module qkd_status_obs_response #(parameter integer W=16)(
 input wire ck,rst_n,start,active,ready,input wire[W-1:0]d,down,output wire[W-1:0]raw,out);
 reg valid;
 qkd_status_obs_capture #(.W(W)) u_data(.ck(ck),.event_v(start),.active(active),.d(d),.q(raw));
 always @(posedge ck or negedge rst_n)if(!rst_n)valid<=0;
 else begin if(valid&&ready)valid<=0;if(start)valid<=1;end
 assign out=valid?raw:down;
endmodule
