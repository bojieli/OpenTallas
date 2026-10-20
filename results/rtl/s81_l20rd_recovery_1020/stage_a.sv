module stage_a(input wire ck,input wire[511:0]q_d,input wire[11:0]pw,input wire hdr_go,input wire q_ld0,q_ld1,input wire[31:0]rl,output reg ql_v,output reg[7:0]ql_h,output wire[511:0]c,output wire[31:0]sc,output wire[15:0]wt,output wire[511:0]meta);
localparam R_JOB=1;reg hgo;wire pay_job=q_ld0||q_ld1;assign c=ql_c;assign sc=ql_s;assign wt=ql_w;assign meta={gat,jb,jn,jend,jk,kb,t0,pp,ik,om,tg,j0,j1,j1p,nw,nwm1,nlw};
    reg  [511:0] q_d1;
    (* keep = "true" *) reg [7:0] q_kind;
    reg  [7:0] qe_head;
    (* keep = "true" *) reg [21:0] hg;        // hgo copies for the field / state loads
    (* keep = "true" *) reg [31:0] qe_h;      // even-word hold enable copies
    (* keep = "true" *) reg [34:0] qe_l;
    (* keep = "true" *) reg qe_l_valid;
    wire qodd_a,qodd_b;
    dsdv_idx_query_odd u_qa(.p(pay_job),.pw(pw),.y(qodd_a));
    dsdv_idx_query_odd u_qb(.p(pay_job),.pw(pw),.y(qodd_b));      // odd-word load enable copies
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
    wire [15:0]  b_j0 = q_kind[0] ? 16'd0 : q_d1[19:4];
    wire [15:0]  b_j1 = q_kind[1] ? 16'(((b_n + 21'd1) >> 1) - 21'd1) : b_end[19:4];
    wire [15:0]  b_nw = q_kind[2] ? 16'((b_n + 21'd1) >> 1) : 16'(b_end[19:4] - q_d1[19:4] + 16'd1);
    always @(posedge ck) begin : g_stb
        integer k;
        q_d1 <= q_d; q_kind <= {8{q_d[511]}};
        hgo <= hdr_go; hg <= {22{hdr_go}};
        qe_h <= {32{q_ld0}}; qe_l <= {{17{qodd_b}},{18{qodd_a}}}; qe_l_valid <= qodd_a;
        qe_head <= 8'(pw[6:1]);
        ql_v <= qe_l_valid; ql_h <= qe_head;
        for (k = 0; k < 32; k = k + 1) begin
            if (qe_h[k]) qhold[16*k+:16] <= q_d1[16*k+:16];
            if (qe_l[k]) ql_c[16*k+:16] <= qhold[16*k+:16];
        end
        if(qe_l[32]) ql_s[15:0] <= q_d1[15:0];
        if(qe_l[33]) ql_s[31:16] <= q_d1[31:16];
        if(qe_l[34]) ql_w <= q_d1[47:32];
        if (hg[0]) begin gat <= q_kind[3]; ik <= q_d1[103:101]; om <= q_d1[106:104]; end
        if(hg[9]) jb[9:0] <= q_d1[9:0];
        if(hg[10]) jb[19:10] <= q_d1[19:10];
        if(hg[1]) jn[10:0] <= b_n[10:0];
        if(hg[11]) jn[20:11] <= b_n[20:11];
        if(hg[12]) jk <= q_d1[50:41];
        if(hg[2]) kb[14:0] <= q_d1[65:51];
        if(hg[13]) kb[29:15] <= q_d1[80:66];
        if(hg[3]) t0 <= q_d1[96:81];
        if(hg[17]) begin pp <= q_d1[100:97]; tg <= q_d1[502:495];end
        if (hg[4]) j0 <= b_j0;
        if (hg[5]) j1 <= b_j1;
        if(hg[6]) nw <= b_nw;
        if(hg[18]) nlw <= q_kind[4] ? 16'((b_n + 21'd15) >> 4) : 16'd0;
        if(hg[7]) jend[10:0] <= (21'(q_d1[19:0]) + b_n);
        if(hg[19]) jend[20:11] <= (21'(q_d1[19:0]) + b_n) >> 11;
        if(hg[8]) j1p <= b_j1 + 16'd1;
        if(hg[20]) nwm1 <= b_nw - 16'd1;
        if (!rl[R_JOB]) begin hgo <= 1'b0; ql_v <= 1'b0; end
    end


endmodule

(* keep_hierarchy = "yes" *) module dsdv_idx_query_odd(input wire p,input wire[11:0]pw,output wire y);
assign y=p && pw<12'd64 && pw[0];
endmodule
