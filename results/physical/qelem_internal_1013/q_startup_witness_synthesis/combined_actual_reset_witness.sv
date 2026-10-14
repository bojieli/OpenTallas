module ot_s81_q_reset_witness(input wire clk,epoch_n,local_n,output wire ack);
    (* keep, dont_touch = "true" *) reg [1:0] live;
    wire actual_reset_n = epoch_n && local_n;
    always @(posedge clk or negedge actual_reset_n)
        if (!actual_reset_n) live <= 2'b00;
        else live <= {live[0],1'b1};
    assign ack=live[1];
endmodule
