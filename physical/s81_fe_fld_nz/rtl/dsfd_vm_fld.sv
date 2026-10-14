(* keep_hierarchy = "yes" *)
module dsfd_vm_be_kreg #(parameter integer W = 1, parameter integer ID = 0) (input wire clk, input wire [W-1:0] d, output reg [W-1:0] q);
    always @(posedge clk) q <= d;
endmodule

module dsfd_vm_fob #(parameter integer STALE = 0, parameter integer WEV = 1, parameter integer MV = 0,
                     parameter integer DF = 1, parameter integer DX = 0) (
    input  wire clk, input wire rn,
    input  wire i_v, input wire i_we, input wire [13:0] i_row, input wire [15:0] i_m, input wire [511:0] i_d,
    output wire [4*(15 + WEV + 4*MV + 128*DF)-1:0] s_o, output wire [((DX > 0) ? DX : 1)-1:0] x_o, output wire [31:0] k_o
);
    localparam integer SW = 15 + WEV + 4*MV + 128*DF;
    reg b_v, b_we; reg [13:0] b_row; reg [15:0] b_m; reg [511:0] b_d;
    always @(posedge clk) begin
        if (!rn) b_v <= 1'b0; else b_v <= i_v;
        b_we <= i_we; b_row <= i_row; b_m <= i_m; b_d <= i_d;
    end
    wire c_v, c_we; wire [13:0] c_row; wire [15:0] c_m; wire [511:0] c_d;
    generate if (STALE != 0) begin : g_st
        reg s_v6, s_we6; reg [13:0] s_row6; reg [15:0] s_m6; reg [511:0] s_d6;
        always @(posedge clk) begin
            if (!rn) s_v6 <= 1'b0; else s_v6 <= b_v;
            s_we6 <= b_we; s_row6 <= b_row; s_m6 <= b_m; s_d6 <= b_d;
        end
        assign c_v = s_v6; assign c_we = s_we6; assign c_row = s_row6; assign c_m = s_m6; assign c_d = s_d6;
    end else begin : g_ns
        assign c_v = b_v; assign c_we = b_we; assign c_row = b_row; assign c_m = b_m; assign c_d = b_d;
    end endgenerate
    genvar gs;
    generate for (gs = 0; gs < 4; gs = gs + 1) begin : g_s
        wire [SW-1:0] w;
        assign w[SW-1] = rn ? c_v : 1'b0;
        if (WEV != 0) begin : g_we assign w[SW-2] = c_we; end
        assign w[4*MV + 128*DF +: 14] = c_row;
        if (MV != 0) begin : g_m assign w[128*DF +: 4] = c_m[4*gs +: 4]; end
        if (DF != 0) begin : g_d assign w[127:0] = c_d[128*gs +: 128]; end
        dsfd_vm_be_kreg #(.W(SW), .ID(600 + gs)) u_s0 (.clk(clk), .d(w), .q(s_o[SW*gs +: SW]));
    end
    if (DX > 0) begin : g_x
        dsfd_vm_be_kreg #(.W(DX), .ID(604)) u_x0 (.clk(clk), .d(c_d[DX-1:0]), .q(x_o));
    end else begin : g_nx
        assign x_o = 1'b0;
    end endgenerate
    (* keep = 1 *) reg k_v; (* keep = 1 *) reg k_we; (* keep = 1 *) reg [13:0] k_row; (* keep = 1 *) reg [15:0] k_m;
    always @(posedge clk) begin
        if (!rn) k_v <= 1'b0; else k_v <= b_v;
        k_we <= b_we; k_row <= b_row; k_m <= b_m;
    end
    assign k_o = {k_v, k_we, k_row, k_m};
endmodule

