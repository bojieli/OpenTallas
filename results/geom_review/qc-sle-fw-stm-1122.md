# East FW and STM placement review

I viewed the original `run/layout_review/place/density.png` for both exact
E7 R6V2 attempt 2 kits. Both completed placement. The subsequent route
attempts were stopped by the owner's structural watchdog after severe global
routing congestion caused OpenROAD to drop the clock NDR. Their type blocks
are unchanged from V3 crt to V4 L2b.

- `sle_fw_v2__cl69f5e854`, AP `b808095e5b0b`. Density is concentrated in
  intermittent narrow columns and bands across the center and west. Round 5
  overflow was 26,779. The setup pair cited for an added station terminates
  the existing D3 landing-pad chain. Its exact final Q and capture are
  ~54.2 µm apart by Manhattan distance in the viewed placement. The scan has
  a separate 47-bit X_SC to SC_EO class with 926 µm mean and 936 µm maximum
  reach, and 581 X_CTL pad legs over reach with 537 µm maximum. The old
  attempt needs a changed layout before another manual route.
- `sle_stm_v1__clbe630b9c`, AP `67ee334b7417`. Density concentrates beside
  four north hard macros and along the narrow passage south of them. The
  exact scan finds 14 tap-0 reset legs to stream registers at up to 673 µm,
  and a separate 1,351 µm stream-to-fault-face leg. The bound gated
  `u_rrl_181` supplies `rst_n_t0` from parent `rst_rl_180` at depth 6.
  Preserve reset lineage in any localization change. The stale anchor on
  independently moved tap rows is a separate V4 intake issue.

The exact kits are below
`epyc7:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V2/items/`
at `TYPE/attempt_2/gen/TYPE`. The placed scans are in `TYPE/attempt_2/geom`.
