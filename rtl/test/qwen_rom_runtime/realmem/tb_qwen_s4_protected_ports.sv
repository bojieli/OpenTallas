`timescale 1ps/1fs
// Minimum full-size PC + actual shared control modules at real clock periods.
module tb_qwen_s4_protected_ports;
    reg clk=0,hclk=0,por=0,warm=1;
    always begin #416.666 clk=1;#416.667 clk=0;end
    always #512 hclk=~hclk;
    reg lv=0,av=0,wv=0,pop=0,run=0;
    reg [16:0] lsec=0;reg [7:0] lrow=0;reg [255:0] ldata=0;
    reg [23:0] wsec=0;reg [255:0] wdata=0;reg [8:0] wtag=0,atag=0;
    wire lvalid,wroom,wdvalid,cf,hf,hwvalid,cv;
    wire [16:0] olsec;wire [7:0] olrow;wire [255:0] oldata,cdata;
    wire [23:0] hwsec,csec;wire [8:0] wdtag,ctag;wire [2:0] credit;
    integer handed=0,completed=0,landed=0,acked=0,credits=0,cycle=0;
    wire hand=run&&hwvalid;
    wire con=run&&(completed<handed)&&(cycle%3==0);
    ot_qwen_s4_protected_pc dut(.clk(clk),.hclk(hclk),.por_n(por),.warm_rst_n(warm),
        .l_v(lvalid),.l_sec(olsec),.l_row(olrow),.l_data(oldata),.l_pop(pop&&lvalid),
        .w_v(wv),.w_sec(wsec),.w_data(wdata),.w_tag(wtag),.w_room(wroom),
        .wd_v(wdvalid),.wd_tag(wdtag),.c_fault(cf),
        .h_lv(lv),.h_lsec(lsec),.h_lrow(lrow),.h_ldata(ldata),.h_cred(credit),
        .h_wv(hwvalid),.h_wsec(hwsec),.h_hand(hand),.h_wcon(con),.h_cv(cv),
        .h_csec(csec),.h_cdata(cdata),.h_ctag(ctag),.h_av(av),.h_atag(atag),.h_fault(hf));
    reg dv=0,go=0,dr=0,busy=0;reg [18:0] row=1;reg [10:0] count=11;
    wire ready,descvalid,hgo,ccf,chf;wire [18:0] orow;wire [10:0] on;
    integer desctaken=0,gotaken=0;
    ot_qwen_s4_protected_control ctl(.clk(clk),.hclk(hclk),.por_n(por),.warm_rst_n(warm),
        .d_v(dv),.d_rdy(ready),.d_row(row),.d_n(count),.go(go),.desc_v(descvalid),
        .desc_r(dr),.desc_row(orow),.desc_n(on),.busy_all(busy),.h_go(hgo),
        .c_external_fault(1'b0),.h_external_fault(1'b0),.c_fault(ccf),.h_fault(chf));
    always @(posedge hclk)if(por)begin
        cycle=cycle+1;credits=credits+credit;
        if(hand)begin
            if(hwsec!==24'(handed*128))$fatal(1,"unchecked/out-of-order handoff sector");
            handed=handed+1;
        end
        if(descvalid&&dr)begin
            if(orow!=1||on!=11)$fatal(1,"descriptor data");
            desctaken=desctaken+1;busy<=1;
        end
        if(hgo)begin
            if(desctaken!=1||gotaken!=0)$fatal(1,"GO replay/order");
            gotaken=gotaken+1;
        end
    end
    // h_cv is the registered capture on the WR edge, exactly the existing
    // wrapper's next-edge completion observation contract.
    always @(negedge hclk)if(por&&cv)begin
        if(csec!==24'(completed*128)||cdata!=={8{32'(completed+99)}}||ctag!==9'(completed))
            $fatal(1,"WR completion identity/data");
        completed=completed+1;
    end
    always @(posedge clk)if(por)begin
        if(lvalid&&pop)begin
            if(olsec!=0||olrow!=0||oldata!={8{32'h12345678}})$fatal(1,"landing data");
            landed=landed+1;
        end
        if(wdvalid)begin if(wdtag!=9'd55)$fatal(1,"ack identity");acked=acked+1;end
    end
    task put(input integer id);
        begin
            @(negedge clk);while(!wroom)@(negedge clk);
            wsec=24'(id*128);wdata={8{32'(id+99)}};wtag=9'(id);wv=1;
            @(negedge clk);wv=0;
        end
    endtask
    initial begin
        repeat(4)@(negedge clk);por=1;repeat(6)@(negedge clk);
        while(!ready)@(negedge clk);
        dv=1;@(negedge clk);dv=0;go=1;@(negedge clk);go=0;
        for(integer i=0;i<12;i=i+1)put(i);
        @(negedge hclk);lv=1;lsec=0;lrow=0;ldata={8{32'h12345678}};
        @(negedge hclk);lv=0;
        repeat(16)@(negedge hclk);
        if(!lvalid||!hwvalid||!descvalid)$fatal(1,"held accepted outputs missing");
        warm=0;repeat(12)@(negedge clk);
        if(wroom||ready||gotaken||landed||completed||!lvalid||!hwvalid||!descvalid)
            $fatal(1,"warm pause changed accepted debt/new admission");
        // Drain old debt while warm remains asserted, including late ACK.
        run=1;pop=1;dr=1;
        @(negedge hclk);av=1;atag=55;@(negedge hclk);av=0;
        repeat(100)@(negedge hclk);
        if(completed!=12||handed!=12||landed!=1||acked!=1||credits!=1||desctaken!=1||gotaken!=1)
            $fatal(1,"drain/replay H%0d C%0d L%0d A%0d credit%0d D%0d G%0d",handed,completed,landed,acked,credits,desctaken,gotaken);
        if(cf||hf||ccf||chf)$fatal(1,"healthy warm drain fault %b%b%b%b",cf,hf,ccf,chf);
        pop=0;dr=0;warm=1;repeat(6)@(negedge clk);
        if(!wroom||!ready)$fatal(1,"warm resume failed to return finite capacity");
        for(integer i=12;i<40;i=i+1)put(i);
        repeat(120)@(negedge hclk);
        if(completed!=40||handed!=40||cf||hf)$fatal(1,"cache wrap/debt failed");
        run=0;put(40);repeat(18)@(negedge hclk);
        dut.slot[8].u_cache.inverse[0]=~dut.slot[8].u_cache.inverse[0];
        #1;
        if(!hf||hwvalid||cv)$fatal(1,"cache fault authorized handoff/completion");
        warm=0;repeat(12)@(negedge hclk);
        if(!hf||dut.u_w.wr_occupancy!=1||dut.u_w.retired!=8)$fatal(1,"warm reset erased quarantined WR debt");
        $display("PASS actualPC281x64/289x16/9x64+shared30x4/GO3x4 warm-held/drain/40WRwrap/ordinalGO/cachefault CLK833.333 H1024");
        $finish;
    end
endmodule
