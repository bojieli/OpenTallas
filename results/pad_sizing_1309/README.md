No existing ASAP7 RVT single-input noninverting BUF/HB variant provides a characterized cell-propagation step <=15 ps at all observed head pin-register group loads. This rejects selecting a stronger buffer using a guessed small delay. It does not prove every total clock-network insertion delta exceeds 15 ps: a new input capacitance changes the upstream driver loading and slew, so any net-level candidate still needs paired actual clock-graph timing. No cells, physical graphs, kit inputs, or source constraints were changed.

The measured vehicle is the routed hd_turn_a A/B reference candidate claude/flowcan-cand2-1025@1ae8ebeb0, epyc1:/srv/opentallas-scratch2/claude/flow-canary/ab/runs/s81_head_1ae8ebeb0_1025_114536_038973/gen/hd_turn_a. The probe loads its actual 6_final ODB, SDC and extracted SPEF, using TT and FF RVT libraries in separate processes. All 35 ot_prp_d* buffer groups were measured with report_net and report_dcalc. The ot-run4GB/1thread job oth-ubuntu-3440641-1792959572 completed EXIT0. Two earlier read-only attempts used unsupported old OpenSTA command flags/names; their failed logs remain in the scratch directory and contributed no timing conclusion.

There are6..26 clock loads per group (median23). Total physical group cap is TT3.04..14.96 fF (median13.07), FF3.32..16.19 (median14.15). Measured pad-input slew is TT8.38..17.90 ps and FF6.43..14.34. Actual BUFx2 cell delay is TT23.55..45.23 ps and FF17.49..32.58. The NLDM parser reproduces each observed BUFx2 report_dcalc delay using its measured Ceff to within0.012 ps (report values are rounded).

The following cell-only sensitivity holds the measured input slew and total physical net capacitance fixed. A replacement cell can alter both slew and effective capacitance. Every out-of-table point is flagged in analysis.json and cannot qualify a conservative choice.

| Cell | TT delay range ps | FF delay range ps | In-table edges TT / FF |
|---|---:|---:|---:|
| BUFx2 |23.62..46.22|17.60..33.83|70/70,70/70|
| BUFx6f |17.62..25.63|13.28..19.02|70/70,70/70|
| BUFx12f |16.78..21.99|12.77..16.41|66/70,66/70|
| BUFx24 |23.49..28.51|17.99..20.93|0/70,0/70|

All16 noninverting INVBUF choices (12BUF +4HB) are in buffers.csv. The hold buffers are slower: HB1xp67 TT33.82..104.10/FF25.17..75.11ps, up to HB4xp67 TT69.87..142.83/FF51.56..104.95ps; all measured points are in-table. Rising-only edges also fail the15ps TT requirement. BUFx24 is not a safe low-load substitute: its characterized output-load minimum is23.04 fF, above every observed group load. The fastest fully characterized candidate is BUFx6f and it still exceeds15ps at TT. Larger cells also increase upstream input capacitance (for example BUFx12f TT input cap~2.34fF versus BUFx2~0.534fF), which must be included in any future graph timing.

For fine granularity, design the local tree/tap placement and branch wire geometry before routing, then measure the actual group insertion delta at TT/FF on GRT/RCX. A serial standard-cell pad is too coarse to be assigned a fixed <=15ps step at these operating points. Do not relax the20ps local balance target or the release timing policy.

analysis.json contains actual group loads, slews, per-polarity observed delays, candidate table lookups and explicit extrapolation flags. The analysis reuses tools/qwen_embedding_pad_nldm.py for the existing Liberty parser/interpolator; source library hashes are recorded, and the libraries remain in the scratch input directory.


Paired actual-clock-graph sensitivity (second experiment): the same35 existing BUF2 pad instances were replaced in an isolated in-memory copy by BUFx6f, then BUFx12f. Connectivity and extracted wires stayed fixed; each sizing step rereads the same SPEF. Canonical clock_family.tcl measures the same frozen register-pin groups at TT/FF. No ODB/netlist/route was saved or modified in the production kit. A replacement Liberty model changes pin capacitance and upstream loading; changed physical pin coordinates, legal cell widths and a fresh route/RCX are not represented. This is a sizing sensitivity only.

| Replacement | Group-mean change from existingBUF2, TT ps | FF ps | Weighted TT / FF change ps |
|---|---:|---:|---:|
| BUFx6f |-20.77..-5.62|-14.69..-3.96|-17.96 / -12.68|
| BUFx12f |-24.61..-5.82|-17.10..-3.92|-21.18 / -14.67|

The actual existing35 group means span49.83psTT/42.89psFF. Uniform6f replacements still span41.42/40.49ps;12f spans41.94/40.81ps, so neither meets the20ps local group-balance goal. The graph was rendered and viewed first (graph.png); its actual pad nodes lie on the left boundary band and lower diagonal sink band. Existing empty upper space and diagonal placement are inherited reference geometry, not a new floorplan approval.

A valid no-pad TOTAL inserted-stage delta was NOT RUN: removing a pad merges two extracted nets and invalidates the saved SPEF topology. There is no matched pre-pad GRT/RCX graph in the reference checkpoints. Therefore neither the cell-only lookup nor the paired strength change is a certified <=15ps inserted-stage quantum. A future opt-in method needs actual before/after graph timing, explicit group spread/max limits, FF internal-to-output hold checks and new physical legality/RC validation before adoption.

The paired job oth-ubuntu-623248-1792960296 completed EXIT0 through ot-run4GB/1thread. whatif_analysis.json and per-group TSVs retain all baseline/candidate values. canonical_clock_family.tcl is the exact parent-provided getter copy used in this experiment.
