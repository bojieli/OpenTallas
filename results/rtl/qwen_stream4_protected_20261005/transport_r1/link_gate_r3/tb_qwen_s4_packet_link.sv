`timescale 1ps/1fs
// Full selected seat: 128 owners, 55 actual registered spans, real clocks.
module tb_qwen_s4_packet_link;
    reg tc=0,rc=0,por=0,warm=1,tv=0,take=0,retire=0,auto_retire=0;
    always begin #416.666 tc=1;#416.667 tc=0;end
    always #512 rc=~rc;
    reg [295:0] frame=0;
    wire tr,rv,tf,rf,quiet;
    wire [295:0] result;wire [7:0] owner,debt,retired;
    integer sent=0,got=0,expected=0;
    integer phase=0;
    always @(negedge tc)if(por&&phase>0&&phase<7&&(tf||rf))
        $fatal(1,"healthy phase=%0d sent=%0d got=%0d debt=%0d retired=%0d faults=%b%b arrived=%0d overflow=%b",phase,sent,got,debt,retired,tf,rf,dut.active.u_ring.wire_path.arrived_bin,dut.active.u_ring.wire_path.arrival_overflow);
    ot_qwen_s4_packet_link #(.ENABLE(1)) dut(.tx_clk(tc),.rx_clk(rc),.cold_por_n(por),.warm_rst_n(warm),
        .tx_valid(tv),.tx_ready(tr),.tx_frame(frame),.rx_valid(rv),.rx_take(take),.rx_frame(result),
        .rx_owner(owner),.rx_retire(auto_retire?(rv&&take):retire),.tx_debt(debt),.rx_retired(retired),
        .tx_fault(tf),.rx_fault(rf),.link_quiet(quiet));
    function automatic [295:0] data(input integer id);
        data={5'(id%32),2'b00,24'(id*128),256'(id*1234567+17),9'(id)};
    endfunction
    always @(posedge tc)if(tv&&tr)sent=sent+1;
    always @(posedge rc)if(rv&&take)begin
        if(result!==data(expected)||owner!==8'(expected))$fatal(1,"frame/owner/order %d %d",expected,owner);
        got=got+1;expected=expected+1;
    end
    task cold;
        begin @(negedge tc);por=0;warm=1;tv=0;take=0;retire=0;auto_retire=0;
            repeat(4)@(negedge tc);sent=0;got=0;expected=0;por=1;
            wait(tr);@(negedge tc);end
    endtask
    task put(input integer id);
        begin @(negedge tc);frame=data(id);tv=1;
            do @(posedge tc);while(!tr);
            @(negedge tc);tv=0;end
    endtask
    task settle;
        begin repeat(130)@(negedge tc);end
    endtask
    reg [295:0] held;
    reg [503:0] code_saved;
    initial begin
        $display("START full128/span55");
        cold();
        phase=1;$display("cold ready");
        // All 128 source owners, including frames still physically in flight.
        for(integer i=0;i<128;i=i+1)put(i);
        settle();if(debt!=128||tr||!rv||tf||rf)$fatal(1,"finite full capacity");
        phase=2;held=result;warm=0;
        settle();if(result!==held||!rv||debt!=128||retired!=0||quiet)$fatal(1,"warm erased held frame/debt");
        // Delivery without retirement must NOT produce a source credit.
        phase=3;@(negedge rc);take=1;
        wait(got==128);@(negedge rc);take=0;
        settle();if(debt!=128||retired!=0||quiet)$fatal(1,"handoff forged retirement credit");
        phase=4;@(negedge rc);retire=1;
        repeat(128)@(negedge rc);retire=0;
        settle();if(debt!=0||retired!=128||!quiet||tf||rf)$fatal(1,"ordered delayed retire");
        phase=5;$display("delayed128 retirement PASS");warm=1;wait(tr);take=1;
        // More than two complete pointer/slot wraps with continuous traffic.
        for(integer i=128;i<512;i=i+1)begin
            put(i);
            // Retire exactly the records actually delivered, independently.
            while(retired!=8'(got))begin @(negedge rc);retire=1;@(negedge rc);retire=0;end
        end
        settle();
        while(retired!=8'(got))begin @(negedge rc);retire=1;@(negedge rc);retire=0;end
        settle();if(got!=512||sent!=512||debt||tf||rf)$fatal(1,"wrap/ordered retirement");
        // A real wire payload upset remains encoded and is corrected at RX.
        phase=0;cold();phase=6;put(0);
        wait(dut.active.u_ring.wire_path.hop[4].control[0]);
        @(negedge tc);dut.active.u_ring.wire_path.hop[4].coded_q[10]=~dut.active.u_ring.wire_path.hop[4].coded_q[10];
        settle();take=1;auto_retire=1;settle();take=0;auto_retire=0;
        if(got!=1||debt||tf||rf)$fatal(1,"wire CE exact gate");
        // Double-bit wire UE preserves the owner forever, including warm.
        phase=0;cold();phase=7;put(0);
        wait(dut.active.u_ring.wire_path.hop[4].control[0]);
        @(negedge tc);dut.active.u_ring.wire_path.hop[4].coded_q[10]=~dut.active.u_ring.wire_path.hop[4].coded_q[10];
        dut.active.u_ring.wire_path.hop[4].coded_q[11]=~dut.active.u_ring.wire_path.hop[4].coded_q[11];
        take=1;warm=0;settle();
        if(!rf||rv||got||retired||debt!=1||quiet)$fatal(1,"wire UE escaped quarantine");
        // A control upset cannot replay the old valid record from its node.
        phase=0;cold();phase=8;put(0);wait(dut.active.u_ring.wire_path.hop[4].control[0]);
        @(negedge tc);dut.active.u_ring.wire_path.hop[4].u_control.primary[0]=~dut.active.u_ring.wire_path.hop[4].u_control.primary[0];
        take=1;warm=0;settle();
        if(!rf||rv||got||retired||debt!=1||quiet)$fatal(1,"wire control upset replay/lost debt");
        $display("PASS packet_link full128/span55 delayed-credit warm-held512 CE UE control-quarantine");$finish;
    end
endmodule
