`timescale 1ns/1ps
module ot_hbm_su_static_pg_lg_tap_m60 #(
 parameter integer READ_RETURN=10,WRITE_RETURN=7,
 parameter integer RSYNC_MUT=0
)(
 input  wire clk_ctl,              
 input  wire pg_clk,               
 input  wire rst_n,                
 input  wire [33:0]  local_rq,far_rq,
 input  wire [561:0] local_wq,far_wq,
 input  wire [1:0]   local_read,local_write,
 output wire [33:0]  near_rq,
 output wire [561:0] near_wq,
 input  wire [513:0] near_rr,
 input  wire [1:0]   near_w_done,
 output wire [513:0] local_rr,far_rr,
 output wire [1:0]   local_w_done,far_w_done,
 output wire         fault
);
 wire tap_rst_n;
 if(RSYNC_MUT==1)begin:g_rmut
  (* keep = "true" *) reg lg_rst; always @(posedge pg_clk) lg_rst <= rst_n;
  assign tap_rst_n = lg_rst;
 end else begin:g_rsync
  reg rc; reg [1:0] rs;
  always @(posedge clk_ctl) rc <= rst_n;
  always @(posedge pg_clk) rs <= {rs[0], rc};
  assign tap_rst_n = rs[1];
 end
 ot_hbm_vm_lg_pair_tap_m60 #(.READ_RETURN(READ_RETURN),.WRITE_RETURN(WRITE_RETURN)) u_tap(
  .clk(pg_clk),.rst_n(tap_rst_n),.local_rq(local_rq),.far_rq(far_rq),.local_wq(local_wq),.far_wq(far_wq),
  .local_read(local_read),.local_write(local_write),.near_rq(near_rq),.near_wq(near_wq),.near_rr(near_rr),
  .near_w_done(near_w_done),.local_rr(local_rr),.far_rr(far_rr),.local_w_done(local_w_done),.far_w_done(far_w_done),
  .fault(fault));
endmodule
module ot_hbm_vm_lg_pair_tap_m60 #(
    parameter integer READ_RETURN=10,
    parameter integer WRITE_RETURN=7,
    parameter integer MUT=0           
)(
    input  wire clk,rst_n,
    input  wire [33:0]  local_rq,far_rq,
    input  wire [561:0] local_wq,far_wq,
    input  wire [1:0]   local_read,local_write,
    output wire [33:0]  near_rq,
    output wire [561:0] near_wq,
    input  wire [513:0] near_rr,
    input  wire [1:0]   near_w_done,
    output wire [513:0] local_rr,far_rr,
    output wire [1:0]   local_w_done,far_w_done,
    output wire         fault
);
    wire [1:0] f;
    for(genvar b=0;b<2;b=b+1)begin:g_bank
        ot_hbm_vm_lg_static_bank_m60 #(.READ_RETURN(READ_RETURN),.WRITE_RETURN(WRITE_RETURN),.MUT(b==1?MUT:0),.RET_PIN(0)) u_tap(
            .clk(clk),.rst_n(rst_n),.rret(5'd0),.wret(5'd0),
            .local_rq(local_rq[b*17+:17]),.far_rq(far_rq[b*17+:17]),
            .local_wq(local_wq[b*281+:281]),.far_wq(far_wq[b*281+:281]),
            .local_read(local_read[b]),.local_write(local_write[b]),
            .near_rq(near_rq[b*17+:17]),.near_wq(near_wq[b*281+:281]),
            .near_rr(near_rr[b*257+:257]),.near_w_done(near_w_done[b]),
            .local_rr(local_rr[b*257+:257]),.far_rr(far_rr[b*257+:257]),
            .local_w_done(local_w_done[b]),.far_w_done(far_w_done[b]),.fault(f[b]));
    end
    assign fault=|f;
endmodule
module ot_hbm_vm_lg_static_bank_m60 #(
    parameter integer READ_RETURN=10,
    parameter integer WRITE_RETURN=7,
    parameter integer MUT=0,  
    parameter integer RET_PIN=0
)(
    input wire clk,rst_n,
    input wire [4:0] rret,wret,    
    input wire [16:0] local_rq,far_rq,
    input wire [280:0] local_wq,far_wq,
    input wire [0:0] local_read,local_write,
    output wire [16:0] near_rq,
    output wire [280:0] near_wq,
    input wire [256:0] near_rr,
    input wire [0:0] near_w_done,
    output wire [256:0] local_rr,far_rr,
    output reg [0:0] local_w_done,far_w_done,
    output reg fault
);
    initial if(READ_RETURN<2||WRITE_RETURN<2)$fatal(1,"tap return latency must include pin/output edges");
    reg [16:0] lrq_d,frq_d;
    reg [280:0] lwq_d,fwq_d;
    reg [0:0] lrq_v,frq_v,lwq_v,fwq_v,read_d,write_d;
    reg [16:0] rq_d;
    reg [280:0] wq_d;
    reg [0:0] rq_v,wq_v;
    reg [256:0] rr_d,return_d;
    reg [0:0] rr_v,done_d,local_rr_v,far_rr_v;
    reg [0:0] read_calendar[0:READ_RETURN-1];
    reg [0:0] write_calendar[0:WRITE_RETURN-1];
    reg [4:0] rret_q,wret_q; always @(posedge clk) begin rret_q<=rret; wret_q<=wret; end
    wire [0:0] read_due =(RET_PIN!=0)?read_calendar[rret_q-5'd1]:read_calendar[READ_RETURN-1];
    wire [0:0] write_due=(RET_PIN!=0)?write_calendar[wret_q-5'd1]:write_calendar[WRITE_RETURN-1];
    always @(posedge clk)begin
        lrq_d<=local_rq;frq_d<=far_rq;lwq_d<=local_wq;fwq_d<=far_wq;
        rr_d<=near_rr;return_d<=rr_d;
        for(integer b=0;b<1;b=b+1)begin
            rq_d[b*17+:16]<=read_d[b]?lrq_d[b*17+:16]:frq_d[b*17+:16];
            wq_d[b*281+:280]<=write_d[b]?lwq_d[b*281+:280]:fwq_d[b*281+:280];
            if(MUT==1&&write_d[b])wq_d[b*281+8+:256]<=fwq_d[b*281+8+:256];
        end
    end
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin
            lrq_v<=0;frq_v<=0;lwq_v<=0;fwq_v<=0;read_d<=0;write_d<=0;
            rq_v<=0;wq_v<=0;rr_v<=0;done_d<=0;
            local_rr_v<=0;far_rr_v<=0;local_w_done<=0;far_w_done<=0;fault<=0;
            for(integer i=0;i<READ_RETURN;i=i+1)read_calendar[i]<=0;
            for(integer i=0;i<WRITE_RETURN;i=i+1)write_calendar[i]<=0;
        end else begin
            read_d<=local_read;write_d<=local_write;done_d<=near_w_done;
            for(integer i=1;i<READ_RETURN;i=i+1)read_calendar[i]<=read_calendar[i-1];
            for(integer i=1;i<WRITE_RETURN;i=i+1)write_calendar[i]<=write_calendar[i-1];
            for(integer b=0;b<1;b=b+1)begin
                lrq_v[b]<=local_rq[b*17+16];frq_v[b]<=far_rq[b*17+16];
                lwq_v[b]<=local_wq[b*281+280];fwq_v[b]<=far_wq[b*281+280];
                rr_v[b]<=near_rr[b*257+256];
                read_calendar[0][b]<=local_read[b]&&local_rq[b*17+16];
                write_calendar[0][b]<=local_write[b]&&local_wq[b*281+280];
                rq_v[b]<=read_d[b]?lrq_v[b]:frq_v[b];
                wq_v[b]<=write_d[b]?lwq_v[b]:fwq_v[b];
                local_rr_v[b]<=read_due[b];
                far_rr_v[b]<=rr_v[b]&&!read_due[b];
                local_w_done[b]<=write_due[b];
                far_w_done[b]<=done_d[b]&&!write_due[b];
                if((lrq_v[b]&&!read_d[b])||(lwq_v[b]&&!write_d[b])||
                   (read_d[b]&&frq_v[b])||(write_d[b]&&fwq_v[b])||
                   (read_due[b]&&!rr_v[b])||
                   (write_due[b]&&!done_d[b]))fault<=1;
            end
        end
    end
    for(genvar b=0;b<1;b=b+1)begin:bank
        assign near_rq[b*17+:17]={rq_v[b],rq_d[b*17+:16]};
        assign near_wq[b*281+:281]={wq_v[b],wq_d[b*281+:280]};
        assign local_rr[b*257+:257]={local_rr_v[b],return_d[b*257+:256]};
        assign far_rr[b*257+:257]={far_rr_v[b],return_d[b*257+:256]};
    end
endmodule