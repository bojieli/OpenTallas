`timescale 1ns/1ps
module tb_s81_seed_packet;
    reg clk=0;always #5 clk=~clk;
    reg rst_n=0,cmd_valid=0,in_valid=0,out_ready=0;
    reg [1:0] cmd_capture=0;
    reg [9:0] cmd_user=10'd513;
    reg [20:0] cmd_position=21'd1048575;
    reg [3:0] cmd_epoch=4'd13;
    reg [7:0] in_beat=0;
    reg [511:0] in_residuals=0;
    wire cmd_ready,in_ready,out_valid,busy,fault,out_last,out_corrected;
    wire [511:0] out_data;
    wire [9:0] out_user;wire [20:0] out_position;wire [3:0] out_epoch;
    wire [1:0] out_capture;wire [5:0] out_frame;
    wire capture_done;wire [1:0] capture_done_capture;
`ifdef HC_MUT_TREE
    localparam integer MT=1;
`else
    localparam integer MT=0;
`endif
`ifdef HC_MUT_ALIAS
    localparam integer MA=1;
`else
    localparam integer MA=0;
`endif
`ifdef HC_INJECT_CE
    localparam [71:0] INJ=72'd1;
`elsif HC_INJECT_UE
    localparam [71:0] INJ=72'd3;
`else
    localparam [71:0] INJ=72'd0;
