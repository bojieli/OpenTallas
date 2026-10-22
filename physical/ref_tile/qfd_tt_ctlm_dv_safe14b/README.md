# qfd_tt_ctlm_dv_safe14b -- QE3-CTLM3 10-21: Q.STA.TTC.4 RTL successor of safe12c (W std band +86.4 um beside the calendar block (864 x 734.4): every macro/child, region box and N/S pin x += 86.4)

Netlist rtl/qwen_dv/lp9f_rr (CALREG 15, see results/rtl/qe3_ctlm3_1021/README.md): FIFO = flop rings + registered next head
(4 FIFO SRAMs removed), start pre-decode register (+1 start -> issue, head/ME aligned), flat issue flags, native_tok/pos/lcv
output registers.  Children (h16c u_hr, closed wtn), pins, recipe = safe12c.  Pair safe14a / safe14b: bind first to close.

## SAFE checklist
1 pins: safe12c plan (exact M3/M4 grants); native_tok/pos/lcv now registered beside u_hr | 2 reach: start decode and FIFO
head read are register-local (no SRAM->adder->E round trip) | 3 fanout: native census max 32 (lp9f_np PASS, lp9f_rr mapped
PASS) | 4 depth: class A (37 lv) cut by STARTREG + ISSUEFLAT, class B by FQREG (register -> KS -> reg); textbook 675 ps / 21 lv
| 5 storage: 2 program SRAMs + 3 OPROM + 2 ROM266 on the lattice; per-user FIFO = 1 kb flops (< 2 kb rule) | 6 floorplan:
fill 27 % (14a) / 24 % (14b), enlarge-not-squeeze | 7 clock: regional ck_core / ck_hr + L5 landings as safe12c; the hard-child
insertion (wtn R 142 / head R 303) still needs ROOT's spine API for clock_rule | 8 reset: control/valid only (new start
valid regs reset, data regs reset-free).
