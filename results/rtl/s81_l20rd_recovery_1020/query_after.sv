module query_after(input wire ck,input wire[511:0]q_d,input wire[11:0]pw,input wire hdr_go,input wire q_ld0,q_ld1,input wire[31:0]rl, output reg ql_v,output reg[7:0]ql_h,output wire[511:0]out_c,output wire[31:0]out_s,output wire[15:0]out_w);
localparam R_JOB=1;reg hgo;assign out_c=ql_c;assign out_s=ql_s;assign out_w=ql_w;
    reg  [511:0] q_d1;
    reg  [7:0] qe_head;
    (* keep = "true" *) reg [16:0] hg;        // hgo copies for the field / state loads
    (* keep = "true" *) reg [15:0] qe_h;      // even-word hold enable copies
    (* keep = "true" *) reg [17:0] qe_l;      // odd-word load enable copies
    reg  [511:0] qhold;
    reg  [511:0] ql_c;
    reg  [31:0]  ql_s;
    reg  [15:0]  ql_w;
    reg          gat;
    reg  [19:0]  jb;
    reg  [20:0]  jn, jend;
    reg  [9:0]   jk;
    reg  [29:0]  kb;
    reg  [15:0]  t0;
    reg  [3:0]   pp;
    reg  [2:0]   ik, om;
    reg  [7:0]   tg;
    reg  [15:0]  j0, j1, j1p, nw, nwm1, nlw;
    wire [20:0]  b_n = q_d1[40:20];
    wire [20:0]  b_end = 21'(q_d1[19:0]) + b_n - 21'd1;
    wire [15:0]  b_j0 = q_d1[511] ? 16'd0 : q_d1[19:4];
    wire [15:0]  b_j1 = q_d1[511] ? 16'(((b_n + 21'd1) >> 1) - 21'd1) : b_end[19:4];
    wire [15:0]  b_nw = q_d1[511] ? 16'((b_n + 21'd1) >> 1) : 16'(b_end[19:4] - q_d1[19:4] + 16'd1);
    always @(posedge ck) begin : g_stb
        integer k;
        q_d1 <= q_d;
        hgo <= hdr_go; hg <= {17{hdr_go}};
        qe_h <= {16{q_ld0}}; qe_l <= {18{q_ld1}};
        qe_head <= 8'(pw[6:1]);
        ql_v <= qe_l[0]; ql_h <= qe_head;
        for (k = 0; k < 16; k = k + 1) begin
            if (qe_h[k]) qhold[32 * k +: 32] <= q_d1[32 * k +: 32];
            if (qe_l[k]) ql_c[32 * k +: 32] <= qhold[32 * k +: 32];
        end
        if (qe_l[16]) ql_s <= q_d1[31:0];
        if (qe_l[17]) ql_w <= q_d1[47:32];
        if (hg[0]) begin gat <= q_d1[511]; jb <= q_d1[19:0]; ik <= q_d1[103:101]; om <= q_d1[106:104]; end
        if (hg[1]) begin jn <= b_n; jk <= q_d1[50:41]; end
        if (hg[2]) kb <= q_d1[80:51];
        if (hg[3]) begin t0 <= q_d1[96:81]; pp <= q_d1[100:97]; tg <= q_d1[502:495]; end
        if (hg[4]) j0 <= b_j0;
        if (hg[5]) j1 <= b_j1;
        if (hg[6]) begin nw <= b_nw; nlw <= q_d1[511] ? 16'((b_n + 21'd15) >> 4) : 16'd0; end
        if (hg[7]) jend <= 21'(q_d1[19:0]) + b_n;
        if (hg[8]) begin j1p <= b_j1 + 16'd1; nwm1 <= b_nw - 16'd1; end
        if (!rl[R_JOB]) begin hgo <= 1'b0; ql_v <= 1'b0; end
    end


endmodule
