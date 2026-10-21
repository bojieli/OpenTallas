`timescale 1ns/1ps
/*verilator lint_off BLKSEQ*/
/*verilator lint_off WIDTH*/
/*verilator lint_off UNUSED*/
module ot_sram_1r1w_1024x256_m2_r2c2_m18 (
    input  wire clk,
    input  wire r_ce_in,
    input  wire [9:0] r_addr_in,
    output reg  [255:0] rd_out,
    input  wire w_ce_in,
    input  wire [9:0] w_addr_in,
    input  wire [255:0] wd_in,
    input  wire [255:0] w_mask_in,
    input  wire [1:0] rr_en,
    input  wire [17:0] rr_addr,
    input  wire [1:0] cr_en,
    input  wire [15:0] cr_sel
);
    localparam integer WORDS = 1024;
    localparam integer BITS = 256;
    localparam integer MUX = 2;
    localparam integer AW = 10;
    localparam integer ROWS = 512;
    localparam integer NSR = 2;
    localparam integer NSC = 2;
    localparam integer PR = 514;
    localparam integer PC = 516;
    localparam integer RA = 9;
    localparam integer CB = 8;
    reg [PC-1:0] arr [0:PR-1];
    integer init_i;
    initial begin
        for (init_i = 0; init_i < PR; init_i = init_i + 1) arr[init_i] = {PC{1'b0}};
    end
    function automatic integer phys_row(input integer a);
        integer k, r;
        begin
            r = a / MUX;
            for (k = 0; k < NSR; k = k + 1)
                if (rr_en[k] && rr_addr[k*RA +: RA] == r[RA-1:0]) r = ROWS + k;
            phys_row = r;
        end
    endfunction
    function automatic integer phys_col(input integer b, input integer s);
        integer k, io;
        begin
            io = b;
            for (k = 0; k < NSC; k = k + 1)
                if (cr_en[k] && cr_sel[k*CB +: CB] == b[CB-1:0]) io = BITS + k;
            phys_col = io * MUX + s;
        end
    endfunction
    function automatic cell_read(input integer r, input integer c);
        reg v;
        begin
            v = arr[r][c];
            cell_read = v;
        end
    endfunction
    task automatic cell_write(input integer r, input integer c, input reg v);
        reg old, nv;
        begin
            old = arr[r][c];
            nv = v;
            arr[r][c] = nv;
        end
    endtask
    function automatic [65:0] decode(input integer a);
        integer r0, r1;
        reg [1:0] sel_n;
        begin
            r0 = phys_row(a);
            r1 = r0;
            sel_n = 2'd1;
            decode = {sel_n, r1[31:0], r0[31:0]};
        end
    endfunction
    function automatic [BITS-1:0] word_read(input integer a);
        integer b, s, r0, r1, n;
        reg [BITS-1:0] q;
        reg [65:0] dsel;
        begin
            dsel = decode(a);
            r0 = dsel[31:0]; r1 = dsel[63:32]; n = dsel[65:64];
            s = a % MUX;
            for (b = 0; b < BITS; b = b + 1)
                if (n == 0) q[b] = 1'b0;
                else if (n == 1) q[b] = cell_read(r0, phys_col(b, s));
                else q[b] = cell_read(r0, phys_col(b, s)) & cell_read(r1, phys_col(b, s));
            word_read = q;
        end
    endfunction
    task automatic word_write(input integer a, input [BITS-1:0] d, input [BITS-1:0] m);
        integer b, s, r0, r1, n;
        reg [65:0] dsel;
        begin
            dsel = decode(a);
            r0 = dsel[31:0]; r1 = dsel[63:32]; n = dsel[65:64];
            s = a % MUX;
            for (b = 0; b < BITS; b = b + 1)
                if (m[b] && n != 0) begin
                    cell_write(r0, phys_col(b, s), d[b]);
                    if (n == 2) cell_write(r1, phys_col(b, s), d[b]);
                end
        end
    endtask
    always @(posedge clk) begin
        if (r_ce_in) rd_out <= word_read(r_addr_in);
        if (w_ce_in) word_write(w_addr_in, wd_in, w_mask_in);
    end
endmodule
/*verilator lint_on BLKSEQ*/
/*verilator lint_on WIDTH*/
/*verilator lint_on UNUSED*/
`timescale 1ns/1ps
`default_nettype none
module hfd_hgi_vm_calendar_m18 #(parameter integer RMUT=0) (
    input wire clk,clk_cap,clk_mem,rst_n,cfg_we,
    input wire [9:0] cfg_addr,
    input wire [255:0] cfg_data,
    input wire start_v,
    input wire [9:0] start_base,
    input wire [10:0] start_limit,
    input wire [15:0] start_loops,
    output wire calendar_v,active,done,fault,
    output wire [31:0] ordinal,
    output wire [9:0] client_seq,
    output wire [4:0] response_enable,
    output wire [9:0] response_seq,
    output wire [7:0] bank_enable,
    output wire [23:0] bank_client,
    output wire [1:0] hub_ring_enable,
    output wire [5:0] hub_ring_client,
    output wire [7:0] rslot_v,
    output wire [7:0] wslot_v,
    output wire [23:0] rslot,
    output wire [23:0] wslot,
    output wire [1:0] ring_tx_enable,
    output wire [5:0] ring_tx_source,
    output wire replay_enable,
    output wire replay_source,
    output wire [23:0] lg_local_read,
    output wire [23:0] lg_local_write
);
    (* async_reg = "true" *) reg rst_meta,rst_sync;
    always @(posedge clk or negedge rst_n)
        if(!rst_n)begin rst_meta<=1'b0;rst_sync<=1'b0;end
        else begin rst_meta<=1'b1;rst_sync<=rst_meta;end
    wire local_rst_n=(RMUT==1)?rst_n:rst_sync;
    wire [186:0] calendar;
    ot_vms_calendar_static_xcap_m18 #(.W(187)) u_programme (
        .clk(clk),.clk_cap(clk_cap),.clk_mem(clk_mem),.rst_n(local_rst_n),.cfg_we(cfg_we),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
        .start_v(start_v),.start_base(start_base),.start_limit(start_limit),.start_loops(start_loops),
        .calendar(calendar),.calendar_v(calendar_v),.ordinal(ordinal),.active(active),.done(done),.fault(fault));
    assign client_seq=calendar[0+:10];
    assign response_enable=calendar[10+:5];
    assign response_seq=calendar[15+:10];
    assign bank_enable=calendar[25+:8];
    assign bank_client=calendar[33+:24];
    assign hub_ring_enable=calendar[57+:2];
    assign hub_ring_client=calendar[59+:6];
    assign rslot_v=calendar[65+:8];
    assign wslot_v=calendar[73+:8];
    assign rslot=calendar[81+:24];
    assign wslot=calendar[105+:24];
    assign ring_tx_enable=calendar[129+:2];
    assign ring_tx_source=calendar[131+:6];
    assign replay_enable=calendar[137+:1];
    assign replay_source=calendar[138+:1];
    assign lg_local_read=calendar[139+:24];
    assign lg_local_write=calendar[163+:24];
endmodule
`default_nettype wire
`timescale 1ns/1ps
`default_nettype none
module hfd_hgi_vm_calendar_f20 #(parameter integer RMUT=0) (
    input wire clk,clk_cap,clk_mem,clk_tgt,rst_n,
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
    output wire tgt_configured,tgt_fault,
    output wire calendar_v,active,done,fault,
    output wire [31:0] ordinal,
    output wire [9:0] client_seq,
    output wire [4:0] response_enable,
    output wire [9:0] response_seq,
    output wire [7:0] bank_enable,
    output wire [23:0] bank_client,
    output wire [1:0] hub_ring_enable,
    output wire [5:0] hub_ring_client,
    output wire [7:0] rslot_v,
    output wire [7:0] wslot_v,
    output wire [23:0] rslot,
    output wire [23:0] wslot,
    output wire [1:0] ring_tx_enable,
    output wire [5:0] ring_tx_source,
    output wire replay_enable,
    output wire replay_source,
    output wire [23:0] lg_local_read,
    output wire [23:0] lg_local_write
); /*verilator hier_block*/
    wire p_we,p_sv; wire [9:0] p_wa,p_sb; wire [255:0] p_wd; wire [10:0] p_sl; wire [15:0] p_lp;
    ot_static_program_target_m18 #(.TARGET(8'hff),.PCW(10),.TGT_PIN(1),.CAP_CLK(1)) u_target(
        .clk(clk_tgt),.clk_cap(clk_cap),.rst_n(rst_n),.tgt(tgt),.cfg_v(cfg_v),.cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
        .desc_v(desc_v),.desc_base(desc_base),.desc_limit(desc_limit),.desc_loops(desc_loops),.launch_v(launch_v),
        .program_active(active),.program_cfg_we(p_we),.program_cfg_addr(p_wa),.program_cfg_data(p_wd),
        .program_start_v(p_sv),.program_start_base(p_sb),.program_start_limit(p_sl),.program_start_loops(p_lp),
        .configured(tgt_configured),.fault(tgt_fault));
    hfd_hgi_vm_calendar_m18 #(.RMUT(RMUT)) u_calendar(
        .clk(clk),.clk_cap(clk_cap),.clk_mem(clk_mem),.rst_n(rst_n),.cfg_we(p_we),.cfg_addr(p_wa),.cfg_data(p_wd),
        .start_v(p_sv),.start_base(p_sb),.start_limit(p_sl),.start_loops(p_lp),
        .calendar_v(calendar_v),.active(active),.done(done),.fault(fault),.ordinal(ordinal),
        .client_seq(client_seq),.response_enable(response_enable),.response_seq(response_seq),.bank_enable(bank_enable),
        .bank_client(bank_client),.hub_ring_enable(hub_ring_enable),.hub_ring_client(hub_ring_client),.rslot_v(rslot_v),
        .wslot_v(wslot_v),.rslot(rslot),.wslot(wslot),.ring_tx_enable(ring_tx_enable),.ring_tx_source(ring_tx_source),
        .replay_enable(replay_enable),.replay_source(replay_source),.lg_local_read(lg_local_read),.lg_local_write(lg_local_write));
