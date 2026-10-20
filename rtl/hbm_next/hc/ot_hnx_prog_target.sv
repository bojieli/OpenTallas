`timescale 1ns/1ps
`default_nettype none
// F20 programme target, hc_<q> copy (HUB-SAFE2 2026-10-20, kit hnx_hcq_hub_safe2_1020) of ot_static_program_target
// (TGT_PIN=1, CAP_CLK=0 form; same ports, F20 protocol, faults and outputs).  SAFE-DESIGN item 3 (fanout) rebuild of the
// installed-row bitmap, which the census of safe1019 found as: reset_live -> 1,059 reset flops, scan_row[0] -> 1,032 /
// [1] 517 loads (1,024:1 bitmap read), program_cfg_we -> 135, program_cfg_addr -> 43 (1,024-row write decode).
//  * The bitmap is NR rows x 32 bits.  A write loads it through KEPT per-row copies of the write strobe (we_c), of the
//    "first write of a new image" clear (clr_c) and of the row one-hot (row_c), plus a KEPT column one-hot (col_c, one
//    copy per row); every copy has <= 32 loads.  The copies are registered on the SAME edge as program_cfg_we (from its
//    next-state), so the bitmap updates on the same edge as before.
//  * The bitmap has NO reset.  img_v (reset) says "an image was written since reset"; a row reads as installed only if
//    img_v.  Before, reset cleared the bitmap; the first write after reset clears every other row (install_open is 0
//    after reset), so both forms read identically.
//  * Scan: the row check is a two-stage registered read (stage A: each row's bit at the scan column, through a KEPT
//    per-row copy of the column pointer; stage B: the row's bit at the scan row group).  scanning stays high until the
//    last row's check leaves stage B (2 edges later than before).  This is INITIALIZATION latency only (configured rises
//    2 edges later; launch is refused before configured, as before; the host waits for configured).
//  * program_cfg_data carries data_q on every edge (it is consumed only with program_cfg_we): no 256-load enable.
// Everything else (descriptor arm / reuse, launch, fault conditions) is the generic module's code.
// HUB-SAFE3 2026-10-20 (census safe2; zero added edges, F20 protocol / faults / configured unchanged):
//  * reset_live is a 4-copy KEPT family (ot_rst_split: the synthesis pass ot_rst_copies.py spreads its reset loads, 55);
//  * cfg_v / desc_v land in 2 / 3 KEPT copies, so the write strobe, the image clear and the descriptor accept are
//    separate nets per row half / register group (we_n 42, io_n 33, the descriptor accept 55, scan_start 37);
//  * program_cfg_addr and program_start_{base,limit,loops} load every edge (they are read only with program_cfg_we /
//    program_start_v, which keep their exact edges): no enable net over them (the launch accept drove 74);
//  * the scan column pointer has one kept copy per 2 rows (16; 32 drove srow_n 33).
module ot_hnx_prog_target #(parameter integer PCW=10)(
    input wire clk,rst_n,
    input wire [7:0] tgt,
    input wire cfg_v,
    input wire [7:0] cfg_target,
    input wire [11:0] cfg_addr,
    input wire [255:0] cfg_data,
    input wire desc_v,
    input wire [11:0] desc_base,
    input wire [12:0] desc_limit,
    input wire [15:0] desc_loops,
    input wire launch_v,
    input wire program_active,
    output reg program_cfg_we,
    output reg [PCW-1:0] program_cfg_addr,
    output reg [255:0] program_cfg_data,
    output reg program_start_v,
    output reg [PCW-1:0] program_start_base,
    output reg [PCW:0] program_start_limit,
    output reg [15:0] program_start_loops,
    output reg configured,fault
);
    localparam integer ROWS=1<<PCW, NR=ROWS/32, RB=PCW-5;
    initial if(PCW<8 || PCW>12)$fatal(1,"programme target PCW must be8..12");
    (* async_reg = "true" *) reg reset_meta;
    (* keep = "true", dont_touch = "true", ot_rst_split *) reg [3:0] rl_c;
    always @(posedge clk or negedge rst_n)
        if(!rst_n)begin reset_meta<=0;rl_c<=4'd0;end
        else begin reset_meta<=1;rl_c<={4{reset_meta}};end
    wire reset_live=rl_c[0];
    reg cv,dv,lv;
    reg [7:0] target;
    reg [7:0] tgt_q; always @(posedge clk) tgt_q<=tgt;
    wire [7:0] tid=tgt_q;
    reg [11:0] address,base;
    reg [PCW-1:0] stored_base;
    reg [255:0] data_q;
    reg [12:0] limit;
    reg [PCW:0] stored_limit;
    reg [15:0] loops,stored_loops;
    reg install_open,armed,scanning,validated,missing,img_v;
    reg sissue;                       // scan rows still being issued
    reg [PCW-1:0] scan_row;
    reg [PCW:0] scan_limit;
    reg [1:0] commit;
    wire launch_ready=armed&&validated&&!scanning&&commit==0&&!program_active&&!fault;
    always @(posedge clk)begin
        target<=cfg_target;address<=cfg_addr;data_q<=cfg_data;
        base<=desc_base;limit<=desc_limit;loops<=desc_loops;
        program_cfg_data<=data_q;
        program_cfg_addr<=address[PCW-1:0];
        program_start_base<=stored_base;program_start_limit<=stored_limit;program_start_loops<=stored_loops;
    end
    (* keep = "true", dont_touch = "true" *) reg [1:0] cv_c;   // = cv
    (* keep = "true", dont_touch = "true" *) reg [2:0] dv_c;   // = dv
    always @(posedge clk or negedge reset_live)
        if(!reset_live)begin cv<=0;dv<=0;lv<=0;cv_c<=0;dv_c<=0;end
        else begin cv<=cfg_v;dv<=desc_v;lv<=launch_v;cv_c<={2{cfg_v}};dv_c<={3{desc_v}};end
    // ---- next-state of the write strobe and of install_open (exactly the assignments of the control block below)
    wire t_hit=target==tid;
    wire cfg_hit=cv && t_hit;
    wire dsc_hit=dv && t_hit;
    wire [1:0] cfg_hit_c={cv_c[1] && t_hit,cv_c[0] && t_hit};
    wire [2:0] dsc_hit_c={dv_c[2] && t_hit,dv_c[1] && t_hit,dv_c[0] && t_hit};
    wire cfg_bad=program_active || scanning || lv || {1'b0,address}>=(13'd1<<PCW) ||
                 data_q[255:240]!=16'hc7a1 || data_q[239:224]!={4'b0,address};
    wire [1:0] we_n={cfg_hit_c[1] && !cfg_bad,cfg_hit_c[0] && !cfg_bad};   // rows 0..NR/2-1 | NR/2..
    wire dsc_bad=program_active || scanning || lv || cv || loops==0 || limit<={1'b0,base} || limit>(13'd1<<PCW);
    wire [1:0] io_n={dsc_hit_c[1] ? 1'b0 : (program_cfg_we ? 1'b1 : install_open),
                     dsc_hit_c[0] ? 1'b0 : (program_cfg_we ? 1'b1 : install_open)};
    wire dsc_ok_a=dsc_hit_c[1] && !dsc_bad, dsc_ok_b=dsc_hit_c[2] && !dsc_bad;   // stored_loops | stored_base/limit
    // scan pointer next-state
    wire reuse=validated && base==stored_base && limit==stored_limit;
    wire scan_start=dsc_hit_c[0] && !dsc_bad && !reuse;           // scan pointer (srow_n)
    wire scan_start_l=dsc_ok_b && !reuse;                          // scan_limit
    wire scan_last={1'b0,scan_row}+1'b1==scan_limit;
    always @(posedge clk)begin
        if(dsc_ok_a)stored_loops<=loops;
        if(dsc_ok_b)begin stored_base<=base[PCW-1:0];stored_limit<=limit[PCW:0];end
        if(scan_start_l)scan_limit<=limit[PCW:0];
    end
    wire [PCW-1:0] srow_n=scan_start ? base[PCW-1:0] : ((sissue && !scan_last) ? scan_row+1'b1 : scan_row);
    // ---- bitmap (no reset) with kept per-row copies
    reg [31:0] colbit_a;              // stage A: row r's bit at the scan column
    (* keep = "true", dont_touch = "true" *) reg [5*((NR+1)/2)-1:0] scol_v;   // scan column copies, one per 2 rows
    always @(posedge clk)scol_v<={((NR+1)/2){srow_n[4:0]}};
    for(genvar r=0;r<NR;r=r+1)begin:g_r
        (* keep = "true", dont_touch = "true" *) reg we_c,clr_c,row_c;
        (* keep = "true", dont_touch = "true" *) reg [31:0] col_c;
        localparam integer H=(r<NR/2)?0:1;
        reg [31:0] inst;
        always @(posedge clk)begin
            we_c<=we_n[H]; clr_c<=!io_n[H]; row_c<=address[PCW-1:5]==RB'(r);   // each <= 32 loads (used under we_c)
            col_c<=32'd1<<address[4:0];
            if(we_c)inst<=(clr_c?32'd0:inst)|({32{row_c}}&col_c);
        end
        wire [4:0] scol=scol_v[(r/2)*5+:5];
        if(r<32)begin:g_a
            always @(posedge clk)colbit_a[r]<=inst[scol];
        end
    end
    // stage B: the row group's bit (NR <= 32 rows of 32 for PCW <= 10)
    reg sv_a,sl_a,img_a,sv_b,sl_b,bit_b;
    reg [RB-1:0] srow_a;
    always @(posedge clk)begin
        srow_a<=scan_row[PCW-1:5];img_a<=img_v;
        bit_b<=img_a && colbit_a[srow_a];
    end
    initial if(PCW>10)$fatal(1,"ot_hnx_prog_target: PCW <= 10 (the hc_<q> programme is 1,024 rows)");
    always @(posedge clk or negedge reset_live)
        if(!reset_live)begin
            program_cfg_we<=0;program_start_v<=0;configured<=0;fault<=0;
            install_open<=0;armed<=0;scanning<=0;validated<=0;missing<=0;img_v<=0;sissue<=0;
            scan_row<=0;commit<=0;sv_a<=0;sl_a<=0;sv_b<=0;sl_b<=0;
        end else begin
            program_cfg_we<=0;program_start_v<=0;
            configured<=launch_ready&&!lv&&!((cv||dv)&&target==tid);
            commit<={commit[0],program_cfg_we};
            if(program_cfg_we)begin install_open<=1;img_v<=1;end
            if(cfg_hit)begin
                armed<=0;validated<=0;configured<=0;
                if(cfg_bad)fault<=1;
                else program_cfg_we<=1;
            end
            if(dsc_hit)begin
                armed<=0;validated<=0;configured<=0;install_open<=0;
                if(dsc_bad)fault<=1;
                else begin
                    armed<=1;missing<=0;
                    if(validated && base==stored_base && limit==stored_limit)begin
                        validated<=1;scanning<=0;
                    end else begin
                        scanning<=1;sissue<=1;scan_row<=base[PCW-1:0];
                    end
                end
            end
            // scan pipeline: issue (sissue) -> stage A (sv_a) -> stage B (sv_b: bit_b valid)
            sv_a<=sissue;sl_a<=sissue && scan_last;
            sv_b<=sv_a;sl_b<=sv_a && sl_a;
            if(sv_b)begin
                if(!bit_b)missing<=1;
                if(sl_b)begin
                    scanning<=0;
                    if(missing || !bit_b)fault<=1;
                    else validated<=1;
                end
            end
            if(sissue)begin
                if(scan_last)sissue<=0;
                else scan_row<=scan_row+1'b1;
            end
            if(lv && armed)begin
                armed<=0;configured<=0;
                if(!launch_ready || cv || dv)fault<=1;
                else program_start_v<=1;
            end
        end
endmodule
`default_nettype wire
