Actual production A+B selector candidates, opt-in only

Use recipes dsdv_bksel_c_pipe_ab_r1 and dsdv_bksel_c_pipe_ab_r2. They patch the active ot_s81ph_sel_su_pipe used under SEARCH_PIPE1 in the production dsdv_bksel_c top. The earlier foreign R1/R2 kits changed an unused native SU; their positive FF-scene CTS estimate did not measure this mechanism or establish TT closure. The B-only source copies and recipes remain as diagnostic history.

The candidates replace both measured critical dynamic selectors with highest-one masks and constant-index balanced OR trees. R1 adds no selector state. R2 registers compare-NEXT masks on the same edges as the existing sum capture. A bucket15 returns zero; B bucket15 returns acc_b4; mask0 retains the original index1 fallback. There are no added cycles or external ABI changes. Actual configurations are Q4/CB11/XR6, coarseQW11 and fineQW21, with XW21 in both SUs. Production/default RTL, recipes, pins and outline are untouched.

The smallest actual A+B cut proof passed524304 checks across all65536 masks per A/B/quota case, changing lane data and the real compare/capture/result register coupling. Stale-mask mutants were caught. See results/rtl/bksel_pipe_select_1131/cut. The full-SU Icarus attempt exhausted its1GB elaboration allocation; no full-SU simulation PASS is claimed.

Fresh synthesis measured R1 mapped134642cells/25659FF and R2 mapped132075/25719FF. The60 additional R2 FFs are within the64-FF estimate; active pipeline ah/gh/az/gz were confirmed. Raw and mapped face checks passed5511 bits per candidate.

Both initial official whole-kit checks failed the same five unchanged-controller correspondence points: c_rep/ovf and four replicated command37 registers. Their exact failure receipts remain immutable. Separate proofs on each candidate's own exact AIGs establish known equal64-edge reset bases and individual induction for the five correspondence lemmas. The recipe lec_hints files are byte copies of those receipts' proven_hints.json. They remain untrusted hints: the normal engine must reprove them and the complete whole-kit miter. Separate normal official continuations passed: R1 55682/55682 points (exit0 at14:11:35 PST), R2 55768/55768 (exit0 at14:37:26 PST), zero differs/undecided. The normal engine also proved anonymous-register correspondence proposals; only the five explicit hints were supplied. Exact source/config/pin/reset/netlist identities are separately pinned, while each receipt retains its missing PROVENANCE.json limitation. See results/rtl/bksel_pipe_select_1131/{r1,r2}_correspondence_lemmas and the original failure directories.

Portable fresh generation:

    python3 physical/die_plan/s81/cores/legacy/gen_core_kit_legacy.py \
      --module dsdv_bksel_c_pipe_ab_r2 \
      --recipes tools/s81_ph/bksel_pipe_select_1131/recipes.json \
      --out OWN_KITS --trial

Use the corresponding ab_r1 recipe for R1. The generator copies each recipe's five untrusted hints into the kit. OT_LEC_HINTS_PRESEED=1 optionally changes proposal order; it does not waive induction or whole-kit comparison. Render the unchanged388.8x172.8/5513-pin source plan, run fresh SYNTH/normal LEC/PLACE, and stop for actual geometry LOOK before CTS. Every new registered selector must enter the actual clock-sink census. Use the merged canonical unplaced guard/final two-mode repair hooks and exact-library CORNERS_TCL at later fresh export; do not overlay active kits.

Actual R1 placement failed reset reach479.25um/680captures>405. A reviewed owned-copy correction moves only existing internal delivery FF rst_s[1] to a vacant legal site near its actual4324-load centroid, retaining rst_s[0] at E and the two-edge reset release. Actual corrected reach is353.75um/zero over405, with counts and pin metrics unchanged. Overall AUTO FAIL remains on aspect2.25, column estimate.64 and GRT NOT RUN. Parent's standing outline exception and conditional CTS-prototype review do not establish routed capacity, timing, SIGNED, adoption or token performance. R1's cell location is not portable to R2: R2 needs its own completed placed database, predecessor/load/row checks and LOOK. See results/geom_review/bksel_pipe_select_1131.

R1 then completed normal CTS (exit0 at14:45:31 PST,1498seconds/2275MB peak). Its actual4_cts geometry review is pending; pre-posthook tap insertion357ps/range343–390 and setup-repair WNS+48.983ps are diagnostics, not final released timing or binding qualification. Candidate clock binding remains TT250/FF202.5 with40ps tolerance. R2 has its own source-verified remaining-placement continuation; no R1 site is transplanted. Both original proof failures and all physical failures remain immutable. No GRT/DRT or adoption is claimed.
