`timescale 1ns/1ps
`default_nettype none
module dsfd_vm_xio_request #(parameter integer RLAT=13)(
 input wire ck,rst_n,input wire n_v,input wire[83:0] n_d,input wire[14:0] f_crq,
 output reg[3:0] a_v,output reg[55:0] a_row,
 output wire[2:0] return_valid,output wire[5:0] return_lane,output reg fault
);
    reg [1:0] rq;
    always @(posedge ck or negedge rst_n) if (!rst_n) rq <= 2'b00; else rq <= {rq[0], 1'b1};
    wire rn = rq[1];
    // Native boundary repair: r1 capture276.58ps on f_crq[2] crossed
    // E->W and decoded before the first FF. Capture inputs at their own face.
    reg n_v_pin;reg[83:0]n_d_pin;reg[14:0]f_crq_pin;
    always @(posedge ck)begin n_v_pin<=rn&&n_v;n_d_pin<=n_d;f_crq_pin<=rn?f_crq:0;end
    // epoch sample index of the current edge (same convention as ot_s81_vm_x43: first edge after release = 0)
    reg [1:0] tp;
    always @(posedge ck or negedge rst_n) if (!rst_n) tp <= 2'd3; else tp <= tp + 2'd1;
    wire [1:0] tn = tp + 2'd1;
    reg [2:0] f_iss;

    // ---------------------------------------------------------------- command decode
    wire [2:0] code = n_d_pin[30:28];
    wire is_st = n_v_pin && code == 3'd4, is_cp = n_v_pin && code == 3'd5, is_cf = n_v_pin && code == 3'd7;
    wire is_cl = n_v_pin && code == 3'd6 && n_d_pin[27:24] == 4'd7;
    // Unit 0 names the direct collective lane; state is used only for Q/G (1/2).
    reg [2:0] act; reg [13:0] u_row [0:2]; reg [4:0] u_n [0:2];
    reg [3:0] stream_av; reg [55:0] stream_ar;
    // ---------------------------------------------------------------- issue (edge I)
    reg [2:0] go; reg [1:0] gl [0:2];
    always @* begin : p_go integer u;
        for (u = 0; u < 3; u = u + 1) begin
            go[u] = (u == 0) ? f_crq_pin[0] : (act[u] && tn != 2'(16-RLAT));
            gl[u] = (u == 0) ? f_crq_pin[2:1] : u_row[u][1:0];
        end
    end
    reg lane_bad;
    reg [2:0] go_ok;
    always @* begin
        lane_bad = 1'b0; go_ok = go;
        if (go[2] && go_ok[1] && gl[2] == gl[1]) begin lane_bad = 1'b1; go_ok[2] = 1'b0; end
    end
    // The direct collective lane is merged with the registered Q/G requests.
    // A collision faults and collective retains its reserved lane; nothing waits.
`ifdef OT_VM_XIO_MUT_REQUEST
    always @* begin
      a_v=stream_av;a_row=stream_ar;
      if(f_crq_pin[0])begin a_v[f_crq_pin[2:1]]=1'b1;a_row[14*f_crq_pin[2:1]+:14]=f_crq_pin[14:1];end
    end
`else
    always @(posedge ck) if (!rn) begin a_v <= 0; a_row <= 0; end else begin
        a_v <= stream_av; a_row <= stream_ar;
        if (f_crq_pin[0]) begin
            a_v[f_crq_pin[2:1]] <= 1'b1;
            a_row[14*f_crq_pin[2:1] +: 14] <= f_crq_pin[14:1];
        end
    end
`endif
    reg [RLAT:0] dC; reg [1:0] dlC [0:RLAT];
    reg [RLAT+1:0] dQ, dG; reg [1:0] dlQ [0:RLAT+1]; reg [1:0] dlG [0:RLAT+1];
    always @(posedge ck) begin : p_iss integer u, k; reg [3:0] av;
        if (!rn) begin
            act <= 3'd0; stream_av <= 4'd0; dC <= '0; dQ <= '0; dG <= '0;
            f_iss <= 3'd0;
        end else begin
            av = 4'd0;
            for (u = 1; u < 3; u = u + 1) if (go_ok[u]) av[gl[u]] = 1'b1;
            stream_av <= av;
            for (u = 1; u < 3; u = u + 1) if (go[u]) begin
                u_row[u] <= u_row[u] + 14'd1;
                if (u_n[u] == 5'd0) act[u] <= 1'b0; else u_n[u] <= u_n[u] - 5'd1;
            end
            if (lane_bad) f_iss[1] <= 1'b1;
            dC <= {dC[RLAT-1:0], f_crq_pin[0]};
            dQ <= {dQ[RLAT:0], go_ok[1]}; dG <= {dG[RLAT:0], go_ok[2]};
            if (f_crq_pin[0] && stream_av[f_crq_pin[2:1]]) f_iss[1] <= 1'b1;
            if (is_cp || is_cf || is_cl) f_iss[2] <= 1'b1;
            if (is_st) begin
                if (n_d_pin[27]) f_iss[2] <= 1'b1;
                else begin
                    if (act[1 + n_d_pin[26]] && !(go[1 + n_d_pin[26]] && u_n[1 + n_d_pin[26]] == 5'd0)) f_iss[0] <= 1'b1;
                    act[1 + n_d_pin[26]] <= 1'b1; u_row[1 + n_d_pin[26]] <= n_d_pin[25:12]; u_n[1 + n_d_pin[26]] <= n_d_pin[11:7];
                end
            end

        end
        for (k = 0; k < 4; k = k + 1)
            stream_ar[14*k +: 14] <= (go_ok[1] && gl[1] == k[1:0]) ? u_row[1] : u_row[2];
        dlC[0] <= f_crq_pin[2:1]; dlQ[0] <= gl[1]; dlG[0] <= gl[2];
        for (k = 1; k <= RLAT+1; k = k + 1) begin
            dlQ[k] <= dlQ[k-1]; dlG[k] <= dlG[k-1];
        end
        for (k = 1; k <= RLAT; k = k + 1) dlC[k] <= dlC[k-1];
    end

 assign return_valid={dG[RLAT+1],dQ[RLAT+1],dC[RLAT]};
 assign return_lane={dlG[RLAT+1],dlQ[RLAT+1],dlC[RLAT]};
 always @(posedge ck) if(!rn)fault<=0;else fault<=|f_iss;
endmodule
`default_nettype wire
