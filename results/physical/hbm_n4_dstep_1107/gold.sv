module gold(input[6:0]a,output[6:0]y);
    function automatic [6:0] dstep(input [2:0] r, input [3:0] d);   // {q digit[3:0], remainder[2:0]}
        reg [6:0] t, q, m;
        begin
            t = {r, d};                       // r * 16 + d, <= 79
            q = t / 7'd5;
            m = t % 7'd5;
            dstep = {q[3:0], m[2:0]};
        end
    endfunction
assign y=dstep(a[6:4],a[3:0]);endmodule
