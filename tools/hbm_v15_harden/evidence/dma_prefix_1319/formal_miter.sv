module miter(input wire [31:0] a,b,c,output wire ok);
    function automatic [31:0] add_total_sub_ack(
        input [31:0] a, input [31:0] b, input [31:0] subtrahend);
        reg [31:0] inv_c, sum_bits, carry_bits, prop_bits, pref_p, pref_g;
        reg [31:0] next_p, next_g, carry_in;
        integer step, bit_index;
        begin
            inv_c = ~subtrahend;
            sum_bits = a ^ b ^ inv_c;
            carry_bits = ((a & b) | (a & inv_c) | (b & inv_c)) << 1;
            prop_bits = sum_bits ^ carry_bits;
            pref_p = prop_bits;
            pref_g = sum_bits & carry_bits;
            for (step=1; step<32; step=step*2) begin
                next_p = pref_p; next_g = pref_g;
                for (bit_index=step; bit_index<32; bit_index=bit_index+1) begin
                    next_g[bit_index] = pref_g[bit_index] |
                        (pref_p[bit_index] & pref_g[bit_index-step]);
                    next_p[bit_index] = pref_p[bit_index] & pref_p[bit_index-step];
                end
                pref_p=next_p; pref_g=next_g;
            end
            // ~subtrahend requires a +1 carry-in for subtraction.
            carry_in = ((pref_g | pref_p) << 1) | 32'd1;
            add_total_sub_ack = prop_bits ^ carry_in;
        end
    endfunction
assign ok=add_total_sub_ack(a,b,c)==(a+b-c);
endmodule
