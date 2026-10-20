# CTRL generated-clock source/export repair

The exact d169b1906 candidate declares forwarded `ck_o_fwd` without an explicit master. Native OpenSTA canonical export consequently omits `-master_clock`, and the current strict clock-family recorder correctly refuses the declaration. Add `-master_clock core_clk` at the source and its two already-generated route/signoff copies. Periods, waveform, uncertainty, data paths, reset, IO budgets, RTL, and physical geometry do not change. No generic helper inference or clock-family exemption is added.

The old submitted job `s81ctrl_rg2_np-np-d169b1906` and its snapshot remain immutable. `original_failure.json` preserves its double-crash receipt. The fresh branch changes only source/export evidence; it authorizes no rerun of that job.

## Native proof

The bounded two-root fixture uses the exact old/new generated-clock declarations and canonical helper from main 58fc3dbc1. On fleet ot-epyc4, unit oth-ubuntu-3535373-1792439090, OpenSTA 3.1.0 exports the baseline without a master and exits 1 with the original clock-family error. The fixed declaration exports name ck_o_fwd, master core_clk, source clk, divide 1, and exits 0 after `ot_cf_refresh` proves ck_o_fwd -> core_clk with hclk independent. Logs and canonical exports are committed. The first OpenROAD invocation omitted technology LEF and failed infrastructure initialization; its logs are preserved and are not counted as a clock witness. `run.sh` runs the final STA probe inside the same fleet Docker image.

This is a source/export ancestry mechanism proof, not a post-CTS native insertion measurement or physical-clock qualification. No new gate, route, REVIEW, or submission was launched.

## Exact candidate SAFE checklist

1. Pins: OPEN. The older kit claims domain-local face flops and two-stage reset; re-establish actual all-pin boundary and per-domain reset proofs on the chosen structural successor. No exemption based on that README claim.
2. Reach: OPEN. Old claimed per-PC reach 266um and textbook reach 0 are not an uncapped native 405um graph certificate. The distinct 22-bank placement already exposed reset/data violations and does not qualify this candidate.
3. Fanout: OPEN. Old direct-count PASS is not an all-driver BUF/INV-transparent logical-pin census. All reset, FF, comb, top-input, macro and tie roles need exact native accounting.
4. Depth: DIAGNOSTIC ONLY. Original gate reports 375.1ps mapped depth; full native source-cone/current-phase review remains owed.
5. Storage: SRAM PRESENT. The four production FIFO memories are real 16x546 dual-clock SRAM macros. This proof does not waive any remaining indexed state or >=3-deep delay-chain inventory.
6. Floorplan: FAIL. Exact LEF has 825 signal/clock contacts on each 81um W/E face, or 10.185 contacts/um (>6). See contact_audit.json. Macro origins are on the 43.2um lattice; that alone cannot repair contact density. Candidate outline 531.25x302.4, four macros, is distinct from the 22-bank source and needs a true structural successor plus parent regrant.
7. Clock: OPEN. Two roots plus forwarded generated output are now exportable. The old gate had CTS rc0 but native insertion rc1; there is no qualified TT/FF <=80ps spread or matched-neighbor boundary certificate. IO hold margin remains .03. Actual macro clock timing and contact/PG escape remain owed.
8. Schedule: UNCHANGED BY THIS PATCH. No added register, edge, or CDC latency. Prior SRAM equivalence evidence remains historical; the chosen new structural successor must carry its real compiler/die schedule and production-shape throughput proof.

## Next owner

Use the current 22-bank or another analytically sized sparse-pin structural source, close its actual reset/data reach and transparent fanout, registered boundaries, legal full-face density/PG/OBS escape, and native dual-clock contract. Carry this explicit-master declaration into that independently fingerprinted kit. Review all eight SAFE items before any fresh gate; do not resubmit the four-wide d169 physical candidate just because its SDC parser is repaired.
