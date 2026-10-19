`timescale 1ns/1ps
`default_nettype none
// HBM F20 target52+qid: real 1536b programme assembler for cfg37 issuer.
// Address[11:9]=0, [8:3]=instruction row, [2:0]=segment. Segments0..5
// carry low-to-high256b uop; segment6 carries metadata[63:0], upper192=0.
// Seven unique frames in any order complete ONE row. No next row while drain
// runs: host compiler leaves55edges after the final frame before next frame.
// Drain emits53 registered commands then1guard; no ready/queue/backpressure.
// Descriptor base/limit are INSTRUCTION indices. loops=1 only; actual native
// issuer metadata retains32bit loop counts. Unsupported loops fault.
// Fresh reset is required to install a different programme. Writes to complete
// rows, partial row changes, launch before completion, and active writes fault.
// Descriptor validation scans64 rows on fixed edges. Reserve66edges from
// descriptor capture to global launch. Every next/target remains in range;
// descriptor last row must contain nativehalt. No runtime ready handshake.
module ot_hgi_coll_static_program_target #(
    parameter [7:0] TARGET=8'd52,
    parameter integer MUT_DATA=0,
    // LOOKAHEAD=1 (COLL fj margin successor, fj_n1s0 d4f TT +1.28: check_row -> flow[64:1 mux] -> row_bad -> fault,
    // 15 levels): the scanned row's flow word and loaded bit are registered one edge ahead (row 0 at descriptor
    // accept, row+1 while scanning). Exact: flow/loaded never change while checking (frames fault while checking,
    // drains cannot start), so every check reads the same values on the same edges. Default 0 = the closed form.
    parameter integer LOOKAHEAD=0,
    // XDIE-HBM4 (10-19): ROWS 128 (default 64 = unchanged): address[11:10]=0, [9:3]=row; metadata[53:51] carry the
    // next/target/lid pc MSBs (metadata[63:54]=0); descriptor base<128, limit<=128; the scan covers 128 rows (reserve
    // 130 edges from descriptor capture to launch); mode-0 issuer cfg carries row[6] in cfg[8].
    // HBM-COLL256-KITS (10-19, SAFE-DESIGN item 5): ROWS 256 keeps the 256 x 18-b flow words in ONE ot_sram_1rw_256x64
    // (g_fsram.u_flow) instead of 4.6 kb of flops: the macro read IS the lookahead register (row 0 read at descriptor
    // accept, row+1 while scanning; frames and descriptor scans never overlap, so one 1RW port suffices), and
    // issuer_start_pc is set at descriptor accept (= base, >= ROWS+2 edges before launch; the 256-row issuer v7 primes
    // its lookahead from a stable start_pc). ROWS 64/128 elaborate exactly as before (flow flops, start_pc at launch).
    parameter integer ROWS=64,
    parameter integer PW=(ROWS>128)?8:(ROWS>64)?7:6      // derived; never override
)(
    input wire clk,rst_n,
    input wire cfg_v,
    input wire [7:0] cfg_target,
    input wire [11:0] cfg_addr,
    input wire [255:0] cfg_data,
    input wire desc_v,
    input wire [11:0] desc_base,
    input wire [12:0] desc_limit,
    input wire [15:0] desc_loops,
    input wire launch_v,program_active,
    input wire issuer_busy,issuer_fault,issuer_uop_v,
    input wire [PW-1:0] issuer_uop_pc,
    output reg [36:0] issuer_cfg,
    output reg issuer_start,
    output reg [PW-1:0] issuer_start_pc,
    output reg configured,init_busy,fault
);
    // Input capture is the first transport rung. Processing and registered
    // cfg/start outputs are the second. Every exported signal is flop Q.
    reg cv,dv,lv;
    reg [7:0] target_q;
    reg [11:0] addr_q,base_q;
    reg [12:0] limit_q;
    reg [15:0] loops_q;
    reg [255:0] data_q;
    always @(posedge clk)begin
        target_q<=cfg_target;addr_q<=cfg_addr;data_q<=cfg_data;
        base_q<=desc_base;limit_q<=desc_limit;loops_q<=desc_loops;
    end
    reg [1535:0] assembly;
    reg [63:0] metadata;
    reg [6:0] seen;
    reg [PW-1:0] row;
    reg [ROWS-1:0] loaded;
    reg [2*PW+1:0] flow[0:ROWS-1]; // {halt,has_repeat,targetPC,nextPC}
    localparam integer FW=2*PW+2;
    reg checking,check_bad;
    reg [PW-1:0] check_row;
    reg draining;
    reg [5:0] step;
    reg [PW-1:0] base;
    reg [PW:0] limit;
    wire in_range={1'b0,check_row}>=base && {1'b0,check_row}<limit;
    reg [FW-1:0] f_la;reg ld_la;
    wire [FW-1:0] f_sram;
    wire [FW-1:0] f=(ROWS>128)?f_sram:(LOOKAHEAD!=0)?f_la:flow[check_row];
    wire ld=(LOOKAHEAD!=0)?ld_la:loaded[check_row];
    wire [PW-1:0] f_nx=f[PW-1:0],f_tg=f[2*PW-1:PW];wire f_halt=f[FW-1],f_rep=f[FW-2];
    wire row_bad=in_range && (!ld ||
        (!f_halt && (f_nx<base || {1'b0,f_nx}>=limit ||
          (f_rep && (f_tg<base || {1'b0,f_tg}>=limit)))) ||
        ({1'b0,check_row}==limit-1'b1 && !f_halt));
    wire [PW-1:0] a_row=addr_q[PW+2:3];
    wire a_hi_bad=(PW==8)?(addr_q[11]!=0):(PW==7)?(addr_q[11:10]!=0):(addr_q[11:9]!=0);
    localparam [12:0] MSPARE=(PW==8)?13'h1fc0:(PW==7)?13'h1ff8:13'h1fff;   // data[63:51] bits that must be zero
    wire occupied=program_active || issuer_busy || issuer_start;
    generate if(ROWS>128)begin:g_fsram
        // the same accept conditions as the frame / descriptor branches below (no fault this edge)
        wire fw=cv && target_q==TARGET && addr_q[2:0]==6 && !(occupied || lv || draining || checking || fault || dv ||
            a_hi_bad || loaded[a_row] || (seen!=0 && row!=a_row) || seen[6] || data_q[255:64]!=0 || (data_q[63:51]&MSPARE)!=0);
        wire dacc=dv && target_q==TARGET && !(occupied || lv || draining || checking || seen!=0 || fault || cv ||
            base_q>=ROWS || limit_q>ROWS || limit_q<={1'b0,base_q} || loops_q!=1);
`ifdef OT_PT_MUT_LA_STALE
        wire fr=dacc;                                              // mutant: lookahead never advances
`else
        wire fr=dacc || (checking && check_row!=PW'(ROWS-1));
`endif
        wire [PW-1:0] fa=dacc ? {PW{1'b0}} : PW'(check_row+1'b1);
        wire [FW-1:0] fwd={data_q[44],|data_q[43:12],data_q[55],data_q[52],data_q[11:6],data_q[54],data_q[51],data_q[5:0]};
        wire [63:0] rd;
        ot_sram_1rw_256x64_m4_r2c2 u_flow(.clk(clk),.ce_in(fw || fr),.we_in(fw),.addr_in(fw ? a_row : fa),
            .wd_in(64'(fwd)),.w_mask_in({64{1'b1}}),.rd_out(rd),
            .rr_en(2'b0),.rr_addr(12'b0),.cr_en(2'b0),.cr_sel(12'b0));
        assign f_sram=rd[FW-1:0];
    end else begin:g_fflop
        assign f_sram={FW{1'b0}};
    end endgenerate
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin
            cv<=0;dv<=0;lv<=0;issuer_cfg<=0;issuer_start<=0;
            issuer_start_pc<=0;configured<=0;init_busy<=0;fault<=0;
            seen<=0;loaded<=0;row<=0;draining<=0;step<=0;
            base<=0;limit<=0;checking<=0;check_bad<=0;check_row<=0;f_la<=0;ld_la<=0;
        end else begin
            cv<=cfg_v;dv<=desc_v;lv<=launch_v;
            issuer_cfg<=0;issuer_start<=0;
            if(issuer_fault)fault<=1;
            if(checking)begin
                if(row_bad)check_bad<=1;
                if(check_row==PW'(ROWS-1))begin
                    checking<=0;init_busy<=0;
                    if(check_bad || row_bad)fault<=1;
                    else if(!fault)configured<=1;
                end else begin
                    check_row<=check_row+1'b1;
`ifndef OT_PT_MUT_LA_STALE
                    f_la<=flow[PW'(check_row+1'b1)];ld_la<=loaded[PW'(check_row+1'b1)];   // mutant: lookahead never advances
`endif
                end
            end
            if(issuer_uop_v && (!configured || issuer_uop_pc<base || {1'b0,issuer_uop_pc}>=limit))fault<=1;
            if(draining)begin
                if(step<51)begin
                    if(step%17==0)issuer_cfg<=(PW==8)?{1'b1,4'd0,22'b0,row[PW-1:PW-2],2'(step/17),row[5:0]}:(PW==7)?{1'b1,4'd0,23'b0,row[PW-1],2'(step/17),row[5:0]}:{1'b1,4'd0,24'b0,2'(step/17),row[5:0]};
                    else issuer_cfg<={1'b1,4'd1,assembly[(step/17)*512+(step%17-1)*32+:32] ^ ((MUT_DATA!=0 && step==1)?32'b1:32'b0)};
                end else if(step==51)issuer_cfg<={1'b1,4'd2,metadata[31:0]};
                else if(step==52)issuer_cfg<={1'b1,4'd3,metadata[63:32]};
                // step53 ensures the issuer has sampled its final metadata.
                if(step==53)begin
                    draining<=0;loaded[row]<=1;seen<=0;init_busy<=0;
                end else step<=step+1'b1;
            end
            if(cv && target_q==TARGET)begin
                if(occupied || lv || draining || checking || fault || dv || a_hi_bad ||
                   addr_q[2:0]==7 || loaded[a_row] ||
                   (seen!=0 && row!=a_row) || seen[addr_q[2:0]] ||
                   (addr_q[2:0]==6 && (data_q[255:64]!=0 || (data_q[63:51]&MSPARE)!=0)))fault<=1;
                else begin
                    row<=a_row;seen[addr_q[2:0]]<=1;init_busy<=1;
                    if(addr_q[2:0]==6)begin
                        metadata<=data_q[63:0];
                        if(ROWS<=128)flow[a_row]<=(PW==8)?FW'({data_q[44],|data_q[43:12],data_q[55],data_q[52],data_q[11:6],data_q[54],data_q[51],data_q[5:0]})
                                            :(PW==7)?FW'({data_q[44],|data_q[43:12],data_q[52],data_q[11:6],data_q[51],data_q[5:0]})
                                            :FW'({data_q[44],|data_q[43:12],data_q[11:0]});
                    end
                    else assembly[addr_q[2:0]*256+:256]<=data_q;
                    if((seen | (7'b1<<addr_q[2:0]))==7'h7f)begin draining<=1;step<=0;end
                end
            end
            if(dv && target_q==TARGET)begin
                if(occupied || lv || draining || checking || seen!=0 || fault || cv ||
                   base_q>=ROWS || limit_q>ROWS || limit_q<={1'b0,base_q} || loops_q!=1)fault<=1;
                else begin
                    base<=base_q[PW-1:0];limit<=limit_q[PW:0];configured<=0;
`ifndef OT_PT_MUT_LATE_SPC
                    if(ROWS>128)issuer_start_pc<=base_q[PW-1:0];   // mutant: start_pc only at launch (v7 start faults)
`endif
                    checking<=1;check_row<=0;check_bad<=0;init_busy<=1;
                    f_la<=flow[0];ld_la<=loaded[0];
                end
            end
            if(lv && configured)begin
                if(occupied || draining || checking || seen!=0 || fault || cv || dv)fault<=1;
                else begin issuer_start<=1;issuer_start_pc<=base;end
            end else if(lv && (seen!=0 || draining || checking))fault<=1;
        end
    end
endmodule
`default_nettype wire
