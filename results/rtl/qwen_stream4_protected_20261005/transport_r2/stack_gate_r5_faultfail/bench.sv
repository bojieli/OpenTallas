`timescale 1ps/1fs
// Minimum shared-stack mechanism: full32 arbitration and literal32-PC R14
// controller, two real protected PC endpoints at14 local spans. PHY return
// pins are directed protocol stimuli, not a physical/numerical provider.
module tb_qwen_s4_stack_transport #(parameter integer WR_COUNT=130);
    reg clk=0,hclk=0,por=0,warm=1,dv=0,go=0;
    always begin #416.666 clk=1;#416.667 clk=0;end
    always #512 hclk=~hclk;
    wire dr,cf,bf,quiet;wire [7:0] fd,rd;
    reg [31:0] wv=0,pop=0;reg [767:0] ws=0;
    reg [8191:0] wd=0;reg [287:0] wt=0;
    wire [31:0] room,av,lv;wire [287:0] at;
    wire [543:0] ls;wire [255:0] lr;wire [8191:0] ld;
    wire bdv,bgo,bdr,bgr,bcb_ready;wire [18:0] bdrow;wire [10:0] bdn;
    wire [31:0] bwv,broom,bav,bardy,blv,blpop;
    wire [767:0] bws;wire [8191:0] bwd,bld;
    wire [287:0] bwt,bat;wire [543:0] bls;wire [255:0] blr;
    wire h_desc,h_go,h_dr,control_cf,control_hf;
    wire hc_desc,hc_go,go_ready;wire [2:0] hd_ord,hg_ord;
    wire [18:0] hr;wire [10:0] hn;
    wire [31:0] colv,colwe,hwv,hwr,busy;
    wire [159:0] banks,cols,wbanks,wcols;
    wire [95:0] credits;wire ctl_fault;
    wire cbv,cbwr,cbwf,cbrf;wire [3:0] cbd;
    wire [31:0] pcf,phf;
    integer phase=0,acks=0,wr_actual=0,desc_actual=0,go_actual=0;
    integer first_ack=-1;
    reg run0=0,run31=1,bad_accept=0;
    ot_qwen_s4_stack_transport #(.ENABLE(1)) dut(
        .clk(clk),.cold_por_n(por),.warm_rst_n(warm),.d_v(dv),.go(go),.d_row(19'd0),.d_n(11'd1),.d_ready(dr),
        .w_v(wv),.w_sec(ws),.w_data(wd),.w_tag(wt),.w_room(room),.wd_v(av),.wd_tag(at),.wd_accept(bad_accept?32'b0:av),
        .l_v(lv),.l_sec(ls),.l_row(lr),.l_data(ld),.l_pop(pop),
        .b_desc_v(bdv),.b_go(bgo),.b_desc_row(bdrow),.b_desc_n(bdn),.b_desc_ready(bdr),.b_go_ready(bgr),
        .b_w_v(bwv),.b_w_sec(bws),.b_w_data(bwd),.b_w_tag(bwt),.b_w_room(broom),.b_wd_v(bav),.b_wd_tag(bat),.b_wd_ready(bardy),
        .b_l_v(blv),.b_l_sec(bls),.b_l_row(blr),.b_l_data(bld),.b_l_pop(blpop),
        .b_desc_done(cbv&&!cbd[3]),.b_go_done(cbv&&cbd[3]),.b_done_ordinal(cbd[2:0]),.b_done_ready(bcb_ready),
        .b_external_fault(control_cf|cbwf|cbrf|(|pcf)),.b_busy(|busy),
        .c_fault(cf),.b_fault(bf),.quiet(quiet),.forward_debt(fd),.return_debt(rd));
    ot_qwen_s4_protected_control #(.MEM_ROWS(36)) u_control(
        .clk(clk),.hclk(hclk),.por_n(por),.warm_rst_n(1'b1),
        .d_v(bdv&&bdr),.d_rdy(bdr),.d_row(bdrow),.d_n(bdn),.go(bgo),
        .desc_v(h_desc),.desc_r(h_dr),.desc_row(hr),.desc_n(hn),.busy_all(&busy),.h_go(h_go),
        .go_ready(bgr),.desc_commit(hc_desc),.go_commit(hc_go),.desc_ordinal(hd_ord),.go_ordinal(hg_ord),
        .c_external_fault(1'b0),.h_external_fault(ctl_fault|(|phf)),.c_fault(control_cf),.h_fault(control_hf));
    ot_qwen_s4_protected_ring #(.WIDTH(4),.DEPTH(4),.KIND(7)) u_callback(
        .wr_clk(hclk),.rd_clk(clk),.por_n(por),.allow_new(1'b1),
        .wr_valid(hc_desc||hc_go),.wr_ready(cbwr),.wr_data({hc_go,hc_go?hg_ord:hd_ord}),.wr_occupancy(),.wr_fault(cbwf),
        .rd_valid(cbv),.rd_ready(bcb_ready),.rd_data(cbd),.rd_owner(),.retire(cbv&&bcb_ready),.retired(),.rd_fault(cbrf),
        .retired_source(),.retired_source_valid());
    ot_hbm_r14_stream_stack #(.ENABLE(1),.REF_MODE(1),.CRED(32),.WR_EN(1),.WQ(4),.PULLIN(0),.AQ_RD(0),.NCH(16)) ctl(
        .clk(hclk),.rst_n(por),.desc_v(h_desc&&h_dr),.desc_r(h_dr),.desc_row(hr),.desc_n(hn),.go(h_go),.next_posted(1'b0),
        .row_v(),.row_op(),.row_bank(),.row_row(),.col_v(colv),.col_bank(banks),.col_col(cols),.cred_ret(credits),
        .busy(busy),.fault(ctl_fault),.wr_v(hwv),.wr_bank(wbanks),.wr_col(wcols),.wr_r(hwr),.col_we(colwe),.wr_rd(32'b0),.col_aq());
    for(genvar p=0;p<32;p=p+1)begin:pc
        if(p==0||p==31)begin:actual
            wire cv,hwvalid;wire [23:0] csec,hsec;wire [255:0] cdata;wire [8:0] ctag;
            reg ack_v=0;reg [8:0] ack_tag=0;
            reg land_v=0,land_sent=0;
            wire run=p==0?run0:run31;
            localparam [16:0] SEC=p==0?17'd0:17'd32828;
            ot_qwen_s4_protected_pc #(.PC_ID(p),.MEM_WORDS(36*131072),.LOCAL_WIRE_SPANS(14),.ACK_BACKPRESSURE(1)) u_pc(
                .clk(clk),.hclk(hclk),.por_n(por),.warm_rst_n(1'b1),
                .l_v(blv[p]),.l_sec(bls[p*17+:17]),.l_row(blr[p*8+:8]),.l_data(bld[p*256+:256]),.l_pop(blpop[p]),
                .w_v(bwv[p]),.w_sec(bws[p*24+:24]),.w_data(bwd[p*256+:256]),.w_tag(bwt[p*9+:9]),.w_room(broom[p]),
                .wd_v(bav[p]),.wd_tag(bat[p*9+:9]),.wd_ready(bardy[p]),.c_fault(pcf[p]),
                .h_lv(land_v),.h_lsec(SEC),.h_lrow(8'd0),.h_ldata({8{32'(p+1234)}}),.h_cred(credits[p*3+:3]),
                .h_wv(hwvalid),.h_wsec(hsec),.h_hand(hwv[p]&&hwr[p]),.h_wcon(colv[p]&&colwe[p]),
                .h_cv(cv),.h_csec(csec),.h_cdata(cdata),.h_ctag(ctag),.h_av(ack_v),.h_atag(ack_tag),.h_fault(phf[p]));
            assign hwv[p]=hwvalid&&run;
            wire [9:0] j={hsec[14:6],hsec[16]};
            assign wbanks[p*5+:5]={j[9:7],j[1:0]};assign wcols[p*5+:5]=j[6:2];
            always @(posedge hclk)begin
                if(!por)begin ack_v<=0;ack_tag<=0;land_v<=0;land_sent<=0;end
                else begin
                    // The callback is driven by the real R14 WR edge and
                    // actual protected cache capture, not by queue handoff.
                    ack_v<=cv;ack_tag<=ctag;
                    land_v<=colv[p]&&!colwe[p]&&!land_sent;
                    if(colv[p]&&!colwe[p]&&!land_sent)land_sent<=1;
                end
            end
        end else begin:unused
            assign {broom[p],bav[p],blv[p],pcf[p],phf[p],hwv[p]}=0;
            assign {bat[p*9+:9],bls[p*17+:17],blr[p*8+:8],bld[p*256+:256],credits[p*3+:3],wbanks[p*5+:5],wcols[p*5+:5]}=0;
        end
    end
    always @(posedge hclk)if(por)begin
        desc_actual=desc_actual+hc_desc;go_actual=go_actual+hc_go;
        wr_actual=wr_actual+$countones(colv&colwe);
        if((hc_desc||hc_go)&&!cbwr)$fatal(1,"real controller callback lost credit");
    end
    always @(posedge clk)if(por)begin
        for(integer p=0;p<32;p=p+1)if(av[p]&&!bad_accept)begin
            if(first_ack<0)first_ack=p;
            acks=acks+1;
        end
        if(phase>0&&phase<3&&(cf||bf))$fatal(1,"healthy stack phase%0d faults=%b%b rootprotocol=%b backendprotocol=%b",phase,cf,bf,dut.active.root_protocol_bad,dut.active.backend_protocol_bad);
    end
    task issue(input integer p,input integer id,input bit pause);
        begin
            @(negedge clk);while(!room[p])@(negedge clk);
            // Actual service register: sees advertised room on this edge,
            // presents w_v for transport reservation on the NEXT edge.
            @(posedge clk);wv<=32'b1<<p;ws[p*24+:24]<=p==0?24'd0:24'd32828;
            wd[p*256+:256]<={8{32'(id+99)}};wt[p*9+:9]<=9'h100|9'(id);
            if(pause)begin @(negedge clk);warm=0;end
            @(posedge clk);wv<=0;
        end
    endtask
    initial begin
        $display("START stack32 arbiter with actual R14/2PC14span CLK833.333 H1024");
        repeat(4)@(negedge clk);por=1;wait(dr);phase=1;
        @(posedge clk);dv<=1;@(posedge clk);dv<=0;go<=1;@(posedge clk);go<=0;
        issue(0,0,0);issue(31,1,1);
        wait(acks==1);repeat(100)@(negedge clk);
        if(first_ack!=31||wr_actual!=1||desc_actual!=1||go_actual!=1||fd!=2||dut.active.fr_ret!=2||quiet)
            $fatal(1,"OOO WR callback/control retirement fd=%0d fret=%0d ACK%0d WR%0d D%0d G%0d",fd,dut.active.fr_ret,acks,wr_actual,desc_actual,go_actual);
        wait(lv[0]&&lv[31]);repeat(100)@(negedge clk);
        if(rd<2||ld[0+:256]!={8{32'd1234}}||ld[31*256+:256]!={8{32'd1265}})
            $fatal(1,"paired held landing or return credit lost");
        @(negedge clk);pop=32'h80000001;@(negedge clk);pop=0;run0=1;
        wait(acks==2);repeat(120)@(negedge clk);
        if(fd||rd||cf||bf||dut.active.ticket[0][14]||dut.active.ticket[1][14]||!quiet)$fatal(1,"warm ordered callback/grant drain");
        warm=1;phase=2;
        for(integer n=2;n<WR_COUNT;n=n+1)begin issue(n%2?31:0,n%256,0);wait(acks==n+1);end
        repeat(120)@(negedge clk);
        if(fd||rd||wr_actual!=WR_COUNT||acks!=WR_COUNT||quiet)$fatal(1,"pool wrap retained debt or advertised grant declared quiet");
        $display("PASS stack32 actual desc/GO consumeACK OOO-WR%0d orderedpool warmgrant/heldpairedrow/quiet CLK833.333 H1024",WR_COUNT);
        // Consumer rejects a real WR ACK. Do not retire the return frame or
        // erase the checked source write owner when its validated callback is0.
        phase=3;bad_accept=1;issue(0,130,0);do @(negedge clk);while(!cf);warm=0;repeat(100)@(negedge clk);
        if(!dut.active.ticket[2][14]||rd==0||quiet)$fatal(1,"rejected ACK erased real owner/debt ticket=%h rd=%0d fd=%0d cf=%b bf=%b proto=%b rootcs=%h ingressbad=%b%b rootR=%h wd=%h",dut.active.ticket[2],rd,fd,cf,bf,dut.active.root_protocol_bad,dut.active.cs,dut.active.iq_wbad,dut.active.iq_rbad,dut.active.rr_frame,av);
        $display("PASS stack32 rejected actual WR ACK preserves source ticket/return debt across warm");
        // Separate cold-POR test epoch. Corrupt the backend report-sent bit
        // itself: its checked primary must not suppress its own fault report.
        @(negedge clk);por=0;phase=0;wv=0;dv=0;go=0;pop=0;bad_accept=0;warm=1;run0=0;
        repeat(4)@(negedge clk);acks=0;first_ack=-1;wr_actual=0;desc_actual=0;go_actual=0;por=1;
        wait(dr);@(posedge clk);dv<=1;@(posedge clk);dv<=0;go<=1;@(posedge clk);go<=0;
        issue(0,131,0);
        wait(dut.active.fm[2][28]);@(negedge clk);phase=4;
        dut.active.u_bs.primary[14]=~dut.active.u_bs.primary[14];
        // Two prior control frames plus encoder2/wire41/CDC2/decoder4 and
        // root fault capture fit well inside this200-edge protocol bound.
        repeat(200)@(negedge clk);warm=0;
        if(!bf||!cf||!dut.active.ticket[3][14]||fd==0||quiet)
            $fatal(1,"backend report-sent upset hid fault/debt bf=%b cf=%b ticket=%h fd=%0d",bf,cf,dut.active.ticket[3],fd);
        $display("PASS stack32 backend checked report-sent upset reaches source and retains WR owner");$finish;
    end
endmodule
