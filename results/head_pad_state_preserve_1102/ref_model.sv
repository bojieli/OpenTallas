// DH54-PAD gold: exact source recurrence of u_wtx hold[61:48]/oq_p[61:48] (W110/N2/P62/MUT0/IDLE_ZERO0),
// projected as in 69812606f README. No reset, no initial value: all 28 state bits are free at time 0.
module pad_ref(input wire ck, start, owe, input wire [13:0] b0, output reg [13:0] o);
    reg [13:0] q;
    always @(posedge ck) begin
        q <= (start | owe) ? 14'b0 : q;
        o <= start ? b0 : q;
    end
endmodule
