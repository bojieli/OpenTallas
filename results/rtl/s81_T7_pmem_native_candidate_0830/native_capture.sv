module native_capture #(parameter integer REPL=2,PWORDS=2,TD=32)(input wire clk,rst_n,p_v,p_ready_i,input wire[1023:0]p_w,output wire p_ready,output wire out_v,output wire[1023:0]out_w);
    wire p_v_i;
    wire [PWORDS*TD*16-1:0] p_w_i;
    generate if (REPL != 0) begin : g_pskid
        // two fixed slots: a push writes slot wp, the loader reads slot rp; a pop only moves rp (no wide mux enable
        // behind the loader's accept logic)
        reg [1:0] sk_n;
        reg       wp, rp;
        reg [PWORDS*TD*16-1:0] sk0, sk1;
        wire push = p_v && p_ready, pop = p_v_i && p_ready_i;
        assign p_ready = (sk_n != 2'd2);
        assign p_v_i = (sk_n != 2'd0);
        assign p_w_i = rp ? sk1 : sk0;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin sk_n <= 2'd0; wp <= 1'b0; rp <= 1'b0; end
            else begin
                sk_n <= sk_n + (push ? 2'd1 : 2'd0) - (pop ? 2'd1 : 2'd0);
                if (push) wp <= !wp;
                if (pop) rp <= !rp;
            end
        end
        always @(posedge clk) begin
            if (push && !wp) sk0 <= p_w;
            if (push && wp) sk1 <= p_w;
        end
    end else begin : g_pdirect
        assign p_ready = p_ready_i;
        assign p_v_i = p_v;
        assign p_w_i = p_w;
    end endgenerate
assign out_v=p_v_i;assign out_w=p_w_i;endmodule
