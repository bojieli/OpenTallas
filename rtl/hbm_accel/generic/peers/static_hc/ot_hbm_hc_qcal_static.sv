`timescale 1ns/1ps
`default_nettype none
// QHUB-S1 10-19 (kit hbm_hcq_hub_s1; SAFE-DESIGN item 4): ot_vms_calendar_static (rtl/hbm_accel/generic/vm/static, left
// byte-identical for its VM users) plus ONE extra output register gb = the hc_<q> gathered-reader launch bounds check
// (ot_hgi_hc_gathered_mix_reader_static bounds_ok over calendar fields npos [26:23], base [42:27], stride [58:43],
// in an exact shallow form, see gb_last),
// computed from the captured programme word on the SAME edge the calendar register loads it.  When the word is not
// valid the calendar is zero (no launch), so gb is only ever consumed together with its own word: bit-identical to the
// reader's internal check, one register earlier (the calendar -> issue_sector cone is cut, zero added edges).
// Everything else below is ot_vms_calendar_static verbatim (module renamed).
// Programme SRAM is written before launch. A launch executes the fixed range
// [base,limit), repeated loops times. Nothing observes datapath arrival/ready.
// Each programme word: magic[255:240]=c7a1, PC identity[233:224], calendar[W-1:0];
// all reserved bits zero. The independent capture rung is the macro's only load.
module ot_hbm_hc_qcal_static #(
    parameter integer W=146,
    parameter integer MUT=0, // 1 wrong wrap PC, 2 extra cycle at loop boundary
    // HBM-HCBANK6 10-20 (QHUB SAFE 2, native32): FAN32 1 = same edges and values, every driver <= 32 loads: the programme
    // word check is registered beside the capture (wok_c copies of word_ok computed from the macro output and pc0 on the
    // edge captured / pc1 load), valid1 has kept copies, and the start-accept select has one kept start copy per loaded
    // register group (pc / base / limit / loops).  gl = GLC kept copies of calendar bit 22 (the gathered-reader launch,
    // same D), for the reader's per-group launch selects.  Default 0 = unchanged (gl = calendar[22] replicated).
    parameter integer FAN32=0,
    parameter integer GLC=12,
    parameter integer GPC=10,
    parameter integer NWS=9
)(
    input wire clk,rst_n,
    input wire cfg_we,
    input wire [9:0] cfg_addr,
    input wire [255:0] cfg_data,
    input wire start_v,
    input wire [9:0] start_base,
    input wire [10:0] start_limit,
    input wire [15:0] start_loops,
    output reg [W-1:0] calendar,
    output reg calendar_v,
    output reg [31:0] ordinal,
    output reg active,done,fault,
    output reg gb,
    output wire [GLC-1:0] gl,
    // FAN32: kept copies of the gather-phase bit (calendar[21], GPC) and the result-store lane selects: wsel[(j*8+b)*NWS+k]
    // = (sector j of the store maps to LG lane b) for calendar fields base [75:60] / position [78:76] (k = copy)
    output wire [GPC-1:0] gp,
    output wire [2:0] gr,               // FAN32: kept copies of calendar bit 0 (residual launch)
    output wire [24*NWS-1:0] wsel
);
    initial if(W<1 || W>223)$fatal(1,"VM calendar width must fit protected programme payload");
    reg cfg_we_q,start_v_q;
    reg [9:0] cfg_addr_q,start_base_q;
    reg [255:0] cfg_data_q;
    reg [10:0] start_limit_q;
    reg [15:0] start_loops_q;
    always @(posedge clk)begin
        cfg_addr_q<=cfg_addr;cfg_data_q<=cfg_data;
        start_base_q<=start_base;start_limit_q<=start_limit;start_loops_q<=start_loops;
    end
    always @(posedge clk or negedge rst_n)
        if(!rst_n)begin cfg_we_q<=0;start_v_q<=0;end
        else begin cfg_we_q<=cfg_we;start_v_q<=start_v;end
    reg running;
    reg [9:0] pc,base;
    reg [10:0] limit;
    reg [15:0] loops_left;
    reg [31:0] issued;
    reg valid0,valid1,last0,last1;
    reg [9:0] pc0,pc1;
    reg [31:0] ord0,ord1;
    reg [255:0] captured;
    wire [255:0] macro_data;
    wire busy=running|valid0|valid1;
    wire legal_start=start_limit_q>{1'b0,start_base_q} && start_limit_q<=11'd1024 && start_loops_q!=0;
    wire final_issue=({1'b0,pc}+11'd1==limit) && loops_left==1;
    wire word_ok=captured[255:240]==16'hc7a1 && captured[233:224]==pc1 &&
                 captured[239:234]==0 && captured[223:W]==0;
    ot_sram_1r1w_1024x256_m2_r2c2 u_program(
        .clk(clk),.r_ce_in(running),.r_addr_in(pc),.rd_out(macro_data),
        .w_ce_in(cfg_we_q && !busy && !start_v_q),.w_addr_in(cfg_addr_q),.wd_in(cfg_data_q),.w_mask_in({256{1'b1}}),
        .rr_en(2'b00),.rr_addr(18'd0),.cr_en(2'b00),.cr_sel(16'd0));
    // gathered-reader bounds over the captured word (same expression as the reader's bounds_ok)
    wire [3:0] gb_npos=captured[26:23];
    wire [15:0] gb_base=captured[42:27],gb_stride=captured[58:43];
    // shallow exact form (gate 10-19: the multiply form was captured -> gb 688 ps / 19 levels): the check is true only
    // for npos 1..8, i.e. n1 = npos - 1 in 0..7, so (npos-1)*stride is three masked shifted addends (no 33-b product)
    // and last < 2^19: last < 32768 <=> last[18:15] == 0.  Outside 1..8 the npos term is false in both forms.
    // COL-HC 10-21 (gate native census, mapped: captured[23..25] QN 76..80 loads -- ABC folded npos - 1 into the 3 x 19-b
    // masks): n1 on KEPT wires (ABC boundary), each bit then drives one 19-b mask.  Same function, same edge.
    (* keep = "true" *) wire [2:0] gb_n1=3'(gb_npos-4'd1);
    wire [18:0] gb_last=19'(gb_base)+19'(2)+({19{gb_n1[0]}}&19'(gb_stride))+({19{gb_n1[1]}}&(19'(gb_stride)<<1))
                       +({19{gb_n1[2]}}&(19'(gb_stride)<<2));
    wire gb_d=gb_npos>=1&&gb_npos<=8&&!gb_base[15]&&gb_last[18:15]==4'd0&&gb_last[14:13]==gb_base[14:13];
    generate if(FAN32==0)begin:g_f0
    // Payload, ordinal and address identity have dedicated, nonreset rungs.
    always @(posedge clk)begin
        captured<=macro_data;
        pc0<=pc;pc1<=pc0;ord0<=issued;ord1<=ord0;
        calendar<=valid1 && word_ok?captured[W-1:0]:{W{1'b0}};
        ordinal<=ord1;
        gb<=gb_d;
    end
    always @(posedge clk or negedge rst_n)
        if(!rst_n)begin
            running<=0;pc<=0;base<=0;limit<=0;loops_left<=0;issued<=0;
            valid0<=0;valid1<=0;last0<=0;last1<=0;calendar_v<=0;
            active<=0;done<=0;fault<=0;
        end else begin
            valid0<=running;valid1<=valid0;last0<=running && final_issue;last1<=last0;
            calendar_v<=valid1;
            active<=busy;done<=valid1 && last1;
            if(valid1 && !word_ok)fault<=1;
            if(cfg_we_q && (busy || start_v_q))fault<=1;
            if(start_v_q)begin
                if(busy || cfg_we_q || !legal_start)fault<=1;
                else begin
                    running<=1;pc<=start_base_q;base<=start_base_q;limit<=start_limit_q;
                    loops_left<=start_loops_q;issued<=0;
                end
            end
            if(running)begin
                issued<=issued+1;
                if({1'b0,pc}+11'd1==limit)begin
                    if(loops_left==1)running<=0;
                    else begin
                        pc<=base + ((MUT==1)?10'd1:10'd0);
                        loops_left<=loops_left-1;
                        if(MUT==2)running<=0;
                    end
                end else pc<=pc+1;
            end
        end
        assign gl={GLC{calendar[22]}};
        assign gp={GPC{calendar[21]}};
        assign gr={3{calendar[0]}};
        wire [2:0] f0_b=calendar[62:60], f0_p=calendar[78:76];
        for(genvar j=0;j<3;j=j+1)begin:g_ws0
            wire [2:0] s=3'(f0_b+f0_p*3+j);
            for(genvar b=0;b<8;b=b+1)begin:g_b
                assign wsel[(j*8+b)*NWS+:NWS]={NWS{s==3'(b)}};
            end
        end
    end else begin:g_f32
        (* keep = "true", dont_touch = "true" *) reg [7:0] wok_c,v1_c;   // 0..3 calendar groups, 4 gl, 5 gp, 6 wsel, 7 gr
        (* keep = "true", dont_touch = "true" *) reg [3:0] sv_c;
        (* keep = "true", dont_touch = "true" *) reg [GLC-1:0] gl_c;
        wire wok_d=macro_data[255:240]==16'hc7a1 && macro_data[233:224]==pc0 && macro_data[239:234]==0 && macro_data[223:W]==0;
        always @(posedge clk)begin
            captured<=macro_data;
            pc0<=pc;pc1<=pc0;ord0<=issued;ord1<=ord0;
            wok_c<={8{wok_d}};
            for(integer i=0;i<W;i=i+1)calendar[i]<=v1_c[(i*4)/W]&&wok_c[(i*4)/W]&&captured[i];
            gl_c<={GLC{v1_c[4]&&wok_c[4]&&captured[22]}};
            ordinal<=ord1;
            gb<=gb_d;
        end
        assign gl=gl_c;
        (* keep = "true", dont_touch = "true" *) reg [GPC-1:0] gp_c;
        (* keep = "true", dont_touch = "true" *) reg [24*NWS-1:0] ws_c;
        wire okw=v1_c[6]&&wok_c[6];
        wire [2:0] cb=okw?captured[62:60]:3'd0, cpp=okw?captured[78:76]:3'd0;
        always @(posedge clk)begin
            gp_c<={GPC{v1_c[5]&&wok_c[5]&&captured[21]}};
            for(integer j=0;j<3;j=j+1)
                for(integer b=0;b<8;b=b+1)
                    ws_c[(j*8+b)*NWS+:NWS]<={NWS{3'(cb+cpp*3+j)==3'(b)}};
        end
        assign gp=gp_c;
        (* keep = "true", dont_touch = "true" *) reg [2:0] gr_c;
        always @(posedge clk) gr_c<={3{v1_c[7]&&wok_c[7]&&captured[0]}};
        assign gr=gr_c;
        assign wsel=ws_c;
        wire [3:0] acc;
        for(genvar k=0;k<4;k=k+1)begin:g_acc
            assign acc[k]=sv_c[k] && !busy && !cfg_we_q && legal_start;
        end
        always @(posedge clk or negedge rst_n)
            if(!rst_n)begin v1_c<=0;sv_c<=0;end
            else begin v1_c<={8{valid0}};sv_c<={4{start_v}};end
        always @(posedge clk or negedge rst_n)
            if(!rst_n)begin
                running<=0;issued<=0;valid0<=0;valid1<=0;last0<=0;last1<=0;calendar_v<=0;active<=0;done<=0;fault<=0;
            end else begin
                valid0<=running;valid1<=valid0;last0<=running && final_issue;last1<=last0;
                calendar_v<=valid1;
                active<=busy;done<=valid1 && last1;
                if(v1_c[0] && !wok_c[0])fault<=1;
                if(cfg_we_q && (busy || start_v_q))fault<=1;
                if(start_v_q && (busy || cfg_we_q || !legal_start))fault<=1;
                if(acc[0])begin running<=1;issued<=0;end
                if(running)begin
                    issued<=issued+1;
                    if({1'b0,pc}+11'd1==limit)begin
                        if(loops_left==1)running<=0;
                        else if(MUT==2)running<=0;
                    end
                end
            end
        // per-group register updates (same next state as the FAN32 0 block; start accept and running are exclusive)
        always @(posedge clk or negedge rst_n)
            if(!rst_n)pc<=0;
            else if(acc[0])pc<=start_base_q;
            else if(running)begin
                if({1'b0,pc}+11'd1==limit)begin if(loops_left!=1)pc<=base + ((MUT==1)?10'd1:10'd0); end
                else pc<=pc+1;
            end
        always @(posedge clk or negedge rst_n) if(!rst_n)base<=0; else if(acc[1])base<=start_base_q;
        always @(posedge clk or negedge rst_n) if(!rst_n)limit<=0; else if(acc[2])limit<=start_limit_q;
        always @(posedge clk or negedge rst_n)
            if(!rst_n)loops_left<=0;
            else if(acc[3])loops_left<=start_loops_q;
            else if(running && {1'b0,pc}+11'd1==limit && loops_left!=1)loops_left<=loops_left-1;
    end endgenerate
endmodule
`default_nettype wire
