`timescale 1ns/1ps
// TOK-FUNC2-IDX_QF 10-21: random lockstep of dsdv_idx_qf (NAT32 successor) vs blob c31c5c582 (G8IQ source, renamed dsdv_idx_qf_old):
// random tree / other / collision frames, bubbles, mid-run resets; every output compared every edge (qr data when valid).
module tb_eq;
    parameter integer MUT = 0;
    reg ck = 0, rst = 0; always #0.5 ck = ~ck;
    reg [512:0] qs = 0, ql = 0; reg [7:0] uid;
    wire [512:0] qr_o, qc0_o, qc1_o, qr_n, qc0_n, qc1_n; wire [3:0] st_o, st_n;
    dsdv_idx_qf_old o (.ck(ck), .rst(rst), .uid(uid), .qs(qs), .ql(ql), .qr(qr_o), .qc0(qc0_o), .qc1(qc1_o), .st(st_o));
    dsdv_idx_qf #(.MUT(MUT)) n (.ck(ck), .rst(rst), .uid(uid), .qs(qs), .ql(ql), .qr(qr_n), .qc0(qc0_n), .qc1(qc1_n), .st(st_n));
    integer cyc = 0, nerr = 0, nqr = 0, nhdr = 0, seed;
    always @(posedge ck) begin
        #0.1;
        if (cyc > 12) begin
          if (qc0_o !== qc0_n || qc1_o !== qc1_n || st_o !== st_n || qr_o[0] !== qr_n[0] || (qr_o[0] && qr_o !== qr_n)) begin
            nerr++; if (nerr < 8) $display("EQ mismatch cyc %0d qr v %b/%b st %b/%b", cyc, qr_o[0], qr_n[0], st_o, st_n);
          end
          if (qr_o[0]) nqr++;
          if (qr_o[0] && qr_o[512:509] == 4 ) nhdr++;
        end
        cyc++;
    end
    function automatic [511:0] rnd512(); rnd512 = {16{$urandom}}; for (int i = 0; i < 16; i++) rnd512[32*i +: 32] = $urandom; endfunction
    task automatic word(input [511:0] w, input integer port);
        @(negedge ck);
        if (port == 0) begin ql = {w, 1'b1}; qs = {rnd512(), 1'b0} & 513'd0; end
        else if (port == 1) begin qs = {w, 1'b1}; ql = 0; end
        else begin ql = {w, 1'b1}; qs = {rnd512(), 1'b1}; end   // collision
    endtask
    initial begin
        if (!$value$plusargs("seed=%d", seed)) seed = 1;
        void'($urandom(seed));
        uid = $urandom % 12;
        repeat (3) @(posedge ck); rst = 1;
        for (int f = 0; f < 400; f++) begin
            int port, ty, ns, len, k;
            reg [511:0] h, w;
            port = ($urandom % 50 == 0) ? 2 : $urandom % 2;
            ty = ($urandom % 3 != 0) ? 10 : $urandom % 16;
            ns = ($urandom % 10 == 0) ? 0 : 1 + $urandom % 4;
            h = rnd512(); h[511:508] = ty[3:0];
            len = (ty == 10 && $urandom % 8 != 0) ? 64 + ns : $urandom % 70;
            h[491:480] = len[11:0]; h[3:0] = ns[3:0];
            word(h, port);
            for (k = 0; k < len; k++) begin
                w = rnd512();
                if (k < ns) for (int e = 0; e < 4; e++) begin
                    w[128*e + 127] = $urandom % 3 != 0; w[128*e + 119 +: 8] = $urandom % 12;
                end
                if ($urandom % 9 == 0) begin @(negedge ck); ql = 0; qs = 0; end   // bubble
                word(w, port);
            end
            repeat ($urandom % 4) begin @(negedge ck); ql = 0; qs = 0; end
            if ($urandom % 97 == 0) begin @(negedge ck); rst = 0; @(negedge ck); rst = 1; end  // mid-run reset
        end
        repeat (8) @(posedge ck);
        $display("EQ_STATS seed %0d uid %0d cyc %0d qr_valid %0d hdr4 %0d nerr %0d", seed, uid, cyc, nqr, nhdr, nerr);
        if (nerr) $display("EQ FAIL"); else $display("EQ PASS");
        $finish;
    end
endmodule
