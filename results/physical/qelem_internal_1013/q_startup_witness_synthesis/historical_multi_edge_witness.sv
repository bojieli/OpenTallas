module ot_s81_q_reset_witness(input wire clk,epoch_n,local_n,output wire ack);
    (* keep, dont_touch = "true" *) reg [1:0] live;
    always @(posedge clk or negedge epoch_n or negedge local_n)
        if (!epoch_n || !local_n) live <= 2'b00;
        else live <= {live[0],1'b1};
    assign ack=live[1];
endmodule