`endif
    reg [511:0] inputs[0:479],expected[0:119];
    integer rank=0;
`ifdef HC_DISTRIBUTED
    wire source_valid,source_ready,source_busy,source_fault,join_busy,join_fault;
    wire [511:0] source_data;wire [9:0] source_user;wire [20:0] source_position;
    wire [3:0] source_epoch;wire [1:0] source_capture;wire [5:0] source_frame;
    wire source_last,source_ce;
    assign busy=source_busy|join_busy;assign fault=source_fault|join_fault|packet_fault|link_fault;
    wire[2:0] txv,txr,txlast,src_ready,txfault;
    wire[3*512-1:0] txdata;
    genvar g;
    generate for(g=0;g<3;g=g+1)begin:formatter
     ot_s81_seed_packet_tx #(.ENABLE(1),.MY_ID(55+g*11),.DEST_ID(500),.CAPTURE(g)) tx(
      .clk(clk),.rst_n(rst_n),.in_valid(source_valid&&source_capture==g),.in_ready(src_ready[g]),
      .in_data(source_data),.in_user(source_user),.in_position(source_position),.in_epoch(source_epoch),
      .in_capture(source_capture),.in_frame(source_frame),.in_last(source_last),
      .out_valid(txv[g]),.out_ready(txr[g]),.out_data(txdata[512*g+:512]),.out_last(txlast[g]),.fault(txfault[g]));
    end endgenerate
    assign source_ready=src_ready[source_capture];
    reg locked=0;reg[1:0] owner=0;integer normal_sent=0,normal_received=0;
    wire[1:0] choose=locked?owner:txv[0]?0:txv[1]?1:2;
    function automatic[511:0] normal_word(input integer i);
     normal_word={16{32'hdeadc0de}};normal_word[27:24]=i==0?4:5;
    endfunction
    wire link_iv=normal_sent<2?1'b1:txv[choose];wire link_ir;
    wire[511:0] pd=normal_sent<2?normal_word(normal_sent):txdata[512*choose+:512];
    wire pl=normal_sent<2?(normal_sent==1):txlast[choose];
    reg[5:0] packet_index=0;integer source_bad=0;
    wire is_header=(packet_index==0)&&(normal_sent>=2);
    wire[511:0] mutated=(source_bad==1&&is_header)?(pd^(512'd1<<12)):
                       (source_bad==2&&is_header)?((pd&~(512'd3<<208))|(512'd3<<208)):
                       (source_bad==4&&is_header&&pd[209:208]==0)?(pd^(512'd1<<210)):pd;
    wire last_mut=(source_bad==3&&packet_index==10)?1'b1:pl;
    assign txr=normal_sent<2?3'd0:({3{link_ir}}&(3'b001<<choose));
    always @(posedge clk)if(rst_n)begin
     if(normal_sent<2&&link_ir)normal_sent<=normal_sent+1;
     else begin
      if(!locked&&txv[choose])begin locked<=1;owner<=choose;end
      if(txv[choose]&&link_ir)begin
       if(pl)begin locked<=0;packet_index<=0;end else packet_index<=packet_index+1'b1;
      end
     end
    end
    wire link_ov,link_or,link_ol;wire[551:0] link_od;
    wire link_fault;wire[3:0] link_fc;wire[31:0] crc,replays;
`ifdef SEED_REPLAY
    localparam integer ERR=1;
`else
    localparam integer ERR=0;
`endif
    ot_dsrom_link_ct #(.FLIT_BYTES(69),.TX_STAGES(2),.RX_STAGES(3),.CREDITS(512),.SEQW(10),.CHANNEL_CYCLES(4),
     .ERR_PERIOD_FWD(ERR?71:0),.ERR_PERIOD_REV(ERR?131:0)) link(.clk(clk),.rst_n(rst_n),.channel_cycles(16'd4),
     .in_valid(link_iv),.in_ready(link_ir),.in_data({40'd0,mutated}),.in_last(last_mut),
     .out_valid(link_ov),.out_ready(link_or),.out_data(link_od),.out_last(link_ol),.fault(link_fault),.fault_code(link_fc),
     .credit_stalls(),.st_flits_tx(),.st_flits_rx_ok(),.st_crc_err(crc),.st_naks(),.st_replays(replays),
     .st_timeouts(),.st_retx_flits(),.st_max_replay_occ());
    wire normal_v,normal_r,normal_l;wire[511:0] normal_d;
    wire seed_v,seed_r,seed_l;wire[511:0] seed_d;wire[9:0] seed_u;wire[20:0] seed_p;
    wire[3:0] seed_e;wire[1:0] seed_c;wire[5:0] seed_f;wire rx_fault;
    wire packet_fault=rx_fault|(|txfault);
    assign normal_r=cycles%7!=0;
    ot_s81_seed_packet_rx #(.ENABLE(1),.MY_ID(500),.SRC0(55),.SRC1(66),.SRC2(77)) rx(
     .clk(clk),.rst_n(rst_n),.in_valid(link_ov),.in_ready(link_or),.in_data(link_od[511:0]),.in_last(link_ol),
     .normal_valid(normal_v),.normal_ready(normal_r),.normal_data(normal_d),.normal_last(normal_l),
     .seed_valid(seed_v),.seed_ready(seed_r),.seed_data(seed_d),.seed_user(seed_u),.seed_position(seed_p),.seed_epoch(seed_e),
     .seed_capture(seed_c),.seed_frame(seed_f),.seed_last(seed_l),.fault(rx_fault));
    always @(posedge clk)if(rst_n&&normal_v&&normal_r)begin
     if(normal_d!==normal_word(normal_received)||normal_l!=(normal_received==1))$fatal(1,"ordinary packet altered");
     normal_received=normal_received+1;
    end
    ot_dsrom_hc_seed_join #(
`ifdef HC_ECC_PIPE
      .ECC_PIPE(1),
`endif
      .READ_INJECT(INJ)) joiner(.clk(clk),.rst_n(rst_n),
      .in_valid(seed_v),.in_ready(seed_r),.in_data(seed_d),
      .in_user(seed_u),.in_position(seed_p),.in_epoch(seed_e),
      .in_capture(seed_c),.in_frame(seed_f),.in_last(seed_l),
      .busy(join_busy),.fault(join_fault),.*);
`endif
`ifdef HC_VM_READER
    wire mcv,mcr,miv,mir;wire [1:0] mcc;wire [9:0] mcu;wire [20:0] mcp;
    wire [3:0] mce;wire [7:0] mib;wire [511:0] mid;
    wire req_valid;wire [13:0] req_row;wire rb,rf;
    reg req_ready=0,rsp_valid=0;reg [511:0] rsp_data=0;
    reg pending=0;integer delay_q=0,copy_vm,row_vm,i_vm;
    reg [511:0] response_q;
    ot_dsrom_hc_input_reader reader(.clk(clk),.rst_n(rst_n),.cmd_valid(cmd_valid),.cmd_ready(cmd_ready),
      .cmd_capture(cmd_capture),.cmd_user(cmd_user),.cmd_position(cmd_position),.cmd_epoch(cmd_epoch),
      .cmd_h_row(bad==7?14'd16300:14'd512),.cmd_rank(rank[1:0]),.cmd_region_rows(bad==8?15'd319:15'd1280),
      .mean_cmd_valid(mcv),.mean_cmd_ready(mcr),.mean_cmd_capture(mcc),.mean_cmd_user(mcu),
      .mean_cmd_position(mcp),.mean_cmd_epoch(mce),
      .req_valid(req_valid),.req_ready(req_ready),.req_row(req_row),
      .rsp_valid(rsp_valid),.rsp_data(rsp_data),.rsp_fault(1'b0),
      .mean_valid(miv),.mean_ready(mir),.mean_beat(mib),.mean_residuals(mid),.busy(rb),.fault(rf));
    ot_dsrom_hc_mean_capture #(
`ifdef HC_ECC_PIPE
      .ECC_PIPE(1),
`endif
      .MUT_TREE(MT),.MUT_LAYER_ALIAS(MA),
`ifdef HC_DISTRIBUTED
      .SINGLE_CAPTURE(1),.READ_INJECT(72'd0)) u(
      .out_valid(source_valid),.out_ready(source_ready),.out_data(source_data),
      .out_user(source_user),.out_position(source_position),.out_epoch(source_epoch),
      .out_capture(source_capture),.out_frame(source_frame),.out_last(source_last),
      .out_corrected(source_ce),.busy(source_busy),.fault(source_fault),
`else
      .READ_INJECT(INJ)) u(
`endif
      .cmd_valid(mcv),.cmd_ready(mcr),.cmd_capture(mcc),.cmd_user(mcu),.cmd_position(mcp),.cmd_epoch(mce),
      .in_valid(miv),.in_ready(mir),.in_beat(mib),.in_residuals(mid),.*);
    always @(negedge clk) begin
        req_ready=cycles%5!=0&&!pending;
        rsp_valid=0;
        if(pending) begin
            if(delay_q==0) begin rsp_valid=1;rsp_data=response_q;pending=0;end
            else delay_q=delay_q-1;
        end
        if(rf) $fatal(1,"native H reader fault");
    end
    always @(posedge clk) if(req_valid&&req_ready) begin
        if(req_row<512 || req_row>=1792 || pending) $fatal(1,"native read bounds/ownership");
        copy_vm=(req_row-512)/320;row_vm=(req_row-512)%320-rank*80;
        if(row_vm<0||row_vm>=80) $fatal(1,"native read rank selection");
        for(i_vm=0;i_vm<16;i_vm=i_vm+1)
            response_q[32*i_vm+:32]={inputs[cmd_capture*160+row_vm*2+i_vm/8][128*copy_vm+16*(i_vm%8)+:16],16'd0};
        if(bad==6) response_q[0]=1;
        pending=1;delay_q=cycles%9+1;
    end
`else
`ifdef HC_DISTRIBUTED
    ot_dsrom_hc_mean_capture #(
`ifdef HC_ECC_PIPE
      .ECC_PIPE(1),
`endif
      .MUT_TREE(MT),.MUT_LAYER_ALIAS(MA),.SINGLE_CAPTURE(1)) u(
      .out_valid(source_valid),.out_ready(source_ready),.out_data(source_data),
      .out_user(source_user),.out_position(source_position),.out_epoch(source_epoch),
      .out_capture(source_capture),.out_frame(source_frame),.out_last(source_last),
      .out_corrected(source_ce),.busy(source_busy),.fault(source_fault),.*);
`else
    ot_dsrom_hc_mean_capture #(
`ifdef HC_ECC_PIPE
      .ECC_PIPE(1),
`endif
      .MUT_TREE(MT),.MUT_LAYER_ALIAS(MA),.READ_INJECT(INJ)) u(.*);
`endif
`endif
    string idir;
    integer bad=0,phase,cap,beat,nout=0,cycles=0,corrected=0;
    reg [511:0] held;reg stalled=0;
    initial begin
        if(!$value$plusargs("vectors=%s",idir)) $fatal(1,"missing vectors");
        if($value$plusargs("rank=%d",rank)) begin end
        if($value$plusargs("bad=%d",bad)) begin end
        $readmemh({idir,"/input.hex"},inputs);
        $readmemh({idir,"/expected.hex"},expected);
        if($value$plusargs("source_bad=%d",source_bad))begin end
        repeat(5) @(negedge clk);rst_n=1;
        for(phase=0;phase<3;phase=phase+1) begin
            cap=(phase==0)?2:(phase==1)?0:1;
            @(negedge clk);while(!cmd_ready) @(negedge clk);
            cmd_capture=(bad==4 && phase==0)?3:cap;
            if(bad==10) cmd_position=21'd1048576;
            if(bad==1 && phase==1) cmd_epoch=12;
            if(bad==3 && phase==1) cmd_capture=2;
            cmd_valid=1;
            @(negedge clk);cmd_valid=0;
            if(((bad==4||bad==10) && phase==0)||((bad==1||bad==3)&&phase==1)) begin
                repeat(5) @(negedge clk);
                if(!fault||out_valid||((bad==1||bad==3)&&!busy)) $fatal(1,"bad command escaped");
                $display("PASS negative command %0d retained prior ownership",bad);$finish;
            end
            for(beat=0;beat<160;beat=beat+1) begin
`ifdef HC_VM_READER
                @(negedge clk);while(rb) @(negedge clk);
                beat=159;
`else
                while(!in_ready) @(negedge clk);
                in_beat=(bad==2 && beat==1)?3:beat;
                in_residuals=inputs[cap*160+beat];
                if(bad==5 && beat==0) in_residuals[15:0]=16'h7fc0;
                in_valid=1;
                @(negedge clk);in_valid=0;
                if((bad==2 && beat==1)||(bad==5 && beat==0)) begin
                    repeat(20) @(negedge clk);
                    if(!fault||out_valid||!busy) $fatal(1,"bad beat escaped");
                    $display("PASS negative beat %0d retained ownership",bad);$finish;
                end
`endif
            end
        end
        while(nout<120) @(negedge clk);
        repeat(3) @(negedge clk);
        if(fault||busy||!cmd_ready) $fatal(1,"final ownership failed to drain");
`ifdef HC_INJECT_CE
        if(corrected!=120) $fatal(1,"correction count");
`endif
        if(normal_received!=2 || (ERR&&(crc==0||replays==0)))$fatal(1,"normal/replay coverage");
        $display("SEED_PACKET full_shape PASS frames=120 packets=3 normal=2 native553=1 crc=%0d replays=%0d cycles=%0d",crc,replays,cycles);
        $finish;
    end
    always @(negedge clk) begin
        cycles=cycles+1;
        if(cycles>40000) $fatal(1,"finite test inventory exhausted");
        out_ready=(cycles%7!=0)&&(cycles%11!=0);
`ifdef HC_INJECT_UE
        if(fault) begin
            if(nout!=0||!busy||out_valid) $fatal(1,"UE disclosed data or lost ownership");
            $display("PASS UE retained ownership and delivered no data");$finish;
        end
`else
        if(source_bad&&(rx_fault||join_fault))begin if(nout!=0)$fatal(1,"unauthenticated seed disclosed");$display("SEED_PACKET negative=%0d rejected PASS",source_bad);$finish;end
        if(fault && bad==0) $fatal(1,"unexpected fault");
`endif
    end
    always @(posedge clk) if(rst_n) begin
        if(stalled && (!out_valid || out_data!==held)) $fatal(1,"output changed under backpressure");
        stalled=out_valid&&!out_ready;held=out_data;
        if(out_valid&&out_ready) begin
            if(out_capture!==nout/40 || out_frame!==nout%40 ||
               out_user!==10'd513 || out_position!==21'd1048575 || out_epoch!==4'd13 ||
               out_last!==(nout==119) || out_data!==expected[nout])
                $fatal(1,"mean/identity/order mismatch frame %0d got=%h expected=%h",nout,out_data,expected[nout]);
            nout=nout+1;corrected=corrected+out_corrected;
        end
    end
endmodule
