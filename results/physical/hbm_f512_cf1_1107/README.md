# F512 vCF1 new source form

This is a full rebuild candidate, not another ECO on the stopped four-pass result. The base is the unchanged native ABI core and reviewed eight-clock-root density/common-alignment contract from intel1 hbm-form-timing-12/f512rp_eco/i3. Its historical TT+51/FF+.02 and13slew were not closure. No old result is overwritten.

18input buses/2059bits gain one coherent input relay cycle. A form-local delivered-reset edge has immediate assertion and one-cycle later release, matching those inputs; core RTL and all eight native clock roots stay unchanged. Output latency+1cycle (.833ns); throughput unchanged. The parent compiler/latency table must adopt this before qualification. Do not count the candidate prematurely.

Actual old pin/native capture coordinates give worst482.127um. The new per-bit legal midpoint guides avoid all three macros plus4.32um halos; worst leg including guide extent280.113um. Added flop area600.40um2, peak additional8um-bin area fraction.15947. Viewed f512_relay_proposal_v2.png: west/east/lower free corridors, no relay box on a macro or narrow abutment. PASS for one PLACE pilot; inspect actual placement and both legs before CTS/route. The macro outline/pins/routing layer remain unchanged. Reg2reg hold scope prevents port padding; fanout64->8 addresses long weak driver trees. The native clock contract is deliberately preserved because independent plain trees previously failed internal hold.

A real single-bank SRAM reference/candidate bench covers4096cycles,2564reads,412countedwrites and actualfault activity, with zero differences for the coherent relay. An exercised row-bit268 bypass mutant produced6516mismatches. The first bit267 mutant was dead on even-row write-lane0 and escaped; that failed negative control is preserved and not claimed as evidence. Previous image probes failed because the ORFS image lacks iverilog; corrected to the installed host compiler, no RTL fix inferred. See BENCH_RESULTS.txt.

The fresh kit inputs and source recipe are committed before launch. Runtime signoff/LEC bundles are refreshed from the released93c tool cohort. Final gates and parent contract qualification still remain.
