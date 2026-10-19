# SFU core k9s: schedule delta (HBM-SAFE-K9 2026-10-19, coordinator 0ks)

- WPIPE (split3 default 1): every operand-store bank write (VM stage sectors into operand groups 0-3, lane element
  writes into the output group) lands 1 clk edge later. Reads keep their edges.
- Compiler rule: write -> read of the same operand-store word needs >= 2 edges (was >= 1). Stage prefetch completes
  before arithmetic launch, and drains read the output group long after the last lane write, so the canonical
  Qswiglu programme meets it unchanged (lockstep vs ot_hgi_sfu_scheduled_engine: 0 mismatching edges of 6,679, no
  boundary output moved). Worst case for any programme: +1 edge on preload->launch and +1 on last write->drain =
  <= +2 edges per SFU invocation (~6,700 edges) = <= 0.03 % of SFU time; well under 0.1 % of the HBM token.
- GCLK (clk_st[4:0]): no cycle change (same die clock; flop-to-flop crossings).
- Reset landing: release +2 clk edges (static constant; the programme starts long after reset).
Owner of the SFU calendar: H-SU / SFU compiler (make_qswiglu_io_calendar.py needs no change for the canonical programme).
