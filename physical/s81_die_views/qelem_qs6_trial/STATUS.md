# QS6 Q-element structural trial

The actual current c7 Q-element uses `core_clk` at 833.333 ps. A source-matched replay of the retained CLOSED route `dsrom-qelem-qs5f-efs-7fb23b7ff-tc-hm10-cl` has SS internal setup slack -187.246658 ps and minimum period 1020.58 ps, with FF hold +12.042617 ps. This is a real same-clock internal path; the historical TT closure remains preserved.

The worst path launches at the registered match `g_hpk.g_k[0].u_w` and captures in the speculative need-walker next-state `g_qt_hit.g_hc[2].g_wrt.u_nr/q[2]`. Its cone selects logical state, decides end/restart, and computes the next MTP position before capturing the candidate. Other retained worst paths include the shared payload-enable fanout and FIFO-count → issue → word-table update.

The opt-in QS6 candidate addresses these three cones:

- register the need-walker restart decision and both normal/restart operands in parallel, then select the candidate after the edge;
- keep one equivalent registered enable for each 32 payload bits;
- register word-walker restart/advance decisions while their operand tables travel in parallel.

The register decisions and operands use exactly the original enabled edges. Defaults remain QS5 or below. No arithmetic ordering, port, period, uncertainty, or timing exception is changed. The die owner confirms the successor must preserve the retained 510.84 × 221.4 μm outline and exact 741 LEF pin rectangles. No larger slot is requested.

At source `0fddf8c8d`, the existing PQ0 reference gate passes four seeds plus sparse NaNs, totaling 12,775,002 compared cycles. Both the missing-MTP-restart and wrong-word-restart mutants produce explicit behavioral state divergence. An independent QS5 baseline on the same source has identical coverage, output sequence counts, and complete reported latency histograms in all five cases; the observed additional cycles are zero. Register-level assertions also compare the new decisions' logical candidates against the original expressions at every checked cycle.

This is component evidence. The fresh production PQ1 field bench, native throughput, SS/FF physical closure, clock-root admissibility, and actual new routed view remain open. The retained route has 53,105 clock sinks, TT root mean 506 ps and all-sink spread 96 ps (boundary mean 510 ps / spread 50 ps). Its historical CLOSED exception does not automatically apply to a new RTL candidate. A candidate must first measure compliant CTS or split into real hardened leaves with independent clock entries; no route is authorized by this document and no qualification is claimed.
