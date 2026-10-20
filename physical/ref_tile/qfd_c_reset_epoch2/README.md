
SAFE checklist (unbound prototype):
1 PASS rst_l0/rst_l1 two face stages, rst_o register Q.
2 PASS17.28um box, total local Manhattan34.56<315/405.
3 PASS first reset pin drives1reg, counter bits<7 and local flag fanout<16.
4 PASS small increment+constant compare; mapped depth measured by gate, no wide mux.
5 FIXED local padding encoded as static release count, no indexed data storage/delay line.
6 WAIVER17.28square candidate is driven by power/clock minimum; sparse control utilisation is explicit, not40-60%. Macros absent, onefull-width cell region, pins full faces. Confirm PG minimum with gate; parent origins must43.2grid+20channels.
7 FIXED local hard-child clock reference, io_hold0.03; TT/FF spread awaits gate.
8 PASS static initialization only, no credits/backpressure/stalls. RELEASEexact; RELEASE>2 asserts cancellation within3edges, intentionally earlier than old padding. Parent canceled-reset semantics/MUT8/actualphysicalresetmodel REQUIRED before binding.
