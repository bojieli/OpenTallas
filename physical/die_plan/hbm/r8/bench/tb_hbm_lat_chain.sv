`timescale 1ns/1ps
`default_nettype none
// DIE-HBM-92-LAT 11-08: HBM VM local-group latency chain bench for one hub quadrant, REAL RTL end to end except the
// VM bank array.  Per local group k (VM bank pair 2k, 2k+1), as on the die:
//   SFU VM bridge (ot_hgi_sfu_vm_static_bridge, sfucore_<q>.__cut_ctl)  -C_rq_k->  SFU tap leaf sfu_<q>k
//   (ot_hgi_sfu_lg_pair_tap_leaf)  -far->  SU LG tap su_<q>k.g_tap_r8b.u_tap (ot_hbm_vm_lg_pair_tap)  -N_rq_k->
//   VM bank model  -N_rr_k->  SU tap  ->  SFU tap  -C_rr_k->  bridge;
//   HC quadrant client hc_<q>.u_q (ot_hbm_hc_q_static, programme loaded through its F20 target)  -H_rq_k->  HC term
//   tap leaf hc_<q>k (ot_hgi_sfu_lg_pair_tap_leaf_term)  -near->  SFU tap far ports  -> ... ->  -H_rr_k->  hc_q.
// Leg delays (the landed register stages of the bound die, after the R8 / loop pads) are ot_hdc_delay lines; the
// calendar_<q> stand-in raises each tap's local_read/local_write on the edge its own client's request reaches the tap
// (as built; the event lands the calendar legs with the request legs at one added delay, LGREQ join).
// VM bank model: read sector -> data BRD edges after near_rq at the bank pins, write commit -> w_done BWD edges.
// MODE 0 = SFU bridge prefetch + drain traffic, 1 = HC programme (residual waves, gathered mixes, result stores),
// 2 = SU slice local reads/writes on the SU tap (checked by the SU tap's own reservation fault).  PASS = no fault anywhere and every datum checked.
module tb_hbm_lat_chain;
    parameter integer MODE=0, NCYC=3000;
    parameter integer BRD=7, BWD=4;                         // bank pins: read data / write done edges
    parameter [31:0] DNRQ=0, DNRR=0, DCRQ=0, DCRR=0, DHRQ=0, DHRR=0;   // 4 x 8-bit leg delays (LG k at [8k+:8])
    parameter [31:0] SU_RR={4{8'd11}}, SU_WR={4{8'd8}}, SFU_RR={4{8'd15}}, SFU_WR={4{8'd12}},
                     HC_RR={4{8'd19}}, HC_WR={4{8'd16}};
    parameter integer BR_RR=14, BR_WR=11;                   // bridge READ_RETURN / WRITE_RETURN
    parameter integer HQ_RD=23, HQ_GP=23, HQ_DONE=19;       // hc_q RD_CAPTURE / GATHER_PHASE / DONE_LAT
    localparam integer LWB=15, XWB=4;
    reg clk=0,rst_n=0;
    always #1 clk=~clk;
    integer tcyc=0; always @(posedge clk) tcyc<=tcyc+1;
    integer errors=0, reads=0, writes=0, waves=0, mixes=0, i, c;
    // ---------------------------------------------------------------- VM bank array (8 banks, sector s -> bank s[2:0])
    reg [255:0] vm[0:32767];
    reg [255:0] snap[0:32767];
    // ---------------------------------------------------------------- SFU bridge
    reg [7:0] prefetch_v=0; reg [127:0] prefetch_sector=0; reg [15:0] prefetch_group=0;
    reg [8*LWB-1:0] prefetch_local_addr=0; reg [7:0] prefetch_scalar=0; reg [23:0] prefetch_word=0; reg [95:0] scalar_addr=0;
    wire [135:0] b_rq; wire [2055:0] b_rr; wire [7:0] stage_v; wire [15:0] stage_group; wire [8*LWB-1:0] stage_addr;
    wire [2047:0] stage_data; wire [63:0] stage_mask; wire [3:0] scalar_load; wire [95:0] scalar_load_addr; wire [127:0] scalar_data;
    reg [1:0] drain_v=0, drain_round_bf16=0, drain_result_v=0; reg [31:0] drain_vm_sector=0; reg [511:0] drain_data=0;
    wire [2247:0] b_wq; wire [7:0] b_wd; wire br_fault;
    ot_hgi_sfu_vm_static_bridge #(.LWB(LWB),.READ_RETURN(BR_RR),.WRITE_RETURN(BR_WR)) bridge(
        .clk(clk),.rst_n(rst_n),.clk_lg({4{clk}}),.rst_lg_n({4{rst_n}}),.prefetch_v(prefetch_v),.prefetch_sector(prefetch_sector),
        .prefetch_group(prefetch_group),.prefetch_local_addr(prefetch_local_addr),.prefetch_scalar(prefetch_scalar),
        .prefetch_word(prefetch_word),.scalar_addr(scalar_addr),.local_rq(b_rq),.local_rr(b_rr),.stage_v(stage_v),
        .stage_group(stage_group),.stage_addr(stage_addr),.stage_data(stage_data),.stage_mask(stage_mask),.scalar_load(scalar_load),
        .scalar_load_addr(scalar_load_addr),.scalar_data(scalar_data),.drain_v(drain_v),.drain_round_bf16(drain_round_bf16),
        .drain_vm_sector(drain_vm_sector),.drain_result_v(drain_result_v),.drain_data(drain_data),.local_wq(b_wq),
        .local_w_done(b_wd),.fault(br_fault));
    always @(posedge clk) drain_result_v <= drain_v;
    // ---------------------------------------------------------------- HC quadrant client
    reg cfg_v=0,desc_v=0,launch_v=0; reg [7:0] cfg_target=0; reg [11:0] cfg_addr=0,desc_base=0; reg [255:0] cfg_data=0;
    reg [12:0] desc_limit=0; reg [15:0] desc_loops=0;
    wire t_conf,prog_active,prog_done,hq_fault;
    wire [135:0] h_rq; wire [2247:0] h_wq; wire [2055:0] h_rr; wire [7:0] h_wd;
    wire xv_l,rdone,gv,gdone,xv,rx_fault; wire [9:0] xword_l,xword; wire [8192/XWB-1:0] xwave_l; wire [1:0] xbeat;
    wire [8191:0] xwave; wire [4:0] grow; wire [2:0] gpos; wire [31:0] gdata;
    reg result_v=0; reg [2:0] result_position=0; reg [767:0] result=0;
    ot_hbm_hc_q_static #(.RD_CAPTURE(HQ_RD),.GATHER_PHASE(HQ_GP),.DONE_LAT(HQ_DONE),.XW_BEATS(XWB)) hcq(
        .clk(clk),.rst_n(rst_n),.tgt(8'd108),.cfg_v(cfg_v),.cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
        .desc_v(desc_v),.desc_base(desc_base),.desc_limit(desc_limit),.desc_loops(desc_loops),.launch_v(launch_v),
        .configured(t_conf),.lg_rq(h_rq),.lg_wq(h_wq),.lg_rr(h_rr),.lg_w_done(h_wd),
        .x_wave_v(xv_l),.x_wave_word(xword_l),.x_wave(xwave_l),.x_wave_beat(xbeat),.residual_done(rdone),
        .gathered_mix_v(gv),.gathered_mix_row(grow),.gathered_mix_pos(gpos),.gathered_mix_data(gdata),.gather_done(gdone),
        .result_v(result_v),.result_position(result_position),.result(result),
        .program_active(prog_active),.program_done(prog_done),.fault(hq_fault));
    ot_hbm_hc_xw_rx_static #(.BEATS(XWB)) rx(.clk(clk),.rst_n(rst_n),.x_v(xv_l),.x_beat(xbeat),.x_word(xword_l),
        .x_data(xwave_l),.wave_v(xv),.wave_word(xword),.wave(xwave),.fault(rx_fault));
    // ---------------------------------------------------------------- SU slice stand-in (MODE 2)
    reg [135:0] s_rq=0; reg [2247:0] s_wq=0; wire [2055:0] s_rr; wire [7:0] s_wd;
    // ---------------------------------------------------------------- per local group chain
    wire [3:0] f_sfu,f_su,f_hc;
    for(genvar k=0;k<4;k=k+1)begin:lg
        localparam integer NRQ=DNRQ[8*k+:8], NRR=DNRR[8*k+:8], CRQ=DCRQ[8*k+:8], CRR=DCRR[8*k+:8],
                           HRQ=DHRQ[8*k+:8], HRR=DHRR[8*k+:8];
        // client legs
        wire [33:0] c_rq,hc_rq; wire [561:0] c_wq,hc_wq; wire [513:0] c_rr,hc_rr; wire [1:0] c_wd,hc_wd;
        ot_hdc_delay #(.W(34),.D(CRQ),.RESET(1)) u_crq(.clk(clk),.rst_n(rst_n),.d(b_rq[34*k+:34]),.q(c_rq));
        ot_hdc_delay #(.W(562),.D(CRQ),.RESET(1)) u_cwq(.clk(clk),.rst_n(rst_n),.d(b_wq[562*k+:562]),.q(c_wq));
        ot_hdc_delay #(.W(514),.D(CRR),.RESET(1)) u_crr(.clk(clk),.rst_n(rst_n),.d(c_rr),.q(b_rr[514*k+:514]));
        ot_hdc_delay #(.W(2),.D(CRR),.RESET(1)) u_cwd(.clk(clk),.rst_n(rst_n),.d(c_wd),.q(b_wd[2*k+:2]));
        ot_hdc_delay #(.W(34),.D(HRQ),.RESET(1)) u_hrq(.clk(clk),.rst_n(rst_n),.d(h_rq[34*k+:34]),.q(hc_rq));
        ot_hdc_delay #(.W(562),.D(HRQ),.RESET(1)) u_hwq(.clk(clk),.rst_n(rst_n),.d(h_wq[562*k+:562]),.q(hc_wq));
        ot_hdc_delay #(.W(514),.D(HRR),.RESET(1)) u_hrr(.clk(clk),.rst_n(rst_n),.d(hc_rr),.q(h_rr[514*k+:514]));
        ot_hdc_delay #(.W(2),.D(HRR),.RESET(1)) u_hwd(.clk(clk),.rst_n(rst_n),.d(hc_wd),.q(h_wd[2*k+:2]));
        // HC term tap (outermost) -> SFU tap far ports -> SU tap far ports -> bank
        wire [33:0] hn_rq,sn_rq,un_rq,bk_rq; wire [561:0] hn_wq,sn_wq,un_wq,bk_wq;
        wire [513:0] hn_rr,sn_rr,un_rr,bk_rr; wire [1:0] hn_wd,sn_wd,un_wd,bk_wd;
        reg [1:0] cal_hr,cal_hw,cal_sr,cal_sw,cal_ur,cal_uw;
        ot_hgi_sfu_lg_pair_tap_leaf_term #(.READ_RETURN(HC_RR[8*k+:8]),.WRITE_RETURN(HC_WR[8*k+:8])) hc(
            .clk(clk),.rst_n(rst_n),.c_rq(hc_rq),.c_wq(hc_wq),.c_rr(hc_rr),.c_w_done(hc_wd),
            .local_read(cal_hr),.local_write(cal_hw),.near_rq(hn_rq),.near_wq(hn_wq),.near_rr(hn_rr),.near_w_done(hn_wd),
            .fault(f_hc[k]));
        ot_hgi_sfu_lg_pair_tap_leaf #(.READ_RETURN(SFU_RR[8*k+:8]),.WRITE_RETURN(SFU_WR[8*k+:8])) sfu(
            .clk(clk),.rst_n(rst_n),.c_rq(c_rq),.c_wq(c_wq),.c_rr(c_rr),.c_w_done(c_wd),
            .local_read(cal_sr),.local_write(cal_sw),.far_rq(hn_rq),.far_wq(hn_wq),.far_rr(hn_rr),.far_w_done(hn_wd),
            .near_rq(sn_rq),.near_wq(sn_wq),.near_rr(sn_rr),.near_w_done(sn_wd),.fault(f_sfu[k]));
        ot_hbm_vm_lg_pair_tap #(.READ_RETURN(SU_RR[8*k+:8]),.WRITE_RETURN(SU_WR[8*k+:8])) su(
            .clk(clk),.rst_n(rst_n),.local_rq(s_rq[34*k+:34]),.far_rq(sn_rq),.local_wq(s_wq[562*k+:562]),.far_wq(sn_wq),
            .local_read(cal_ur),.local_write(cal_uw),.near_rq(un_rq),.near_wq(un_wq),.near_rr(un_rr),.near_w_done(un_wd),
            .local_rr(s_rr[514*k+:514]),.far_rr(sn_rr),.local_w_done(s_wd[2*k+:2]),.far_w_done(sn_wd),.fault(f_su[k]));
        // calendar_<q> stand-in: each tap's select on the edge its own client's request is at the tap's local pins
        always @*begin
            for(integer b=0;b<2;b=b+1)begin
                cal_hr[b]=hc.l_rq[17*b+16]; cal_hw[b]=hc.l_wq[281*b+280];
                cal_sr[b]=sfu.l_rq[17*b+16]; cal_sw[b]=sfu.l_wq[281*b+280];
                cal_ur[b]=s_rq[34*k+17*b+16]; cal_uw[b]=s_wq[562*k+281*b+280];
            end
        end
        // N legs + bank pair
        ot_hdc_delay #(.W(34),.D(NRQ),.RESET(1)) u_nrq(.clk(clk),.rst_n(rst_n),.d(un_rq),.q(bk_rq));
        ot_hdc_delay #(.W(562),.D(NRQ),.RESET(1)) u_nwq(.clk(clk),.rst_n(rst_n),.d(un_wq),.q(bk_wq));
        ot_hdc_delay #(.W(514),.D(NRR),.RESET(1)) u_nrr(.clk(clk),.rst_n(rst_n),.d(bk_rr),.q(un_rr));
        ot_hdc_delay #(.W(2),.D(NRR),.RESET(1)) u_nwd(.clk(clk),.rst_n(rst_n),.d(bk_wd),.q(un_wd));
        for(genvar b=0;b<2;b=b+1)begin:bank
            reg [256:0] rp[0:BRD-1]; reg wp[0:BWD-1];
            assign bk_rr[257*b+:257]=rp[BRD-1];
            assign bk_wd[b]=wp[BWD-1];
            initial begin for(integer i=0;i<BRD;i=i+1)rp[i]=0; for(integer i=0;i<BWD;i=i+1)wp[i]=0; end
            always @(posedge clk)begin
                rp[0]<=bk_rq[17*b+16]?{1'b1,vm[bk_rq[17*b+:15]]}:257'd0;
                for(integer i=1;i<BRD;i=i+1)rp[i]<=rp[i-1];
                wp[0]<=bk_wq[281*b+280];
                for(integer i=1;i<BWD;i=i+1)wp[i]<=wp[i-1];
                if(bk_rq[17*b+16]&&bk_rq[17*b+:3]!=3'(2*k+b))begin errors=errors+1;$display("TB read sector bank mismatch");end
                if(bk_wq[281*b+280])begin
                    if(bk_wq[281*b+264+:3]!=3'(2*k+b))begin errors=errors+1;$display("TB write sector bank mismatch");end
                    if(MODE!=0)for(integer w=0;w<8;w=w+1)if(bk_wq[281*b+w])
                        vm[bk_wq[281*b+264+:15]][w*32+:32]<=bk_wq[281*b+8+w*32+:32];
                end
            end
        end
    end
    // ---------------------------------------------------------------- checks
    reg [15:0] sec;
    wire any_fault=br_fault|hq_fault|rx_fault|(|f_sfu)|(|f_su)|(|f_hc);
    integer first_fault=-1;
    always @(posedge clk) if(rst_n && any_fault && first_fault<0) first_fault<=tcyc;
    // MODE 0: staged data == VM sector (stage_addr carries the sector's low 15 bits)
    always @(negedge clk) if(MODE==0) for(i=0;i<8;i=i+1) if(stage_v[i])begin
        reads=reads+1;
        if(stage_data[256*i+:256]!==vm[stage_addr[LWB*i+:LWB]])begin errors=errors+1; if(errors<5)$display("stage %0d data mismatch t=%0d",i,tcyc);end
    end
    // MODE 1: HC programme waves / mixes (tb_hbm_hc_q_static golden)
    // programme (tb_hbm_hc_q_static form) scheduled for the round trip: the residual returns drain before the gather
    // window, the window covers GNPOS periods + the gather return edges, stores after it (compiler schedule)
    localparam integer RNPOS=1, RBASE=256, GNPOS=2, GBASE=8192, GSTRIDE=40, SBASE=12288;
    localparam integer GPER=(HQ_GP>=24)?HQ_GP+1:24, G0=RNPOS*320+HQ_RD+8, GW=GNPOS*GPER+HQ_GP+16, S0=G0+GW+4;
    reg [78:0] prog[0:1023];
    reg [767:0] res_val[0:7];
    always @(posedge clk)begin
        result_v<=hcq.programme.valid0&&hcq.programme.macro_data[59];
        result_position<=hcq.programme.macro_data[78:76];
        result<=res_val[hcq.programme.macro_data[78:76]];
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
    function automatic [255:0] word(input integer pc, input [78:0] cw);
        word=0;word[255:240]=16'hc7a1;word[233:224]=10'(pc);word[78:0]=cw;
    endfunction
    task automatic f20_cfg(input [7:0] target,input [11:0] a,input [255:0] d);
        @(negedge clk);cfg_v=1;cfg_target=target;cfg_addr=a;cfg_data=d;@(negedge clk);cfg_v=0;
    endtask
    integer n_words;
    initial begin
        for(integer s=0;s<32768;s=s+1)begin vm[s]={$random,$random,$random,$random,$random,$random,$random,$random};snap[s]=vm[s];end
        for(integer s=0;s<8;s=s+1)res_val[s]={24{$random}};
        repeat(5)@(negedge clk);rst_n=1;repeat(6)@(negedge clk);
        if(MODE==0)begin
            for(c=0;c<NCYC;c=c+1)begin
                @(negedge clk);
                for(i=0;i<8;i=i+1)begin
                    prefetch_v[i]=(($random&3)==0)&&(c<NCYC-400);
                    sec=($random&16'h7ff8)|i; prefetch_sector[16*i+:16]=sec; prefetch_local_addr[LWB*i+:LWB]=sec[14:0];
                end
                drain_v=(c<NCYC-400)?($random&3):0; drain_vm_sector=$random&32'h7fff7fff; drain_data={16{$random}};
                if(drain_v==2'b11&&drain_vm_sector[2:0]==drain_vm_sector[18:16])drain_v=2'b01;
                if(drain_v!=0)writes=writes+1;
            end
            prefetch_v=0; drain_v=0; repeat(300)@(negedge clk);
        end else if(MODE==2)begin
            for(c=0;c<NCYC;c=c+1)begin
                @(negedge clk);
                for(i=0;i<8;i=i+1)begin
                    sec=($random&16'h7ff8)|i;
                    s_rq[17*i+:17]={(($random&3)==0)&&(c<NCYC-400),sec};
                    s_wq[281*i+:281]={(($random&7)==0)&&(c<NCYC-400),sec,256'd0,8'h00};   // mask 0: VM unchanged
                    if(s_wq[281*i+280])writes=writes+1;
                end
            end
            s_rq=0; s_wq=0; repeat(300)@(negedge clk);
        end else begin
            for(integer p=0;p<1024;p=p+1)prog[p]=0;
            prog[0][0]=1;prog[0][4:1]=RNPOS;prog[0][20:5]=RBASE;
            for(integer p=G0;p<G0+GW;p=p+1)prog[p][21]=1;
            prog[G0][22]=1;prog[G0][26:23]=GNPOS;prog[G0][42:27]=GBASE;prog[G0][58:43]=GSTRIDE;
            for(integer p=0;p<4;p=p+1)begin prog[S0+p*2][59]=1;prog[S0+p*2][75:60]=SBASE;prog[S0+p*2][78:76]=3'(p);end
            n_words=S0+12;
            if(n_words>1024)begin errors=errors+1;$display("programme %0d words > 1024",n_words);end
            for(integer p=0;p<n_words;p=p+1)f20_cfg(8'd108,12'(p),word(p,prog[p]));
            @(negedge clk);desc_v=1;cfg_target=8'd108;desc_base=0;desc_limit=13'(n_words);desc_loops=1;@(negedge clk);desc_v=0;
            for(integer warm=0;warm<n_words+8 && !t_conf;warm++)@(negedge clk);
            if(!t_conf)begin errors=errors+1;$display("HC programme not configured");end
            launch_v=1;@(negedge clk);launch_v=0;
            wait(prog_done);repeat(HQ_DONE+400)@(negedge clk);
            for(integer p=0;p<4;p=p+1)for(integer j=0;j<3;j=j+1)
                if(vm[SBASE+p*3+j]!==res_val[p][j*256+:256])begin errors=errors+1;if(errors<5)$display("store mismatch pos %0d sector %0d",p,j);end
            if(waves!=RNPOS*80)begin errors=errors+1;$display("waves %0d expected %0d",waves,RNPOS*80);end
            if(mixes!=GNPOS*24)begin errors=errors+1;$display("mixes %0d expected %0d",mixes,GNPOS*24);end
        end
        if(first_fault>=0)errors=errors+1;
        $display("LATCHAIN %s MODE=%0d errors=%0d first_fault=%0d (bridge %0d hc_q %0d rx %0d sfu %b su %b hc %b) reads=%0d writes=%0d waves=%0d mixes=%0d BR=%0d/%0d HQ=%0d/%0d/%0d",
            errors==0?"PASS":"FAIL",MODE,errors,first_fault,br_fault,hq_fault,rx_fault,f_sfu,f_su,f_hc,reads,writes,waves,mixes,
            BR_RR,BR_WR,HQ_RD,HQ_GP,HQ_DONE);
        $finish;
    end
    initial begin #2000000;$display("LATCHAIN FAIL MODE=%0d timeout",MODE);$finish;end
endmodule
`default_nettype wire
