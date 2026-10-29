// P = control state equal, valid-slot contents equal AND old write_oh == 1 << wc[1:0].
// Proof 1 (inductive, sat -tempinduct-inductonly k=1): P(t) -> P(t+1) for every input (rsi, i free).
// Proof 2 (inductive): I = write_oh == 1 << wc[1:0] on the OLD writer alone is preserved by every edge, and the
// first edge with rq low establishes it (reset branch) -> every reachable post-reset state satisfies P when the two
// writers start equal; then bank/epo/vld (the writer outputs = whole writer state) are identical forever.
module miter #(parameter integer W=8) (input wire ck, rsi, input wire [W-1:0] i, output wire p, output wire inv);
  wire [4*W-1:0] bo, bn; wire [11:0] eo, en; wire [3:0] vo, vn; wire ro, rn; wire [2:0] wo, wn; wire [3:0] ho, hn;
  old_local #(.W(W),.D(4)) uo(.ck(ck),.rsi(rsi),.i(i),.bank(bo),.epo(eo),.vld(vo),.x_rq(ro),.x_wc(wo),.x_woh(ho));
  new_local #(.W(W),.D(4)) un(.ck(ck),.rsi(rsi),.i(i),.bank(bn),.epo(en),.vld(vn),.x_rq(rn),.x_wc(wn),.x_woh(hn));
  assign inv = (ho == (4'b0001 << wo[1:0]));
  // slot s data/epoch need to agree only while slot s is valid (invalid slots are never presented by the reader:
  // o = warm && |(vld & read_oh) ? bank[read_oh] : 0, reader unchanged and fed the same vld/epo)
  wire [3:0] slot_ok;
  for (genvar s = 0; s < 4; s = s + 1) begin : g_s
    assign slot_ok[s] = !vo[s] || (bo[s*W+:W] == bn[s*W+:W] && eo[s*3+:3] == en[s*3+:3]);
  end
  assign p = inv && &slot_ok && vo == vn && ro == rn && wo == wn && ho == hn;
endmodule
module inv_only #(parameter integer W=8) (input wire ck, rsi, input wire [W-1:0] i, output wire inv);
  wire [4*W-1:0] bo; wire [11:0] eo; wire [3:0] vo; wire ro; wire [2:0] wo; wire [3:0] ho;
  old_local #(.W(W),.D(4)) uo(.ck(ck),.rsi(rsi),.i(i),.bank(bo),.epo(eo),.vld(vo),.x_rq(ro),.x_wc(wo),.x_woh(ho));
  assign inv = (ho == (4'b0001 << wo[1:0]));
endmodule
