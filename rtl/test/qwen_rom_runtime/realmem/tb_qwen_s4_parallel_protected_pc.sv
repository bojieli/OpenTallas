`timescale 1ps/1fs
module tb_qwen_s4_parallel_protected_pc;
    reg clk=0,hclk=0,por=0,warm=1;
    always begin #416.666 clk=1;#416.667 clk=0;end
    always #512 hclk=~hclk;
    reg lv=0,pop=0,wv=0,av=0,hand=0,con=0,ack=0;
    reg [16:0] sec=0;reg [7:0] row=0;reg [255:0] data=0;
    reg [23:0] ws=0;reg [255:0] wd=0;reg [8:0] wt=0,at=0;
    wire lvalid,room,awv,cf,hf,hwv,cv,cq,hq;
    wire [16:0] ls;wire [7:0] lr;wire [255:0] ld,cd;
    wire [23:0] hs,cs;wire [8:0] awt,ct;wire [2:0] cred;
    integer credits=0;
    ot_qwen_s4_parallel_protected_pc #(.ENABLE(1),.MEM_WORDS(36*131072),.LOCAL_WIRE_SPANS(14),.LANDING_RSEL(1)) dut(
        .clk(clk),.hclk(hclk),.por_n(por),.warm_rst_n(warm),
        .l_v(lvalid),.l_sec(ls),.l_row(lr),.l_data(ld),.l_pop(pop),
        .w_v(wv),.w_sec(ws),.w_data(wd),.w_tag(wt),.w_room(room),
        .wd_v(awv),.wd_tag(awt),.wd_accept(ack),.c_fault(cf),
        .h_lv(lv),.h_lsec(sec),.h_lrow(row),.h_ldata(data),.h_cred(cred),
        .h_wv(hwv),.h_wsec(hs),.h_hand(hand),.h_wcon(con),.h_cv(cv),
        .h_csec(cs),.h_cdata(cd),.h_ctag(ct),.h_av(av),.h_atag(at),.h_fault(hf),.c_quiet(cq),.h_quiet(hq));
    always @(posedge hclk) if(por)credits=credits+cred;
    initial begin repeat(2048)@(negedge hclk);$fatal(1,"finite test transaction failed to drain");end
    task cold;
        begin por=0;warm=1;lv=0;wv=0;av=0;pop=0;hand=0;con=0;ack=0;
            repeat(4)@(negedge clk);por=1;repeat(32)@(negedge hclk);credits=0;end
    endtask
    task land;
        begin @(negedge hclk);sec=0;row=35;data={8{32'h01234567}};lv=1;
            @(negedge hclk);lv=0;end
    endtask
    task write_one;
        begin @(negedge clk);wait(room);ws=128;wd={8{32'h76543210}};wt=9'd37;wv=1;
            @(negedge clk);wv=0;end
    endtask
    task finish_write;
        begin wait(hwv);@(negedge hclk);if(hs!=128)$fatal(1,"write identity");hand=1;
            @(negedge hclk);hand=0;con=1;@(negedge hclk);con=0;
            if(!cv||cs!=128||ct!=37||cd!={8{32'h76543210}})$fatal(1,"WR capture");end
    endtask
    task send_ack(input [8:0] tag);
        begin @(negedge hclk);at=tag;av=1;@(negedge hclk);av=0;end
    endtask
    initial begin
        cold();
        if(!cq||!hq)$fatal(1,"initial debt quiet");
        fork
            land();
            begin
                wait(dut.active.u_endpoint.u_l.sector_lanes.lane[0].u_raw.lw_bin!=0);
                #0.001;
                // Simultaneous coded halves: one CE in distinct72bit pieces.
                dut.active.u_endpoint.u_l.sector_lanes.lane[0].u_raw.lmem[0][3]=
                    ~dut.active.u_endpoint.u_l.sector_lanes.lane[0].u_raw.lmem[0][3];
                dut.active.u_endpoint.u_l.sector_lanes.lane[1].u_raw.lmem[0][3]=
                    ~dut.active.u_endpoint.u_l.sector_lanes.lane[1].u_raw.lmem[0][3];
            end
        join
        write_one();wait(lvalid);repeat(20)@(negedge clk);
        if(ls!=0||lr!=35||ld!={8{32'h01234567}}||cf||hf)$fatal(1,"simultaneous lane CE/identity");
        warm=0;repeat(10)@(negedge clk);
        if(room||cq||hq||!lvalid||ld!={8{32'h01234567}})$fatal(1,"warm held/debt");
        finish_write();repeat(10)@(negedge hclk);
        // WR completed, but real consumer has not accepted ACK: quiet forbidden.
        if(cq||hq||dut.active.debt!=1)$fatal(1,"lateACK debt disappeared");
        send_ack(37);wait(awv);repeat(8)@(negedge clk);
        if(awt!=37||dut.active.debt!=1||cq||hq)$fatal(1,"heldACK debt");
        @(negedge clk);ack=1;pop=1;@(negedge clk);ack=0;pop=0;
        repeat(70)@(negedge hclk);
        if(cf||hf||!cq||!hq||credits!=1||dut.active.debt!=0)$fatal(1,"warm drain/quiet/credit");
        warm=1;repeat(8)@(negedge clk);write_one();finish_write();send_ack(38);wait(awv);
        // Root consumer rejects wrong identity; adapter must NOT retire or clear debt.
        warm=0;repeat(20)@(negedge clk);
        if(awt!=38||!awv||cq||hq||dut.active.debt!=1||dut.active.u_endpoint.u_a.release_bin!=1)
            $fatal(1,"wrongACK accepted/erased");
        cold();
        fork
            land();
            begin
                wait(dut.active.u_endpoint.u_l.sector_lanes.lane[0].u_raw.lw_bin!=0);#0.001;
                dut.active.u_endpoint.u_l.sector_lanes.lane[0].u_raw.lmem[0][1:0]=
                    dut.active.u_endpoint.u_l.sector_lanes.lane[0].u_raw.lmem[0][1:0]^2'b11;
            end
        join
        repeat(60)@(negedge hclk);
        if(!cf||lvalid||credits||dut.active.u_endpoint.u_l.release_bin!=0)$fatal(1,"UE released owner");
        warm=0;repeat(8)@(negedge clk);
        if(!cf||dut.active.u_endpoint.u_l.wr_occupancy!=1||cq||hq)$fatal(1,"warm erased UE debt");
        $display("PASS parallelPC full504 two simultaneous rawRSEL1 lanes full36 row35 CEboth heldwarm WRcapture lateACK refusedwrongACK UE debt/quiet CLK833.333 H1024");$finish;
    end
endmodule
