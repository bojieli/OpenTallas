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