module dsfd_vm_fld_pick2 #(parameter integer N=6)
 (input wire[N-1:0] req,output wire[N-1:0] first,second);
 generate for(genvar k=0;k<N;k=k+1) begin:g_k
  localparam[N-1:0] BEFORE=({{(N-1){1'b0}},1'b1}<<k)-1'b1;
  wire[N*N-1:0] pairs;
  for(genvar a=0;a<N;a=a+1) begin:g_a
   for(genvar b=0;b<N;b=b+1) begin:g_b
    assign pairs[a*N+b]=(a<k && b<a) ? (req[a]&req[b]) : 1'b0;
   end
  end
  assign first[k]=req[k] && !(| (req&BEFORE));
  assign second[k]=req[k] && (| (req&BEFORE)) && !(|pairs);
 end endgenerate
endmodule

(* keep_hierarchy = "yes" *)
module dsfd_vm_fld (
    input  wire [0:0]    ck, input wire rni,
    input  wire [9:0]    av, input wire [5259:0] ret, input wire [3:0] ok, input wire [9:0] ovf, input wire [9:0] sflt,
    output wire [9:0]    g,
    output wire [1143:0] s_o,            
    output wire [63:0]   k_o,
    output reg  [2:0]    t_cts,
    output reg           ovr_o, output reg sflt_o,
    output reg  [0:0]    rn_o            
);
    localparam integer NSVC = 1, NLL = 10, NLP = 2, LGL = 1, LDL = 1, LSD = 3 + 2 + 3;
    wire clk = ck[0];
    reg rn;
    (* keep = 1 *) reg [0:0] rn_k;
    always @(posedge clk) begin rn <= rni; rn_k <= rn; end
    always @* rn_o = rn_k;
    wire [NLL-1:0] ll_avd = av; wire [NLL*512-1:0] ll_od; wire [NLL*14-1:0] ll_or;    
    genvar gl;
    generate for (gl = 0; gl < NLL; gl = gl + 1) begin : g_u
        assign ll_od[512*gl +: 512] = ret[526*gl +: 512]; assign ll_or[14*gl +: 14] = ret[526*gl + 512 +: 14];
    end endgenerate
    reg [NLL-1:0] ll_tk;
    reg [NLL-1:0] av_r; reg [NLL-1:0] g_r [0:LGL-1];
    reg [NLL*512-1:0] dd_r [0:LDL-1]; reg [NLL*14-1:0] dr_r [0:LDL-1];
    reg [6:0] lc [0:NLL-1];              
    reg [$clog2(NLL)-1:0] ll_ptr; reg [NLP-1:0] lp_v; reg [NLP*14-1:0] lp_row; reg [NLP*512-1:0] lp_d;
    reg [NLP-1:0] lsel_v; reg [$clog2(NLL)-1:0] lsel [0:NLP-1];
reg [NLL-1:0] lc_nz;
always @(posedge clk) begin : p_lc_nz integer li;
    if (!rn) lc_nz <= {NLL{1'b0}};
    else for (li = 0; li < NLL; li = li + 1)
        lc_nz[li] <= ((lc[li] > 7'd1) & !((lc[li] == 7'd127) & av_r[li] & !ll_tk[li]))
                   | ((lc[li] == 7'd1) & (av_r[li] | !ll_tk[li]))
                   | ((lc[li] == 7'd0) & av_r[li] & !ll_tk[li]);
end
wire [5:0] priority_req={lc_nz[9],lc_nz[8],lc_nz[7],lc_nz[6],lc_nz[1],lc_nz[0]};
wire [3:0] flow_req={lc_nz[5],lc_nz[4],lc_nz[3],lc_nz[2]};
wire [3:0] flow_first,flow_second;
wire [35:0] ranks_first,ranks_second;
genvar rank;
generate for(rank=0;rank<6;rank=rank+1) begin:g_fixed_rank
    wire [5:0] rr,ff,ss;
    if(rank==0) begin:g_zero
        assign rr=priority_req;
        assign ranks_first[6*rank+:6]=ff;
        assign ranks_second[6*rank+:6]=ss;
    end else begin:g_rot
        assign rr={priority_req[rank-1:0],priority_req[5:rank]};
        assign ranks_first[6*rank+:6]={ff[5-rank:0],ff[5:6-rank]};
        assign ranks_second[6*rank+:6]={ss[5-rank:0],ss[5:6-rank]};
    end
    dsfd_vm_fld_pick2 #(.N(6)) u_rank(.req(rr),.first(ff),.second(ss));
end endgenerate
dsfd_vm_fld_pick2 #(.N(4)) u_flow(.req(flow_req),.first(flow_first),.second(flow_second));
reg [5:0] fixed_first,fixed_second;
reg [5:0] rk_sel;   // registered one-hot rank of the CURRENT ll_ptr (decoded from its next value one edge early)
function automatic [5:0] rk_dec(input [3:0] p);
 case(p) 0,10:rk_dec=6'b000001; 1,11:rk_dec=6'b000010; 7:rk_dec=6'b001000; 8:rk_dec=6'b010000; 9:rk_dec=6'b100000;
  default:rk_dec=6'b000100; endcase
endfunction
always @(posedge clk) begin
 if (!rn) rk_sel <= rk_dec(4'd0);
 else rk_sel <= rk_dec((ll_ptr == NLL - 1) ? 4'd0 : ll_ptr + 4'd1);
end
always @* begin : p_rk integer k;
  fixed_first=6'd0; fixed_second=6'd0;
  for(k=0;k<6;k=k+1) begin
   begin
    fixed_first=fixed_first|(ranks_first[6*k+:6]&{6{rk_sel[k]}});
    fixed_second=fixed_second|(ranks_second[6*k+:6]&{6{rk_sel[k]}});
   end
  end
 end
wire[9:0] nonflow_first={fixed_first[5:2],4'b0,fixed_first[1:0]};
wire[9:0] nonflow_second={fixed_second[5:2],4'b0,fixed_second[1:0]};
wire[9:0] first_selected=(|fixed_first) ? nonflow_first : {4'b0,flow_first,2'b0};
wire[9:0] second_selected=(|fixed_second) ? nonflow_second : ((|fixed_first) ? {4'b0,flow_first,2'b0} : {4'b0,flow_second,2'b0});
always @* begin:p_parallel_grant integer li;
 ll_tk=first_selected|second_selected;
 lsel_v={|second_selected,|first_selected};lsel[0]=0;lsel[1]=0;
 for(li=0;li<NLL;li=li+1) begin
  lsel[0]=lsel[0]|(li[3:0]&{4{first_selected[li]}});
  lsel[1]=lsel[1]|(li[3:0]&{4{second_selected[li]}});
 end
end
    reg [NLL-1:0] sd_oh [0:NLP-1][0:LSD-1]; reg [NLP-1:0] sd_v [0:LSD-1];
    always @(posedge clk) begin : p_l578 integer lk, li, i; reg [511:0] dsel; reg [13:0] rsel;
        if (!rn) begin
            lp_v <= {NLP{1'b0}}; ll_ptr <= 0; av_r <= {NLL{1'b0}};
            for (li = 0; li < NLL; li = li + 1) lc[li] <= 7'd0;
            for (i = 0; i < LGL; i = i + 1) g_r[i] <= {NLL{1'b0}};
            for (i = 0; i < LSD; i = i + 1) sd_v[i] <= {NLP{1'b0}};
        end else begin
            ll_ptr <= (ll_ptr == NLL - 1) ? 0 : ll_ptr + 1'b1;
            av_r <= ll_avd;
            for (li = 0; li < NLL; li = li + 1) lc[li] <= lc[li] + {6'd0, av_r[li]} - {6'd0, ll_tk[li]};
            g_r[0] <= ll_tk;
            for (i = 1; i < LGL; i = i + 1) g_r[i] <= g_r[i-1];
            sd_v[0] <= lsel_v;
            for (i = 1; i < LSD; i = i + 1) sd_v[i] <= sd_v[i-1];
            lp_v <= sd_v[LSD-1];
        end
        for (lk = 0; lk < NLP; lk = lk + 1) begin
            sd_oh[lk][0] <= lsel_v[lk] ? ({{(NLL-1){1'b0}}, 1'b1} << lsel[lk]) : {NLL{1'b0}};
            for (i = 1; i < LSD; i = i + 1) sd_oh[lk][i] <= sd_oh[lk][i-1];
            dsel = 512'd0; rsel = 14'd0;
            for (li = 0; li < NLL; li = li + 1) if (sd_oh[lk][LSD-1][li]) begin
                dsel = dsel | dd_r[LDL-1][512*li +: 512]; rsel = rsel | dr_r[LDL-1][14*li +: 14];
            end
            lp_row[14*lk +: 14] <= rsel; lp_d[512*lk +: 512] <= dsel;
        end
        dd_r[0] <= ll_od; dr_r[0] <= ll_or;
        for (i = 1; i < LDL; i = i + 1) begin dd_r[i] <= dd_r[i-1]; dr_r[i] <= dr_r[i-1]; end
    end
    assign g = g_r[0];
    reg [3:0] ok_q; reg [9:0] ov_q, sf_q;
    always @(posedge clk) begin
        if (!rn) begin ok_q <= 4'd0; t_cts <= 3'd0; ovr_o <= 1'b0; sflt_o <= 1'b0; end
        else begin ok_q <= ok; t_cts <= {1'b0, 1'b1, &ok_q}; ovr_o <= |ov_q; sflt_o <= |sf_q; end
        ov_q <= ovf; sf_q <= sflt;
    end
    genvar gj, gs;
    generate for (gj = 0; gj < 2; gj = gj + 1) begin : g_p
        wire [571:0] fs;
        dsfd_vm_fob #(.WEV(0)) u_b (.clk(clk), .rn(rn), .i_v(lp_v[gj]), .i_we(1'b1), .i_row(lp_row[14*gj +: 14]), .i_m(16'hffff),
            .i_d(lp_d[512*gj +: 512]), .s_o(fs), .x_o(), .k_o(k_o[32*gj +: 32]));
        for (gs = 0; gs < 4; gs = gs + 1) begin : g_s
            assign s_o[(2*gs + gj)*143 +: 143] = fs[143*gs +: 143];
        end
    end endgenerate
endmodule
