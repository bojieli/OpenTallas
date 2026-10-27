# QC R26 clock recovery

Codex recovered the paused R26 opt-in implementation from the R25 branch on 2026-10-27. The A0 form is selected only by `--a0-mesh`; existing default clock plans stay on the previous path.

The recovery fixes a concrete band-path indexing bug: multiple row-band trees fed by the same column tree were indexed by column identity, so later rows replaced earlier paths. Each band tree now retains its own paths. Legal geometry now includes band buffers and repeaters, shares the actual upstream anchor cell, and uses their physical pin-to-pin nets in timing. The speculative `drive` sizing mode cannot claim legal geometry; the approved `adjcol` sizing is the default for the opt-in A0 form.

`test_qc_clk_r26.py` and the existing `test_qc_clk_mesh3.py`: **14 passed**. This checks path identity, actual shared upstream cells and physical edges, plus segmented mesh crossing continuity and disconnected-tap rejection.

The inherited four-level anchor search is an **analytic feed FAIL**, not a route-ready clock: 884 equal-level band trees / 3,620 leaves, maximum feed residual TT 111.513 ps / FF 122.043 ps. No modeled node is inside a core keepout. A uniform 16w search up to eight ancestors still fails (TT maximum 131.987 ps). These are unreviewed diagnostic numbers; they do not qualify routed clock timing. No die freeze or sign-off is claimed.

The existing physical exporter emitted the top 16w tree only. A complete clock needs column trees, band trees, mesh segments, crossing vias, and the actual loads. Mixed per-edge NDR and heterogeneous tied groups must be handled by the physical builder before it can import the whole clock. The pending all-stage exporter exposes those limitations explicitly.

Data on intel2: `/srv/opentallas-scratch2/claude/codex-qc-clock-1027/`. The inherited R25 top-tree DRC continues in `/srv/opentallas-scratch2/claude/qc-mesh-r25/drc/`; its scope does not include the complete fine mesh.
