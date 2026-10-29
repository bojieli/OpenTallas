# QC native macro power contact coupon

Picture personally viewed: results/qc_macro_pg_1029/coupon_review.png.

Verdict PASS-COND for the bounded 754-term physical connectivity coupon only. The full die view places one VDD/VSS access pair in each existing macro, without new cells, pin movement, or routing channels. The magnified native crossing shows the VIA78 M7 pad wholly enclosed by the actual same-net vertical macro PG pin and the M8 pad enclosed by the horizontal canonical same-net stripe. Adjacent opposite M7 rail remains separate. No wire bridge or patch is added. All 754 selected contacts clear actual h800 signals, obstructions, and the 484 joint clock reservations at native M7/M8 spacing. The unchanged macro layout and clock tap placement introduce no new data reach or clock latency changes.

This is not die PG closure, IR capacity, timing or a routing approval. One contact per macro term deliberately does not establish distributed supply capacity; 1690 of 137306 native M7 fragments do not directly cross same-net M8 and require internal PG connectivity authority or further access design before per-fragment closure. No RTL or cycles change.