endmodule
`default_nettype wire
`timescale 1ns/1ps
`default_nettype none
module ot_static_program_target_m18 #(parameter [7:0] TARGET=8'd48,parameter integer PCW=10,parameter integer TGT_PIN=0,
                                  parameter integer CAP_CLK=0)(
    input wire clk,rst_n,
    input wire clk_cap,    
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
    localparam integer ROWS=1<<PCW;
    initial if(PCW<8 || PCW>12)$fatal(1,"programme target PCW must be8..12");
    (* async_reg = "true" *) reg reset_meta,reset_live;
    always @(posedge clk or negedge rst_n)
        if(!rst_n)begin reset_meta<=0;reset_live<=0;end
        else begin reset_meta<=1;reset_live<=reset_meta;end
    reg cv,dv,lv;
    reg [7:0] target;
    wire clk_in=(CAP_CLK!=0)?clk_cap:clk;
    reg [7:0] tgt_q; always @(posedge clk_in) tgt_q<=tgt;
    wire [7:0] tid=(TGT_PIN!=0)?tgt_q:TARGET;
    reg [11:0] address,base;
    reg [PCW-1:0] stored_base;
    reg [255:0] data_q;
    reg [12:0] limit;
    reg [PCW:0] stored_limit;
    reg [15:0] loops,stored_loops;
    reg [ROWS-1:0] installed;
    reg install_open,armed,scanning,validated,missing;
    reg [PCW-1:0] scan_row;
    reg [PCW:0] scan_limit;
    reg [1:0] commit;
    wire launch_ready=armed&&validated&&!scanning&&commit==0&&!program_active&&!fault;
    always @(posedge clk_in)begin
        target<=cfg_target;address<=cfg_addr;data_q<=cfg_data;
        base<=desc_base;limit<=desc_limit;loops<=desc_loops;
    end
    always @(posedge clk_in or negedge reset_live)
        if(!reset_live)begin cv<=0;dv<=0;lv<=0;end
        else begin cv<=cfg_v;dv<=desc_v;lv<=launch_v;end
    always @(posedge clk or negedge reset_live)
        if(!reset_live)begin
            program_cfg_we<=0;program_start_v<=0;configured<=0;fault<=0;
            installed<=0;install_open<=0;armed<=0;scanning<=0;validated<=0;missing<=0;
            scan_row<=0;scan_limit<=0;commit<=0;
        end else begin
            program_cfg_we<=0;program_start_v<=0;
            configured<=launch_ready&&!lv&&!((cv||dv)&&target==tid);
            commit<={commit[0],program_cfg_we};
            if(program_cfg_we)begin
                if(!install_open)installed<=({{(ROWS-1){1'b0}},1'b1}<<program_cfg_addr);
                else installed[program_cfg_addr]<=1'b1;
                install_open<=1;
            end
            if(cv && target==tid)begin
                armed<=0;validated<=0;configured<=0;
                if(program_active || scanning || lv || {1'b0,address}>=(13'd1<<PCW) ||
                   data_q[255:240]!=16'hc7a1 || data_q[239:224]!={4'b0,address})fault<=1;
                else begin program_cfg_we<=1;program_cfg_addr<=address[PCW-1:0];program_cfg_data<=data_q;end
            end
            if(dv && target==tid)begin
                armed<=0;validated<=0;configured<=0;install_open<=0;
                if(program_active || scanning || lv || cv || loops==0 || limit<={1'b0,base} || limit>(13'd1<<PCW))fault<=1;
                else begin
                    stored_base<=base[PCW-1:0];stored_limit<=limit[PCW:0];stored_loops<=loops;
                    armed<=1;missing<=0;
                    if(validated && base==stored_base && limit==stored_limit)begin
                        validated<=1;scanning<=0;
                    end else begin
                        scanning<=1;scan_row<=base[PCW-1:0];scan_limit<=limit[PCW:0];
                    end
                end
            end
            if(scanning)begin
                if(!installed[scan_row])missing<=1;
                if({1'b0,scan_row}+1'b1==scan_limit)begin
                    scanning<=0;
                    if(missing || !installed[scan_row])fault<=1;
                    else validated<=1;
                end else scan_row<=scan_row+1'b1;
            end
            if(lv && armed)begin
                armed<=0;configured<=0;
                if(!launch_ready || cv || dv)fault<=1;
                else begin
                    program_start_v<=1;program_start_base<=stored_base;
                    program_start_limit<=stored_limit;program_start_loops<=stored_loops;
                end
            end
        end
endmodule
`default_nettype wire
`timescale 1ns/1ps
`default_nettype none
module ot_vms_calendar_static_xcap_m18 #(
    parameter integer W=146,
    parameter integer MUT=0  
)(
    input wire clk,clk_cap,clk_mem,rst_n,
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
    output reg active,done,fault
);
    initial if(W<1 || W>223)$fatal(1,"VM calendar width must fit protected programme payload");
    reg cfg_we_q,start_v_q;
    reg [9:0] cfg_addr_q,start_base_q;
    reg [255:0] cfg_data_q;
    reg [10:0] start_limit_q;
    reg [15:0] start_loops_q;
    always @(posedge clk_cap)begin
        cfg_addr_q<=cfg_addr;cfg_data_q<=cfg_data;
        start_base_q<=start_base;start_limit_q<=start_limit;start_loops_q<=start_loops;
    end
    always @(posedge clk_cap or negedge rst_n)
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
    ot_sram_1r1w_1024x256_m2_r2c2_m18 u_program(
        .clk(clk_mem),.r_ce_in(running),.r_addr_in(pc),.rd_out(macro_data),
        .w_ce_in(cfg_we_q && !busy && !start_v_q),.w_addr_in(cfg_addr_q),.wd_in(cfg_data_q),.w_mask_in({256{1'b1}}),
        .rr_en(2'b00),.rr_addr(18'd0),.cr_en(2'b00),.cr_sel(16'd0));
    always @(posedge clk)begin
        captured<=macro_data;
        pc0<=pc;pc1<=pc0;ord0<=issued;ord1<=ord0;
        calendar<=valid1 && word_ok?captured[W-1:0]:{W{1'b0}};
        ordinal<=ord1;
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
endmodule
`default_nettype wire
