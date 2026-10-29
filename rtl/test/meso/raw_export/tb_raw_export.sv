module tb_raw_export;
    timeunit 1ps; timeprecision 1fs;
    logic clk=0,d=0;
    logic gold=0;
    wire q,export_q;
    integer cycles=0,checks=0;
    logic [31:0] random_state=32'hba5ecafe;
    always #416.5 clk=~clk;
    ot_dp_head_raw_export_pair dut(.clk(clk),.d(d),.q(q),.export_q(export_q));
    always @(posedge clk) gold<=d;
    always @(negedge clk) begin
        random_state={random_state[30:0],random_state[31]^random_state[21]^random_state[1]^random_state[0]};
        if(cycles<4)d=0;else d=random_state[0];
    end
    always @(posedge clk) begin
        #1;cycles=cycles+1;
        if(cycles>1) begin
            checks=checks+1;
            if(q!==gold || export_q!==gold) begin
                $display("RAW_EXPORT_PAIR_MISMATCH cycle=%0d d=%b q=%b export=%b gold=%b",cycles,d,q,export_q,gold);
                $fatal(1,"raw export copy added delay or changed the native wavefront");
            end
        end
        if(cycles==4096)begin $display("RAW_EXPORT_PAIR_PASS checks=%0d added_cycles=0 added_FF=1",checks);$finish;end
    end
endmodule
