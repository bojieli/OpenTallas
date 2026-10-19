# qfd_c_land_w257_safe: SAFE-QW-CB16 checklist

1 FIXED: data outputs are register Qs; ring inputs capture directly in slot registers. Read bank inputs are the explicitly landed crossing and terminate at read output flops (same window as parent). Reset r1/r2 per 24-bit slice, no reset on ring data.
2 PASS: 64.8 x129.6 outline; every possible local wire <=194.4 um Manhattan, no inter-child wire included in this leaf.
3 FIXED: kept hierarchy and per-24bit kept sel/r1/r2/warm copies. Select bit <=24 data gates +1 rotation. Confirm mapped keep audit in gate; unverified until synthesis.
4 FIXED: registered rotating one-hot selects, 4-way masked OR read, no runtime binary wide mux.
5 FIXED: full 514/516 ring splits into two 257/258b hard children; each ring <=1032b. Ring is circular storage, not a serial delay line. No indexed flop mux.
6 WAIVER: pin-bound 64.8x129.6 (aspect2), bank face <=516/128.52=4.02pins/um; no macros; one full-width standard cell region. Low utilisation expected from bank-export pin perimeter; this is explicit, not a measured 40-60% claim. Parent origins must be snapped43.2 and channels>=20um before parent gate.
7 FIXED: local hard-child clock, root beside register mass, io_hold_margin_ns0.03. TT/FF spread awaits gate. Parent root only hard-child clocks remains integration prerequisite.
8 FIXED: static continuous ring, no credit/backpressure. Two reset stages shift both landing epochs +1 versus historical halves; normal data latency unchanged K=2. Parent warm-up/compiler reset update required BEFORE binding. New halves remain unbound pending that work.
