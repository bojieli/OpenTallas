`timescale 1ns/1ps
module tb_dsdv_idx_loop_lane3;
    reg [275:0] i, expected;
    wire [275:0] o, mlane, mqslot;
    integer c, b, bad=0, lane_bad=0, slot_bad=0;
    dsdv_idx_loop_lane3 u(.i(i),.o(o));
    dsdv_idx_loop_lane3 #(.MUT(2)) u_lane(.i(i),.o(mlane));
    dsdv_idx_loop_lane3 #(.MUT(3)) u_slot(.i(i),.o(mqslot));
    initial begin
        for(c=0;c<2048;c=c+1) begin
            for(b=0;b<276;b=b+1) i[b]=$random;
            i[5:4]=c[3:2]; i[51:50]=c[5:4];
            // Construct semantic classes, independent of the DUT decoder.
            case(c%8)
            0: begin i[0]=1; i[3:1]=4; i[7:6]=2'b10; i[19:16]=1; end // HDR single
            1: begin i[0]=1; i[3:1]=4; i[7:6]=2'b00; i[19:16]=2; end // BEAT low
            2: begin i[0]=1; i[3:1]=4; i[7:6]=2'b01; end              // BEAT high
            3: begin i[0]=1; i[3:1]=4; i[7:6]=2'b10; i[19:16]=6; end // REBASE
            4: begin i[0]=0; i[3:1]=4; i[7:6]=2'b10; i[19:16]=1; end // invalid HDR-shaped
            5: begin i[0]=1; i[3:1]=0; i[7:6]=2'b10; i[19:16]=1; end // CTL-shaped
            6: begin i[0]=1; i[3:1]=5; i[7:6]=2'b10; i[19:16]=1; end // egress kind
            7: begin i[0]=1; i[3:1]=4; i[7:6]=2'b00; i[19:16]=1; end // non-single
            endcase
            expected=i; expected[5:4]=3;
            #1;
            if(o!==expected) bad=bad+1;
            if(mlane!==expected) lane_bad=lane_bad+1;
            if(mqslot!==expected) slot_bad=slot_bad+1;
        end
        if(bad==0 && lane_bad>0 && slot_bad>0)
            $display("LOOP_LANE3_MITER PASS cases=%0d errors=%0d lane_mutant=%0d qslot_mutant=%0d",c,bad,lane_bad,slot_bad);
        else $fatal(1,"LOOP_LANE3_MITER FAIL errors=%0d lane_mutant=%0d qslot_mutant=%0d",bad,lane_bad,slot_bad);
        $finish;
    end
endmodule
