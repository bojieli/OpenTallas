
## UCIE7 SAFE review (HBM-OWN/PHY2 10-21 13:20) -- structural FALLBACK for the ck_rck boundary spread FAIL (coli 93.6 / colj 91.5 / colg 84 ps TT > 80)
Geometry: coli = ROOT-approved colf geometry 259.2x1771.2 (tx hop 432 um repeated, colf risk kept); hop rst_rck pin->sync capped 380 um. RTL/netlist identical to colh/coli (ucie6 @d8191f6a3 benches + mutants on Verilator 5.050 stand: audit PASS, lockstep m0 PASS / m4 FAIL, link MODE 0/1/2 PASS 6000/6000, mut1/2/3 FAIL).
Cause: the rck region's only boundary flops = rst_rck synchroniser u_lpr_rck (2 stages) fixed by io_flop_at_pins at the N pin, 260-430 um from the rck mass (u_prr 513 b + u_rm write side at the rxm top, pma_rck pin, SRAM wclk); lone CTS branch 59-94 ps late vs the pma_rck macro pin.
1 pins PASS: core pins registered in RTL as colh; rst_rck is a quasi-static reset input landed 2 stages on ck_rck, now INSIDE the rck region (pin->sync = one repeated input hop).
2 reach FIX: rst_rck pin->sync hop <= 380 um (< 405), buffered by the resizer at its true length (pair FIRM through GPL/resizer); colh in->reg slack was +436 ps at 216 um.
3 fanout PASS: unchanged (sync q -> u_rm write-side / u_sts control resets only; census max 32 in the gate).
4 depth PASS: unchanged (colh reg->reg +265, macro->out +239).
5 storage PASS: dual-clock SRAM + PMA abstracts unchanged.
6 floorplan PASS: outline/macros unchanged; the pair sits in the PMA-top channel beside the rck mass (no squeeze).
7 clock FIX: the reset synchroniser joins the rck region's local tree (seed above the rxm pma_rck pin, then the measured ck_rck sink median) -> no lone N-pin branch; 3 regional roots, no new phase.
8 reset PASS: reset only control bits, landed per region on its own clock (rst_tx/rst_rx unchanged at their pins, rst_rck landed in its region); no global reset.
Hooks: PRE_GPL tools/ref_tile/specs/hbm_pdie_ucie_rck_rst_seed.tcl (after io_flop_at_pins), PRE_DPL tools/ref_tile/specs/hbm_pdie_ucie_rck_rst_land.tcl. Placement only, no netlist edit.
PDN: inherited validated macro_m5 grid (copied from the colh/coli kit; the generator still lacks it -> PDN-0233).
