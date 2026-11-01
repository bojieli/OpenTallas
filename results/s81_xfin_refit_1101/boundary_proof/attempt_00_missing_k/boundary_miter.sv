module old_boundary(input clk,rstn,go,input [2:0] f_v,input [5:0] f_t,input [23:0] f_base,input [479:0] f_d,
 input wr_v,input [9:0] wr_n,input [31:0] wr_d,input f_add,input [2:0] dup,
 output reg r_v,output reg [31:0] r_hh,r_kk,r_dd,output fault,
 output [2:0] iv_out,dn_out,output [95:0] held_out);
 localparam P=3,T=3,NVP=128;
 reg go_t;
    always @(posedge clk or negedge rstn) if (!rstn) go_t <= 1'b0; else go_t <= go;
    reg [P-1:0] iv; reg [P*2-1:0] it; reg [P*8-1:0] ib; reg [P*K*32-1:0] id;
    always @(posedge clk or negedge rstn) if (!rstn) iv <= {P{1'b0}}; else iv <= go_t ? {P{1'b0}} : f_v;
    always @(posedge clk) begin it <= f_t; ib <= f_base; id <= f_d; end

     // roots: node 1 of each tree
    reg [T-1:0] dn; reg flt;
    always @(posedge clk or negedge rstn)
        if (!rstn) begin dn <= {T{1'b0}}; r_v <= 1'b0; flt <= 1'b0; end
        else begin
            r_v <= 1'b0;
            if (go_t) begin dn <= {T{1'b0}}; flt <= 1'b0; end
            else begin
                if (wr_v && wr_n == 1 * 1)           dn[0] <= 1'b1;
                if (wr_v && wr_n == NVP + 1)         dn[1] <= 1'b1;
                if (wr_v && wr_n == 2 * NVP + 1)     dn[2] <= 1'b1;
                if (dn != {T{1'b1}} && (dn | {wr_v && wr_n == 2 * NVP + 1, wr_v && wr_n == NVP + 1, wr_v && wr_n == 1})
                    == {T{1'b1}}) r_v <= 1'b1;
                if (f_add || (|dup)) flt <= 1'b1;
            end
        end
    always @(posedge clk) begin
        if (wr_v && wr_n == 1)           r_hh <= wr_d;
        if (wr_v && wr_n == NVP + 1)     r_kk <= wr_d;
        if (wr_v && wr_n == 2 * NVP + 1) r_dd <= wr_d;
    end
    assign fault = flt;

 assign iv_out=iv;assign dn_out=dn;assign held_out={r_dd,r_kk,r_hh};
endmodule

module new_boundary(input clk,rstn,go,input [2:0] f_v,input [5:0] f_t,input [23:0] f_base,input [479:0] f_d,
 input wr_v,input [9:0] wr_n,input [31:0] wr_d,input f_add,input [2:0] dup,
 output reg r_v,output reg [31:0] r_hh,r_kk,r_dd,output fault,
 output [2:0] iv_out,dn_out,output [95:0] held_out);
 localparam P=3,T=3,NVP=128;
 reg go_t;
    always @(posedge clk or negedge rstn) if (!rstn) go_t <= 1'b0; else go_t <= go;
    // S81-CORES-KITS-9 10-31 (hard child face rule, raw face_guard): f_v lands RAW in its face flop iv_r; the go clear
    // is applied after the flop with go_t delayed by the same edge (iv = iv_r & ~go_q == old go_t ? 0 : f_v register,
    // cycle-exact, both reset 0 under rstn).
    reg [P-1:0] iv_r; reg go_q; reg [P*2-1:0] it; reg [P*8-1:0] ib; reg [P*K*32-1:0] id;
    always @(posedge clk or negedge rstn) if (!rstn) begin iv_r <= {P{1'b0}}; go_q <= 1'b0; end
                                         else begin iv_r <= f_v; go_q <= go_t; end
    wire [P-1:0] iv = iv_r & {P{~go_q}};
    always @(posedge clk) begin it <= f_t; ib <= f_base; id <= f_d; end

     // roots: node 1 of each tree
    reg [T-1:0] dn; (* keep = "true" *) reg flt;
    always @(posedge clk or negedge rstn)
        if (!rstn) begin dn <= {T{1'b0}}; r_v <= 1'b0; flt <= 1'b0; end
        else begin
            r_v <= 1'b0;
            if (go_t) begin dn <= {T{1'b0}}; flt <= 1'b0; end
            else begin
                if (wr_v && wr_n == 1 * 1)           dn[0] <= 1'b1;
                if (wr_v && wr_n == NVP + 1)         dn[1] <= 1'b1;
                if (wr_v && wr_n == 2 * NVP + 1)     dn[2] <= 1'b1;
                if (dn != {T{1'b1}} && (dn | {wr_v && wr_n == 2 * NVP + 1, wr_v && wr_n == NVP + 1, wr_v && wr_n == 1})
                    == {T{1'b1}}) r_v <= 1'b1;
                if (f_add || (|dup)) flt <= 1'b1;
            end
        end
    // S81-CORES-KITS-9 10-31 (hard child face rule: no output pin flop reads itself): the root values are held in
    // internal registers *_s; the r_* pin flops load the root value on the r_v edge and ZERO otherwise, so r_* equal
    // the old held r_* whenever r_v = 1 (the only cycle ot_s81dv_xfin reads them: ehh/ekk/edd and e_* load under cr_v).
    // fault = its own pin flop loading the next state of the kept sticky flt (same value every cycle, as xfin's fault).
    wire w_hh = wr_v && wr_n == 1, w_kk = wr_v && wr_n == NVP + 1, w_dd = wr_v && wr_n == 2 * NVP + 1;
    wire fin = !go_t && dn != {T{1'b1}} && (dn | {w_dd, w_kk, w_hh}) == {T{1'b1}};   // = the r_v set condition
    reg [31:0] hh_s, kk_s, dd_s;
    always @(posedge clk) begin
        if (w_hh) hh_s <= wr_d;
        if (w_kk) kk_s <= wr_d;
        if (w_dd) dd_s <= wr_d;
        r_hh <= fin ? (w_hh ? wr_d : hh_s) : 32'd0;
        r_kk <= fin ? (w_kk ? wr_d : kk_s) : 32'd0;
        r_dd <= fin ? (w_dd ? wr_d : dd_s) : 32'd0;
    end
    reg flt_o;
    always @(posedge clk or negedge rstn)
        if (!rstn) flt_o <= 1'b0; else flt_o <= go_t ? 1'b0 : (flt | f_add | (|dup));
    assign fault = flt_o;

 assign iv_out=iv;assign dn_out=dn;assign held_out={dd_s,kk_s,hh_s};
endmodule
module top #(parameter MUT=0)(input clk,rstn,go,input [2:0] f_v,input [5:0] f_t,input [23:0] f_base,input [479:0] f_d,
 input wr_v,input [9:0] wr_n,input [31:0] wr_d,input f_add,input [2:0] dup);
 wire ov,nv,ofault,nfault;wire [31:0] oh,ok,od,nh,nk,nd;wire [2:0] oi,ni,odn,ndn;wire [95:0] oheld,nheld;
 old_boundary o(clk,rstn,go,f_v,f_t,f_base,f_d,wr_v,wr_n,wr_d,f_add,dup,ov,oh,ok,od,ofault,oi,odn,oheld);
 new_boundary n(clk,rstn,go,f_v,f_t,f_base,f_d,wr_v,wr_n,wr_d,f_add,dup,nv,nh,nk,nd,nfault,ni,ndn,nheld);
 wire [95:0] observed_new={nd,nk,nh} ^ ((MUT && nv) ? 96'd1 : 96'd0);
 reg initialized=0;
 always @(posedge clk) begin
  if (!rstn) initialized<=1;
  if (initialized) begin
   assert(oi==ni);assert(odn==ndn);assert(ov==nv);assert(ofault==nfault);
   assert(!ov || {od,ok,oh}==observed_new);
   assert(!odn[0] || oheld[31:0]==nheld[31:0]);
   assert(!odn[1] || oheld[63:32]==nheld[63:32]);
   assert(!odn[2] || oheld[95:64]==nheld[95:64]);
  end
 end
endmodule
