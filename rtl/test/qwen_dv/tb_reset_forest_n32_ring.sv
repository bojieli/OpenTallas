`timescale 1ns/1ps
module tb_reset_forest_n32_ring;
    localparam integer W=1073,C=(W+23)/24,D=4;
    reg ck=0,rst_n=0;
    reg [W-1:0] payload;
    wire [C:0] resets;
    wire normal;
    wire [D*W-1:0] old_bank,new_bank;
    wire [D*3-1:0] old_epoch,new_epoch;
    wire [D*C-1:0] old_valid,new_valid;
    wire [W-1:0] old_answer,new_answer;
    always #5 ck=~ck;
    ot_pl_land_reset_forest_lead #(.DEPTH(2),.LEAVES(C+1),.ROOT_LOADS(2)) forest(
        .ck(ck),.d(rst_n),.q(resets),.scalar_q(normal));
    ot_pl_land_vector_reset_w #(.W(W),.D(D),.CHUNK_BITS(24)) old_writer(
        .ck(ck),.rsi(resets[C:1]),.i(payload),.bank(old_bank),.epo(old_epoch),.vld(old_valid));
    ot_pl_land_vector_reset_w #(.W(W),.D(D),.CHUNK_BITS(24),.NATIVE32(1)) new_writer(
        .ck(ck),.rsi(resets[C:1]),.i(payload),.bank(new_bank),.epo(new_epoch),.vld(new_valid));
    ot_pl_land_vector_reset_r #(.W(W),.D(D),.K(2),.CHUNK_BITS(24)) old_reader(
        .ck(ck),.rsi(resets[C:1]),.bank(old_bank),.epo(old_epoch),.vld(old_valid),.o(old_answer));
    ot_pl_land_vector_reset_r #(.W(W),.D(D),.K(2),.CHUNK_BITS(24)) new_reader(
        .ck(ck),.rsi(resets[C:1]),.bank(new_bank),.epo(new_epoch),.vld(new_valid),.o(new_answer));
    integer cyc,j,compares=0;
    initial begin
        payload=0;
        for(cyc=0;cyc<10000;cyc=cyc+1) begin
            @(negedge ck);
            // Initial long reset plus repeated assertion/release at different phases.
            rst_n=(cyc>10 && cyc%211>3 && cyc%97!=20);
            for(j=0;j<W;j=j+1) payload[j]=1'($random);
            @(posedge ck); #1;
            if(cyc>20) begin
                if(old_answer!==new_answer) $fatal(1,"N32_VECTOR_RESET_RING_MISMATCH cycle=%0d",cyc);
                compares=compares+1;
            end
        end
        $display("N32_VECTOR_RESET_RING_LOCKSTEP_PASS compares=%0d",compares);
        $finish;
    end
endmodule
