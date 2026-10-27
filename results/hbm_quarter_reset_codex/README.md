# Native quarter delivered reset

This clean-source candidate adds opt-in DELIVERED_RESET=1 across the selected native quarter wrapper, quarter control, eight chunks, 64 HCOL instances (128 reset regions) and two tails. Default0 preserves the legacy mode and positional parameter order. The new helper rtl/lib/ot_rst_delivered3.sv uses three kept synchronous relay stages per region. There are no local2FF synchronizers in the selected mode. Keybuf/meta/fault have no local synchronizer to replace.

Release dates remain control3, chunk/tail6 and HCOL9 edges from the delivered reset. Each new local relay's assertion now takes3timededges. Existing direct reset consumers are retained; their input is the die-delivered synchronous net with normal timing, no local false paths. Boot/START must use actual delivered wavefront offsets and native readiness; this source packet does not invent a calendar. Data stages and key ages3/5/7/9(port),4/6/8/10(key_p) are unchanged.

The smallest reset-chain miter checks224edges across16reset phases, both preserved HCOL clock bits on the same833ps source, and tail/glue/control nesting; an early-release mutant is caught. No wholequarter arithmetic rerun or physical rebuild was performed.

The ordinary split recipe closures now include the helper without changing legacy parameters. recipes_delivered.json supplies explicit mode1 recipe overlays; the native HCOL caller setsmode1. Other direct tail/residual callers must use these explicit parameters and helper closure. Preserve physical register copies with the existing ot_keep_regs canonicalization hook, disable any unpriced generic reset landing for this already-landed source profile, then qualify actual anchors before placement.
