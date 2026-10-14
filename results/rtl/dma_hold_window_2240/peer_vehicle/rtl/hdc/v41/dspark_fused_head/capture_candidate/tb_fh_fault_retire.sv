`timescale 1ns/1ps
module tb_fh_fault_retire;
    localparam integer PW=5510;
    reg clk=0,rst_n=0,packet_v=0;
    reg [PW-1:0] packet=0;
    reg [63:0] poison=0;
    reg [3:0] address_fault=0;
    reg arithmetic_fault=0;
    wire retired_v,fault,busy,baseline_v,baseline_fault,baseline_busy;
    wire [PW-1:0] retired_packet,baseline_packet;
    wire [63:0] lane_veto,baseline_lane;
    wire [3:0] write_veto,baseline_write;
`ifdef FH_NEG_DROP_POISON
    wire [63:0] candidate_poison=0;
`else
    wire [63:0] candidate_poison=poison;
`endif
`ifdef FH_NEG_WRONG_INDEX
    wire [PW-1:0] candidate_packet=packet^(5510'b1<<33);
`else
    wire [PW-1:0] candidate_packet=packet;
`endif
    ot_hdc_v41_fh_fault_retire #(.ENABLE(1)) dut
        (clk,rst_n,packet_v,candidate_packet,candidate_poison,address_fault,arithmetic_fault,
         retired_v,retired_packet,lane_veto,write_veto,fault,busy);
    ot_hdc_v41_fh_fault_retire baseline
        (clk,rst_n,packet_v,packet,poison,address_fault,arithmetic_fault,
         baseline_v,baseline_packet,baseline_lane,baseline_write,baseline_fault,baseline_busy);
    always #5 clk=~clk;
    // Event calendar, independent of the DUT shift-register implementation.
    reg [PW-1:0] expected_packet[0:255];
    reg expected_fault[0:255];
    integer due[0:255],head=0,tail=0,cycle=0;
    integer accepted=0,released=0,reset_aborted=0,warm_accepted=0,warm_released=0,warm_aborted=0;
    integer faulted=0,checks=0,i,j;
    reg [63:0] poison_seen=0;
    reg [3:0] address_seen=0;
    reg arithmetic_seen=0;
    always @(negedge rst_n) begin
        while(head<tail) begin
            reset_aborted=reset_aborted+1;
            if(expected_packet[head][0]) warm_aborted=warm_aborted+1;
            head=head+1;
        end
    end
    always @(posedge clk) begin
        cycle=cycle+1;
        if(rst_n&&packet_v) begin
            expected_packet[tail]=packet;
            expected_fault[tail]=(|poison)||(|address_fault)||arithmetic_fault;
            due[tail]=cycle+3;tail=tail+1;accepted=accepted+1;
            if(packet[0]) warm_accepted=warm_accepted+1;
            poison_seen=poison_seen|poison;
            address_seen=address_seen|address_fault;
            arithmetic_seen=arithmetic_seen|arithmetic_fault;
        end
        #1;
        if(baseline_v!==packet_v||baseline_packet!==packet||baseline_busy!==0||
           baseline_fault!==((|poison)||(|address_fault)||arithmetic_fault))
            $fatal(1,"defaultOFF changed baseline");
        if(!rst_n) begin
            if(retired_v!==0||busy!==0||fault!==0||lane_veto!==0||write_veto!==0)
                $fatal(1,"reset leaves valid/debt/fault");
        end else if(head<tail&&due[head]==cycle) begin
            if(retired_v!==1||retired_packet!==expected_packet[head]||
               fault!==expected_fault[head]||lane_veto!=={64{expected_fault[head]}}||
               write_veto!=={4{expected_fault[head]}})
                $fatal(1,"transaction/fault/mask/tag/index misalignment cycle%0d",cycle);
            if(retired_packet[0]) warm_released=warm_released+1;
            if(fault) faulted=faulted+1;
            released=released+1;head=head+1;checks=checks+1;
        end else if(retired_v!==0) $fatal(1,"unsolicited/duplicate retirement");
    end
    initial begin
        repeat(2) @(negedge clk);rst_n=1;
        // One deterministic config: all64 poison sources, all4 address faults,
        // arithmetic faults, holes, warm markers, and full-width masked data.
        for(i=0;i<192;i=i+1) begin
            @(negedge clk);
            packet_v=(i%7!=3);
            for(j=0;j<PW;j=j+1) packet[j]=((j*13+i*7)^(j>>3)^(i>>2))&1;
            packet[0]=(i%5==0)||(i==18); // Reset with a warm-index marker in flight.
            poison=64'b1<<(i%64);if(i%3==0) poison=0;
            address_fault=(i%11==0)?(4'b1<<(i%4)):0;
            arithmetic_fault=(i%13==0);
            if(i==19) begin rst_n=0;packet_v=0;end
            if(i==21) rst_n=1;
        end
        @(negedge clk);packet_v=0;poison=0;address_fault=0;arithmetic_fault=0;
        repeat(6) @(negedge clk);
        if(busy||head!=tail||accepted!=released+reset_aborted||
           warm_accepted!=warm_released+warm_aborted||faulted==0||checks<60||
           poison_seen!={64{1'b1}}||address_seen!==4'b1111||!arithmetic_seen)
            $fatal(1,"lost warm/transaction debt accepted%0d released%0d abort%0d",accepted,released,reset_aborted);
        $display("PASS G4W16 packet5510 faultretire4 defaultOFF exactcalendar accepted=%0d released=%0d reset_abort=%0d warm=%0d/%0d/%0d faulted=%0d",accepted,released,reset_aborted,warm_accepted,warm_released,warm_aborted,faulted);
        $finish;
    end
endmodule
