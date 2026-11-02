`timescale 1ns/1ps
module ot_hgi_sfu_vm_static_bridge #(
 parameter integer LWB=15, READ_RETURN=14, WRITE_RETURN=11
)(
 input wire clk,rst_n,
  
  
 input wire [3:0] clk_lg,rst_lg_n,
 input wire [7:0] prefetch_v,
 input wire [127:0] prefetch_sector,
 input wire [15:0] prefetch_group,
 input wire [8*LWB-1:0] prefetch_local_addr,
 input wire [7:0] prefetch_scalar,
 input wire [23:0] prefetch_word,
 input wire [95:0] scalar_addr,
 output wire [135:0] local_rq,
 input wire [2055:0] local_rr,
 output wire [7:0] stage_v,
 output wire [15:0] stage_group,
 output wire [8*LWB-1:0] stage_addr,
 output wire [2047:0] stage_data,
 output wire [63:0] stage_mask,
 output reg [3:0] scalar_load,
 output wire [95:0] scalar_load_addr,
 output reg [127:0] scalar_data,
 input wire [1:0] drain_v,drain_round_bf16,
 input wire [31:0] drain_vm_sector,
 input wire [1:0] drain_result_v,
 input wire [511:0] drain_data,
 output wire [2247:0] local_wq,
 input wire [7:0] local_w_done,
 output reg fault
);
 localparam META=2+4+2*LWB+2+6;
 wire [7:0] expect_v,scalar;
 wire [23:0] word_sel;
 wire [3:0] group_fault;
  
 reg [95:0] scalar_addr_pipe[0:READ_RETURN];
 assign scalar_load_addr=scalar_addr_pipe[READ_RETURN];
 assign stage_v=expect_v&~scalar;
 assign stage_mask=64'hffffffffffffffff;
 for(genvar b=0;b<8;b=b+1)begin:g_read
  assign local_rq[b*17+:17]={prefetch_v[b],prefetch_sector[b*16+:16]};
  assign stage_data[b*256+:256]=local_rr[b*257+:256];
 end
 reg scalar_collision;
 reg [3:0] used_group;
 always @*begin
  scalar_load=0;scalar_data=0;used_group=0;scalar_collision=0;
  for(integer b=0;b<8;b=b+1)if(expect_v[b]&&scalar[b])begin
   if(used_group[stage_group[2*b+:2]])scalar_collision=1;
   used_group[stage_group[2*b+:2]]=1;
   scalar_load[stage_group[2*b+:2]]=1;
   scalar_data[32*stage_group[2*b+:2]+:32]=local_rr[257*b+32*word_sel[3*b+:3]+:32];
  end
 end
 function automatic [255:0] round_sector(input [255:0] data,input do_round);
  reg [31:0] word,rounded;
  for(integer w=0;w<8;w=w+1)begin
   word=data[32*w+:32];
 
    


   rounded=word+32'h00007fff+{31'd0,word[16]};


   round_sector[32*w+:32]=do_round?{rounded[31:16],16'd0}:word;
  end
 endfunction
  
  
  
  
 for(genvar g=0;g<4;g=g+1)begin:g_lg
  reg [META-1:0] meta[0:READ_RETURN];
  reg [561:0] write_q;
  assign local_wq[562*g+:562]=write_q;
  assign {expect_v[2*g+:2],stage_group[4*g+:4],stage_addr[2*LWB*g+:2*LWB],
          scalar[2*g+:2],word_sel[6*g+:6]}=meta[READ_RETURN];
  reg [1:0] drain_round_q,drain_expected;
  reg [31:0] drain_sector_q;
  reg [1:0] write_expected[0:WRITE_RETURN+1];
  reg [1:0] write_v;
  reg write_collision;
  reg fault_q;
  assign group_fault[g]=fault_q;
  always @*begin
   write_v=0;write_collision=0;
   for(integer s=0;s<2;s=s+1)
    if(drain_expected[s] && drain_sector_q[16*s+1+:2]==g)begin
     if(write_v[drain_sector_q[16*s]])write_collision=1;
     write_v[drain_sector_q[16*s]]=1;
    end
  end
  always @(posedge clk_lg[g])begin
   drain_sector_q<=drain_vm_sector;drain_round_q<=drain_round_bf16;
   write_q<=0;
   for(integer s=0;s<2;s=s+1)
    if(drain_expected[s] && drain_sector_q[16*s+1+:2]==g)
     write_q[281*drain_sector_q[16*s]+:281]<=
      {1'b1,drain_sector_q[16*s+:16],round_sector(drain_data[256*s+:256],drain_round_q[s]),8'hff};
  end
  always @(posedge clk_lg[g] or negedge rst_lg_n[g])begin
   if(!rst_lg_n[g])begin
    fault_q<=0;drain_expected<=0;
    for(integer i=0;i<=WRITE_RETURN+1;i=i+1)write_expected[i]<=0;
    for(integer i=0;i<=READ_RETURN;i=i+1)meta[i]<=0;
   end else begin
    meta[0]<={prefetch_v[2*g+:2],prefetch_group[4*g+:4],prefetch_local_addr[2*LWB*g+:2*LWB],
              prefetch_scalar[2*g+:2],prefetch_word[6*g+:6]};
    for(integer i=1;i<=READ_RETURN;i=i+1)meta[i]<=meta[i-1];
    drain_expected<=drain_v;
    write_expected[0]<=write_v;
    for(integer i=1;i<=WRITE_RETURN+1;i=i+1)write_expected[i]<=write_expected[i-1];
    for(integer b=0;b<2;b=b+1)begin
     if(prefetch_v[2*g+b]&&prefetch_sector[16*(2*g+b)+:3]!=(2*g+b))fault_q<=1;
     if(expect_v[2*g+b]!=local_rr[(2*g+b)*257+256])fault_q<=1;
     if(write_expected[WRITE_RETURN+1][b]!=local_w_done[2*g+b])fault_q<=1;
    end
    if(drain_result_v!=drain_expected || write_collision)fault_q<=1;
   end
  end
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   fault<=0;
   for(integer i=0;i<=READ_RETURN;i=i+1)scalar_addr_pipe[i]<=0;
  end else begin
   scalar_addr_pipe[0]<=scalar_addr;
   for(integer i=1;i<=READ_RETURN;i=i+1)scalar_addr_pipe[i]<=scalar_addr_pipe[i-1];
   if(|group_fault || scalar_collision)fault<=1;
  end
 end
endmodule
module ot_hgi_sfu_lg_pair_tap_leaf #(
    parameter integer READ_RETURN=14,
    parameter integer WRITE_RETURN=11,
    parameter integer MUT=0
)(
    input  wire clk,rst_n,
    input  wire [33:0]  c_rq,
    input  wire [561:0] c_wq,
    output wire [513:0] c_rr,
    output wire [1:0]   c_w_done,
    input  wire [1:0]   local_read,local_write,
    input  wire [33:0]  far_rq,
    input  wire [561:0] far_wq,
    output wire [513:0] far_rr,
    output wire [1:0]   far_w_done,
    output wire [33:0]  near_rq,
    output wire [561:0] near_wq,
    input  wire [513:0] near_rr,
    input  wire [1:0]   near_w_done,
    output wire         fault
);
    wire [33:0] l_rq; wire [561:0] l_wq; wire [513:0] l_rr; wire [1:0] l_done;
    (* keep = "true" *) reg rst_pin; always @(posedge clk) rst_pin <= rst_n;    
    ot_hgi_sfu_lg_pair_leaf #(.PIN_RST(0)) u_leaf(.clk(clk),.rst_n(rst_pin),.c_rq(c_rq),.c_wq(c_wq),.c_rr(c_rr),
        .c_w_done(c_w_done),.lg_rq(l_rq),.lg_wq(l_wq),.lg_rr(l_rr),.lg_w_done(l_done));
    ot_hbm_vm_lg_pair_tap #(.READ_RETURN(READ_RETURN),.WRITE_RETURN(WRITE_RETURN),.MUT(MUT)) u_tap(
        .clk(clk),.rst_n(rst_pin),.local_rq(l_rq),.far_rq(far_rq),.local_wq(l_wq),.far_wq(far_wq),
        .local_read(local_read),.local_write(local_write),.near_rq(near_rq),.near_wq(near_wq),
        .near_rr(near_rr),.near_w_done(near_w_done),.local_rr(l_rr),.far_rr(far_rr),
        .local_w_done(l_done),.far_w_done(far_w_done),.fault(fault));
endmodule
module ot_hgi_sfu_lg_pair_leaf #(parameter integer PIN_RST=0) (
 input wire clk,rst_n,
 input wire [33:0] c_rq,
 input wire [561:0] c_wq,
 output wire [513:0] c_rr,
 output wire [1:0] c_w_done,
 output wire [33:0] lg_rq,
 output wire [561:0] lg_wq,
 input wire [513:0] lg_rr,
 input wire [1:0] lg_w_done
);
  
  
 (* keep = "true" *) reg rst_pin;
 generate if(PIN_RST) begin:g_rst_pin
  always @(posedge clk) rst_pin <= rst_n;
 end else begin:g_rst_wire
  always @* rst_pin = rst_n;
 end endgenerate
 for(genvar b=0;b<2;b=b+1)begin:g_bank
   
  ot_hdc_delay #(.W(1),.D(1),.RESET(1)) u_rqv(.clk(clk),.rst_n(rst_pin),.d(c_rq[17*b+16]),.q(lg_rq[17*b+16]));
  ot_hdc_delay #(.W(16),.D(1)) u_rqd(.clk(clk),.rst_n(rst_pin),.d(c_rq[17*b+:16]),.q(lg_rq[17*b+:16]));
   
  ot_hdc_delay #(.W(1),.D(1),.RESET(1)) u_wqv(.clk(clk),.rst_n(rst_pin),.d(c_wq[281*b+280]),.q(lg_wq[281*b+280]));
  ot_hdc_delay #(.W(280),.D(1)) u_wqd(.clk(clk),.rst_n(rst_pin),.d(c_wq[281*b+:280]),.q(lg_wq[281*b+:280]));
   
  ot_hdc_delay #(.W(1),.D(1),.RESET(1)) u_rrv(.clk(clk),.rst_n(rst_pin),.d(lg_rr[257*b+256]),.q(c_rr[257*b+256]));
  ot_hdc_delay #(.W(256),.D(1)) u_rrd(.clk(clk),.rst_n(rst_pin),.d(lg_rr[257*b+:256]),.q(c_rr[257*b+:256]));
 end
 ot_hdc_delay #(.W(2),.D(1),.RESET(1)) u_done(.clk(clk),.rst_n(rst_pin),.d(lg_w_done),.q(c_w_done));
endmodule
module ot_hbm_vm_lg_pair_tap #(
    parameter integer READ_RETURN=10,
    parameter integer WRITE_RETURN=7,
    parameter integer MUT=0,          
    parameter integer LOCAL_SPLIT=0,  
    parameter integer SPLIT_MUT=0     
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
        ot_hbm_vm_lg_static_bank #(.READ_RETURN(READ_RETURN),.WRITE_RETURN(WRITE_RETURN),.MUT(b==1?MUT:0),.RET_PIN(0),.LOCAL_SPLIT(LOCAL_SPLIT),.SPLIT_MUT(b==1?SPLIT_MUT:0)) u_tap(
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
module ot_hbm_vm_lg_static_bank #(
    parameter integer READ_RETURN=10,
    parameter integer WRITE_RETURN=7,
    parameter integer MUT=0,  
     
     
    parameter integer RET_PIN=0,
     
     
     
     
     
     
     
     
     
    parameter integer LOCAL_SPLIT=0,
    parameter integer SPLIT_MUT=0
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
    initial if(LOCAL_SPLIT!=0&&(RET_PIN!=0||READ_RETURN<3||WRITE_RETURN<3))$fatal(1,"LOCAL_SPLIT needs RET_PIN=0 and returns >= 3");
    localparam integer DUE_OFF=(LOCAL_SPLIT!=0&&SPLIT_MUT!=1)?2:1;
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
    wire [0:0] read_due =(RET_PIN!=0)?read_calendar[rret_q-5'd1]:read_calendar[READ_RETURN-DUE_OFF];
    wire [0:0] write_due=(RET_PIN!=0)?write_calendar[wret_q-5'd1]:write_calendar[WRITE_RETURN-DUE_OFF];
    wire [255:0] return_l;    
    if(LOCAL_SPLIT!=0)begin:g_lsplit
        ot_hbm_vm_lg_keep_reg u_ret_l(.clk(clk),.d(SPLIT_MUT==2?near_rr[255:0]:rr_d[255:0]),.q(return_l));
    end else begin:g_lshare
        assign return_l=return_d[255:0];
    end
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
                if(LOCAL_SPLIT!=0)begin
                    read_calendar[0][b]<=read_d[b]&&lrq_v[b];
                    write_calendar[0][b]<=write_d[b]&&lwq_v[b];
                end else begin
                    read_calendar[0][b]<=local_read[b]&&local_rq[b*17+16];
                    write_calendar[0][b]<=local_write[b]&&local_wq[b*281+280];
                end
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
        assign local_rr[b*257+:257]={local_rr_v[b],return_l};
        assign far_rr[b*257+:257]={far_rr_v[b],return_d[b*257+:256]};
    end
endmodule
module ot_hbm_vm_lg_keep_reg (
    input wire clk,
    input wire [255:0] d,
    output reg [255:0] q
);
    always @(posedge clk) q<=d;
endmodule
module ot_hdc_delay #(
    parameter integer W = 32,
    parameter integer D = 1,
    parameter integer RESET = 0
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    generate
        if (D == 0) begin : g_wire
            assign q = d;
        end else if (D == 1) begin : g_one
            reg [W-1:0] line;
            if (RESET != 0) begin : g_rst
                always @(posedge clk or negedge rst_n)
                    if (!rst_n) line <= {W{1'b0}};
                    else line <= d;
            end else begin : g_nrst
                always @(posedge clk) line <= d;
            end
            assign q = line;
        end else begin : g_line
            reg [W*D-1:0] line;
            if (RESET != 0) begin : g_rst
                always @(posedge clk or negedge rst_n)
                    if (!rst_n) line <= {(W*D){1'b0}};
                    else line <= {line[W*(D-1)-1:0], d};
            end else begin : g_nrst
                always @(posedge clk) line <= {line[W*(D-1)-1:0], d};
            end
            assign q = line[W*D-1 -: W];
        end
    endgenerate
endmodule
