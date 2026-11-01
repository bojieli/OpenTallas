`timescale 1ps/1fs
module tb_hbm_phy_slices_model;
    reg clk=0; always begin #512 clk=1; #512 clk=0; end
    reg rst_n=0;
    reg [31:0] row_v=0,col_v=0,col_we=0;
    reg [95:0] row_op=0;
    reg [159:0] row_bank=0,col_bank=0,col_col=0;
    reg [607:0] row_row=0;
    reg [8191:0] col_data=0;
    reg [1023:0] col_strb=0;
    wire [31:0] ref_v,slice_v;
    wire [8191:0] ref_d,slice_d;
    integer mutant=0,cyc=0,read_due=-1,checks=0,returned=0;
    reg [255:0] expected[0:31];
    wire [3071:0] slice1_write=col_data[10*256+:12*256] ^ ((mutant==1 && col_we[10]) ? 3072'd1 : 3072'd0);
    ot_hbm3e_phy_rc_e8p5 #(.IMAGE_KEY("fixture"),.REQUIRE_INITIALIZED(1)) reference_model(.*,.dram_rvalid(ref_v),.dram_rdata(ref_d));
    ot_hbm3e_phy_rc_e8p5_pc0_9 #(.IMAGE_KEY("fixture")) slice0(
        .clk(clk),.rst_n(rst_n),.row_v(row_v[0+:10]),.row_op(row_op[0+:30]),.row_bank(row_bank[0+:50]),.row_row(row_row[0+:190]),
        .col_v(col_v[0+:10]),.col_we(col_we[0+:10]),.col_bank(col_bank[0+:50]),.col_col(col_col[0+:50]),.col_data(col_data[0+:2560]),.col_strb(col_strb[0+:320]),
        .dram_rvalid(slice_v[0+:10]),.dram_rdata(slice_d[0+:2560]));
    ot_hbm3e_phy_rc_e8p5_pc10_21 #(.IMAGE_KEY("fixture")) slice1(
        .clk(clk),.rst_n(rst_n),.row_v(row_v[10+:12]),.row_op(row_op[30+:36]),.row_bank(row_bank[50+:60]),.row_row(row_row[190+:228]),
        .col_v(col_v[10+:12]),.col_we(col_we[10+:12]),.col_bank(col_bank[50+:60]),.col_col(col_col[50+:60]),.col_data(slice1_write),.col_strb(col_strb[320+:384]),
        .dram_rvalid(slice_v[10+:12]),.dram_rdata(slice_d[2560+:3072]));
    ot_hbm3e_phy_rc_e8p5_pc22_31 #(.IMAGE_KEY("fixture")) slice2(
        .clk(clk),.rst_n(rst_n),.row_v(row_v[22+:10]),.row_op(row_op[66+:30]),.row_bank(row_bank[110+:50]),.row_row(row_row[418+:190]),
        .col_v(col_v[22+:10]),.col_we(col_we[22+:10]),.col_bank(col_bank[110+:50]),.col_col(col_col[110+:50]),.col_data(col_data[5632+:2560]),.col_strb(col_strb[704+:320]),
        .dram_rvalid(slice_v[22+:10]),.dram_rdata(slice_d[5632+:2560]));
    always @(posedge clk) begin
        cyc=cyc+1;
        if(rst_n && col_v!=0 && col_we==0) read_due=cyc+23;
        #1;
        if(rst_n)begin
            checks=checks+1;
            if(ref_v!==slice_v) $fatal(1,"PHY_SLICE_MODEL FAIL valid cycle%0d",cyc);
            if((cyc==read_due) !== (&slice_v)) $fatal(1,"PHY_SLICE_MODEL FAIL latency cycle%0d due%0d",cyc,read_due);
            for(integer p=0;p<32;p=p+1)if(slice_v[p])begin
                if(slice_d[p*256+:256]!==ref_d[p*256+:256] || slice_d[p*256+:256]!==expected[p])
                    $fatal(1,"PHY_SLICE_MODEL FAIL payload pc%0d cycle%0d",p,cyc);
                returned=returned+1;
            end
        end
    end
    task automatic tick(input integer n);repeat(n)@(negedge clk);endtask
    initial begin
        void'($value$plusargs("MUT=%d",mutant));
        for(integer p=0;p<32;p=p+1)expected[p]={8{32'h12340000+32'(p)}};
        tick(3);rst_n=1;row_v='1;
        for(integer p=0;p<32;p=p+1)row_op[3*p+:3]=3'd1;
        tick(1);row_v=0;tick(20);
        col_v='1;tick(1);col_v=0;tick(26);
        // Masked writes retain every unwritten byte of the initialized image.
        for(integer p=0;p<32;p=p+1)begin
            col_data[p*256+:256]={8{32'hdead0000+32'(p)}};
            col_strb[p*32+:32]=32'h55555555;
            for(integer b=0;b<32;b=b+1)if((b%2)==0)expected[p][b*8+:8]=col_data[p*256+b*8+:8];
        end
        col_v='1;col_we='1;tick(1);col_v=0;col_we=0;tick(16);
        col_v='1;tick(1);col_v=0;tick(26);
        // PRE + per-bank refresh preserve memory contents but close the row.
        row_v='1;row_op=0;tick(1);row_v=0;tick(18);
        row_v='1;for(integer p=0;p<32;p=p+1)row_op[3*p+:3]=3'd6;
        tick(1);row_v=0;tick(198);
        row_v='1;for(integer p=0;p<32;p=p+1)row_op[3*p+:3]=3'd1;
        tick(1);row_v=0;tick(20);
        col_v='1;tick(1);col_v=0;tick(26);
        if(checks<300 || returned!=96)$fatal(1,"PHY_SLICE_MODEL FAIL vacuous checks%0d returned%0d",checks,returned);
        $display("PHY_SLICE_MODEL PASS checks=%0d returned=%0d pcs=32 read_latency=23 phy_period_ps=1024 added_on_die_cycles=0",checks,returned);
        $finish;
    end
endmodule
