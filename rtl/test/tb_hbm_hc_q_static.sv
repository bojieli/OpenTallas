`timescale 1ns/1ps
`default_nettype none
// Bench for ot_hbm_hc_q_static (die hc_<q>) with its real die neighbours: four ot_hgi_sfu_lg_pair_leaf
// (hc_<q>0..3) and the far HC tap ot_hbm_vm_lg_static_split_term #(18,15) (lg_<q>_2). Behind the tap a
// fixed-latency 8-bank VM model (sector s -> bank s[2:0]) answers at the reserved edge, as the VM chain does.
// The tap selects (local_read/local_write) are driven like calendar_<q>: exactly on the edges the HC
// programme issues. The HC programme is loaded and launched through ot_static_program_target (TARGET 108).
// Golden: residual waves == VM sectors, gathered mixes == VM words, stored results land at their sectors.
// MUT (plusarg +MUT=n): 1/2/3 = ot_hbm_hc_q_static mutants, 4 = tap advances its return reservation.
module tb_hbm_hc_q_static;
    parameter integer MUT=0;
    localparam integer TAP_MUT=(MUT==4)?2:0, DUT_MUT=(MUT>=1&&MUT<=3)?MUT:0;
    localparam integer VM_RD=15, VM_WR=12;
    reg clk=0,rst_n=0;
    always #1 clk=~clk;
    // host F20 broadcast toward the programme target
    reg cfg_v=0,desc_v=0,launch_v=0;
    reg [7:0] cfg_target=0;
    reg [11:0] cfg_addr=0,desc_base=0;
    reg [255:0] cfg_data=0;
    reg [12:0] desc_limit=0;
    reg [15:0] desc_loops=0;
    wire p_we,p_start,t_conf,t_fault;
    wire [9:0] p_addr,p_base;
    wire [255:0] p_data;
    wire [10:0] p_limit;
    wire [15:0] p_loops;
    wire prog_active,prog_done,dut_fault;
    ot_static_program_target #(.TARGET(8'd108),.PCW(10)) tgt(
        .clk(clk),.rst_n(rst_n),.cfg_v(cfg_v),.cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
        .desc_v(desc_v),.desc_base(desc_base),.desc_limit(desc_limit),.desc_loops(desc_loops),.launch_v(launch_v),
        .program_active(prog_active),.program_cfg_we(p_we),.program_cfg_addr(p_addr),.program_cfg_data(p_data),
        .program_start_v(p_start),.program_start_base(p_base),.program_start_limit(p_limit),
        .program_start_loops(p_loops),.configured(t_conf),.fault(t_fault));
    wire [135:0] c_rq,t_rq,n_rq;
    wire [2247:0] c_wq,t_wq,n_wq;
    wire [2055:0] c_rr,t_rr;
    wire [7:0] c_wd,t_wd,bank_fault;
    wire xv,rdone,gv,gdone;
    wire [9:0] xword;
    wire [8191:0] xwave;
    wire [4:0] grow;
    wire [2:0] gpos;
    wire [31:0] gdata;
    reg result_v=0;
    reg [2:0] result_position=0;
    reg [767:0] result=0;
    ot_hbm_hc_q_static #(.MUT(DUT_MUT)) dut(
        .clk(clk),.rst_n(rst_n),.cfg_we(p_we),.cfg_addr(p_addr),.cfg_data(p_data),.start_v(p_start),
        .start_base(p_base),.start_limit(p_limit),.start_loops(p_loops),
        .lg_rq(c_rq),.lg_wq(c_wq),.lg_rr(c_rr),.lg_w_done(c_wd),
        .x_wave_v(xv),.x_wave_word(xword),.x_wave(xwave),.residual_done(rdone),
        .gathered_mix_v(gv),.gathered_mix_row(grow),.gathered_mix_pos(gpos),.gathered_mix_data(gdata),.gather_done(gdone),
        .result_v(result_v),.result_position(result_position),.result(result),
        .program_active(prog_active),.program_done(prog_done),.fault(dut_fault));
    for(genvar k=0;k<4;k=k+1)begin:pair
        ot_hgi_sfu_lg_pair_leaf leaf(.clk(clk),.rst_n(rst_n),
            .c_rq(c_rq[k*34+:34]),.c_wq(c_wq[k*562+:562]),.c_rr(c_rr[k*514+:514]),.c_w_done(c_wd[k*2+:2]),
            .lg_rq(t_rq[k*34+:34]),.lg_wq(t_wq[k*562+:562]),.lg_rr(t_rr[k*514+:514]),.lg_w_done(t_wd[k*2+:2]));
    end
    // calendar_<q> stand-in: the tap select is high exactly on the HC programme's issue edges
    reg [7:0] sel_r,sel_w;
    always @*for(integer b=0;b<8;b=b+1)begin sel_r[b]=t_rq[b*17+16];sel_w[b]=t_wq[b*281+280];end
    wire [2055:0] n_rr;
    wire [7:0] n_wd;
    ot_hbm_vm_lg_static_split_term #(.READ_RETURN(18),.WRITE_RETURN(15),.MUT(TAP_MUT)) tap(
        .clk({8{clk}}),.rst_n(rst_n),.local_rq(t_rq),.local_wq(t_wq),.local_read(sel_r),.local_write(sel_w),
        .near_rq(n_rq),.near_wq(n_wq),.near_rr(n_rr),.near_w_done(n_wd),.local_rr(t_rr),.local_w_done(t_wd),
        .bank_fault(bank_fault));
    // VM model: 8 banks x 4096 rows, fixed read/write return
    reg [255:0] vm[0:32767];
    reg [256:0] rpipe[0:7][0:VM_RD-1];
    reg wpipe[0:7][0:VM_WR-1];
    for(genvar b=0;b<8;b=b+1)begin:vmb
        assign n_rr[b*257+:257]=rpipe[b][VM_RD-1];
        assign n_wd[b]=wpipe[b][VM_WR-1];
        always @(posedge clk)begin
            rpipe[b][0]<=n_rq[b*17+16]?{1'b1,vm[n_rq[b*17+:15]]}:257'd0;
            for(integer i=1;i<VM_RD;i=i+1)rpipe[b][i]<=rpipe[b][i-1];
            wpipe[b][0]<=n_wq[b*281+280];
            for(integer i=1;i<VM_WR;i=i+1)wpipe[b][i]<=wpipe[b][i-1];
            if(n_wq[b*281+280])begin
                if(n_wq[b*281+264+:3]!=3'(b))$display("TB: write sector bank mismatch");
                for(integer w=0;w<8;w=w+1)if(n_wq[b*281+w])vm[n_wq[b*281+264+:15]][w*32+:32]<=n_wq[b*281+8+w*32+:32];
            end
            if(n_rq[b*17+16]&&n_rq[b*17+:3]!=3'(b))$display("TB: read sector bank mismatch");
        end
    end
    // engine tail stand-in: the result for the store word is presented one edge ahead (compiler alignment)
    reg [767:0] res_val[0:7];
    always @(posedge clk)begin
        result_v<=dut.programme.valid0&&dut.programme.macro_data[59];
        result_position<=dut.programme.macro_data[78:76];
        result<=res_val[dut.programme.macro_data[78:76]];
    end
    // programme
    localparam integer RNPOS=2, RBASE=256, GNPOS=3, GBASE=8192, GSTRIDE=40, SBASE=12288;
    reg [78:0] prog[0:1023];
    integer n_words, errors, waves, mixes;
    reg [255:0] snap[0:32767];
    function automatic [255:0] word(input integer pc, input [78:0] c);
        word=0;word[255:240]=16'hc7a1;word[233:224]=10'(pc);word[78:0]=c;
    endfunction
    task automatic f20_cfg(input [7:0] target,input [11:0] a,input [255:0] d);
        @(negedge clk);cfg_v=1;cfg_target=target;cfg_addr=a;cfg_data=d;@(negedge clk);cfg_v=0;
    endtask
    initial begin
        errors=0;waves=0;mixes=0;
        for(integer s=0;s<32768;s=s+1)begin vm[s]={$random,$random,$random,$random,$random,$random,$random,$random};snap[s]=vm[s];end
        for(integer s=0;s<8;s=s+1)res_val[s]={24{$random}};
        for(integer i=0;i<1024;i=i+1)prog[i]=0;
        // residual: 2 positions = 640 issue edges from word 0; gather window after residual returns drain
        prog[0][0]=1;prog[0][4:1]=RNPOS;prog[0][20:5]=RBASE;
        for(integer i=700;i<700+GNPOS*24+40;i=i+1)prog[i][21]=1;
        prog[700][22]=1;prog[700][26:23]=GNPOS;prog[700][42:27]=GBASE;prog[700][58:43]=GSTRIDE;
        for(integer p=0;p<4;p=p+1)begin prog[860+p*2][59]=1;prog[860+p*2][75:60]=SBASE;prog[860+p*2][78:76]=3'(p);end
        n_words=900;
        repeat(5)@(negedge clk);rst_n=1;repeat(3)@(negedge clk);
        for(integer i=0;i<n_words;i=i+1)f20_cfg(8'd108,12'(i),word(i,prog[i]));
        f20_cfg(8'd109,12'd0,word(0,79'd1)); // another target: must be ignored
        @(negedge clk);desc_v=1;cfg_target=8'd108;desc_base=0;desc_limit=13'(n_words);desc_loops=1;@(negedge clk);desc_v=0;
        repeat(3)@(negedge clk);launch_v=1;@(negedge clk);launch_v=0;
        wait(prog_done);repeat(60)@(negedge clk);
        // stores
        for(integer p=0;p<4;p=p+1)for(integer j=0;j<3;j=j+1)
            if(vm[SBASE+p*3+j]!==res_val[p][j*256+:256])begin errors=errors+1;if(errors<5)$display("store mismatch pos %0d sector %0d",p,j);end
        for(integer s=0;s<32768;s=s+1)if((s<SBASE||s>=SBASE+12)&&vm[s]!==snap[s])begin errors=errors+1;if(errors<5)$display("stray write sector %0d",s);end
        if(waves!=RNPOS*80)begin errors=errors+1;$display("waves %0d expected %0d",waves,RNPOS*80);end
        if(mixes!=GNPOS*24)begin errors=errors+1;$display("mixes %0d expected %0d",mixes,GNPOS*24);end
        if(dut_fault||t_fault||(|bank_fault))begin errors=errors+1;$display("fault dut=%0d target=%0d bank=%b",dut_fault,t_fault,bank_fault);end
        if(errors==0)$display("TB_HBM_HC_Q_STATIC PASS MUT=%0d waves=%0d mixes=%0d stores=12",MUT,waves,mixes);
        else $display("TB_HBM_HC_Q_STATIC FAIL MUT=%0d errors=%0d",MUT,errors);
        $finish;
    end
    always @(posedge clk)begin
        if(xv)begin
            waves<=waves+1;
            for(integer j=0;j<32;j=j+1)if(xwave[j*256+:256]!==snap[RBASE+xword*32+j])begin
                errors=errors+1;if(errors<5)$display("wave %0d sector %0d mismatch",xword,j);end
        end
        if(gv)begin
            mixes<=mixes+1;
            if(gdata!==snap[GBASE+gpos*GSTRIDE+grow/8][(grow%8)*32+:32])begin
                errors=errors+1;if(errors<5)$display("mix pos %0d row %0d mismatch",gpos,grow);end
        end
    end
    initial begin #400000;$display("TB_HBM_HC_Q_STATIC FAIL MUT=%0d timeout",MUT);$finish;end
endmodule
`default_nettype wire
