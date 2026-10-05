`timescale 1ns/1ps
// Changed-adapter protocol component ONLY. Full16 bank geometry is unchanged;
// five read/16write seats keep this independent test finite, not a production
// capacity or native-SU/numerical qualification. Initial raw bytes are from
// Ampere's pinned, authorized HEAD initial fixture, not normalized activations.
module tb_qwen_finite_vm_adapter;
    localparam NR=5,NW=16,VX0=3,NVX=2;
    reg clk=0,rst_n=0;
    always #5 clk=~clk;
    reg me_wanted=0;
    reg [NR-1:0] re=0;
    reg [NR*24-1:0] ra=0;
    wire [NR*32-1:0] rq;
    reg [NW-1:0] we=0;
    reg [NW*24-1:0] wa=0;
    reg [NW*32-1:0] wd=0;
    wire tick,lease,drained,fault;
    wire [63:0] epoch,reads,writes,acks,held;
    wire native_clk;
    reg [63:0] native_edges=0,raw_acks=0;
    reg [31:0] initial_x[0:4095];
    reg [1023:0] fixture_path;
    integer negative=0;
    ot_hdc_cg u_gate(.clk(clk),.en(!rst_n||tick),.gclk(native_clk));
    always @(posedge native_clk)if(rst_n)native_edges<=native_edges+1;
    ot_qwen_finite_vm_adapter #(.ENABLE(1),.HEAD_CACHE(0),
        .NR(NR),.NW(NW),.VX0(VX0),.NVX(NVX)) dut(
        .clk(clk),.rst_n(rst_n),.source_me_wanted(me_wanted),.head_source_producer_go(1'b0),
        .read_en(re),.read_addr(ra),.read_q(rq),.write_en(we),.write_addr(wa),.write_data(wd),
        .native_tick(tick),.native_me_lease(lease),.drained(drained),.fault(fault),
        .native_epoch(epoch),.physical_reads(reads),.physical_writes(writes),.physical_ACKs(acks),
        .held_edges(held),.head_fill_reads(),.head_hit_edges());
    always @(posedge clk)if(rst_n)begin
        if(|dut.g_bound.u_bank.raw_ack)raw_acks<=raw_acks+1;
        if(tick && dut.pack_valid)$fatal(1,"native admission with unpaid write pack");
        if(tick && fault)$fatal(1,"faulted native admission");
    end
    // Bound is derived from all seats missing independently and all writes
    // flushing independently, with the actual9/28 calendar and control seats.
    // This detects a protocol deadlock; no process/wall/resource time limit.
    localparam FRAME_BOUND=2+NR*14+NW*33+32;
    task automatic frame;
        integer steps;reg [63:0] before_epoch,before_native,before_acks;
        begin
            before_epoch=epoch;before_native=native_edges;before_acks=acks;
            steps=0;
            do begin
                @(posedge clk);#1;steps=steps+1;
                if(fault)$fatal(1,"unexpected frame fault");
                if(epoch==before_epoch && native_edges!=before_native)$fatal(1,"native state advanced while frame held");
                if(steps>FRAME_BOUND)$fatal(1,"finite frame failed to drain within source-derived bound");
            end while(epoch==before_epoch);
            if(native_edges!=before_native+1)$fatal(1,"native controller/adapter edge mismatch");
            if((|we) && acks==before_acks)$fatal(1,"write admitted without positive physical ACK");
            if(!drained)$fatal(1,"native source admitted before frame drain");
            @(negedge clk);re=0;we=0;
        end
    endtask
    task automatic install(input integer base,input integer fixture_offset);
        begin
            for(integer i=0;i<16;i=i+1)begin
                we[i]=1;wa[i*24+:24]=base+i;wd[i*32+:32]=initial_x[fixture_offset+i];
            end
            frame();
        end
    endtask
    initial begin
        if(!$value$plusargs("FIXTURE=%s",fixture_path))$fatal(1,"mandatory actual initial fixture missing");
        if($value$plusargs("NEGATIVE=%d",negative))begin end
        $readmemh(fixture_path,initial_x);
        if(^initial_x[0]===1'bx || ^initial_x[4095]===1'bx)$fatal(1,"incomplete initial fixture");
        repeat(3)@(negedge clk);rst_n=1;
        install(4096,0);install(4160,64);install(4224,128);
        if(acks!=3 || raw_acks!=3)$fatal(1,"initial source physical installation missing ACK");
        re=5'b00111;ra[0+:24]=4096;ra[24+:24]=4160;ra[48+:24]=4224;
        we=1;wa[0+:24]=4096;wd[0+:32]=initial_x[1];
        frame();
        if(rq[0+:32]!==initial_x[0] || rq[32+:32]!==initial_x[64] || rq[64+:32]!==initial_x[128])
            $fatal(1,"old-read before masked write / three operand windows mismatch");
        re=3;ra[0+:24]=4096;ra[24+:24]=4097;frame();
        if(rq[0+:32]!==initial_x[1] || rq[32+:32]!==initial_x[1])
            $fatal(1,"masked write readback / untouched neighbor mismatch");
        if(writes!=4 || acks!=4 || raw_acks!=4 || held==0)$fatal(1,"physical write/readback/hold coverage missing");
        $display("POSITIVE physical_writes=%0d checked_ACKs=%0d raw_ACKs=%0d reads=%0d held=%0d native=%0d",writes,acks,raw_acks,reads,held,native_edges);
        // A foreign echo is a deliberate negative at the response boundary,
        // never an input/ACK shortcut to get the positive path through.
        if(negative==0)begin
            re=1;ra[0+:24]=4160;
            @(posedge clk);#1;
            wait(dut.rd_valid);
            force dut.rd_owner=227'h1;
            @(posedge clk);#1;
            release dut.rd_owner;
            if(!fault || tick || lease)$fatal(1,"foreign response did not fail closed");
            $display("PASS initial_source_install oldread_write readback hold foreign_response HEAD_CACHE_OFF");
        end else if(negative==1)begin:foreign_ack
            reg [63:0] before_native;
            before_native=native_edges;
            // Negative response on empty-frame fast admission must hold the
            // SAME native edge, not merely capture fault for the next edge.
            force dut.wr_ACK=4'b0001;
            #1;if(tick || lease)$fatal(1,"unsolicited ACK admitted native edge before fault capture");
            @(posedge clk);#1;
            release dut.wr_ACK;
            if(!fault || tick || lease || native_edges!=before_native)
                $fatal(1,"unsolicited ACK did not hold source/fail closed");
            $display("PASS unsolicited_ACK_same_edge_hold HEAD_CACHE_OFF");
        end else $fatal(1,"unknown negative case");
        $finish;
    end
endmodule
