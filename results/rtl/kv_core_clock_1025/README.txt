Owner decision14 core-clock implementation (optin), exactly833.000ps.

Select OT_KV_CONTROLLER_CORE=1 in KV static template/age/boot compiler.
Phase and landing leaves get SAME_CLOCK1. PC path parents get CORE_CLOCK1,
forwarded through fan/embedding/path/controller/scheduler/timing and calendar/
return-calendar. Regenerate SRAM clones with kv_pc_sram_gen.py, then regenerate
and reharden flattened group/PC cores. Existing _r2c netlists cannot inherit a
leaf-source change. Preserve the r2 fan/deskew wrapper, not just the base group.

The625/625 phase ticks are dimensionless. Both physical core/controller clocks
are833ps. Same-clock phase transport retains four registered edges; no reset-beat
origin or serial0.9GHz clock remains in this transport. Landing uses exact
same-clock integer edge arithmetic including XU626 (two625-tick steps).

Physical JEDEC minima round up from their1024ps source intervals. Refresh
maximum intervals round DOWN to EVEN row-slot periods (REFIPB144,REFI4680),
because each pseudo-channel owns alternate row slots. The naive145 interval
FAILed ref_fault at edge350; original failure is retained here. Counter widths
grow for RAS/WRR35,FAW19,WTR18. Raw latency23->29; write completion17->19;
registered command/return pipeline edges stay unchanged.

Compiler: K8on/3off,V8on/6off, ring64 unchanged. At833ps all128PC calendars
compile with512reads+4commands/PC, max sustained duty8/11=0.7272727 <=0.73.
Pair token period293376 unchanged. Full kv44 bundle compile/write PASS
(COMPILED_NOT_QUALIFIED), token busy290059, embedding margin1158cycles.
K reservation burst adds31wait cycles/256sectors vs8/2; V adds93 vs8/3.
These are charged in compiler leads, not an unreported new per-token delay.

Small component gates:
- Same-clock phase: lockstep70packets/all7masks, four-cycle latency PASS;
  early-stage and corrupted-metadata mutants FAIL.
- Landing: independent24cases, T1..8192 across3groups, exact edge+sector PASS;
  V-sector mutant FAIL256checks; K-order mutant FAIL112checks atT2048.
  K-order mutant atT8192 is vacuous (sector order alreadyascending), so useT2048.
- Actual native controller:36layers x512reads =18432landed, jitter0/8/16 PASS;
  independent PHY-pin physical tRCD/RP/RAS/RTP/CCDL/RRDS/RRDL/FAW/RFCpb checks.
- Default timing-core lockstep vs frozenbc751c01a reference: same36layers,
  jitters0/8/16 PASS alloutputs everycycle. Refresh-period mutant FAIL.
- Old timing constants at833 mutant FAIL tFAW13328ps <15360ps.

Reproduce controller: python3 tools/qwen_static_kv/run_controller_calendar_core.py OUT
  --legacy-miter / --legacy-miter --miter-mutant1 / --timing-mutant1
(add spaces before each1). Use ot-run for builds. Core sources/results staged at
intel2:/srv/opentallas-scratch2/claude/codex-kv-token-1025; phase/landing at
intel2:/srv/opentallas-scratch2/claude/codex-kv-token-core.

Still required: native kv45 rebind+recompile on its ages, native PC/group
regeneration and timing closure, boot/token/mutants. The record does not claim
SIGNED hardware or full-die token qualification. SRAM clone regeneration also
picks up the already-accepted B boot window from its canonical source.
