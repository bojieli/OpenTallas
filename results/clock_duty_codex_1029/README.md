Clock duty reporter correction, 2026-10-29
=========================================

Inherited die-s81-18/stage/in/duty_eval.py applied BUFx24 scale to every
clock, causing four false duty failures on an inverter tree. The new helper
imports die_sta_related's ONE shared calibration and requires the clock-cell
declaration. inv2 normalizes to the inverter master. Mixed paths require
measured per-master components and use the shared source/local-edge-aware
component calibration; no inverter or buffer fallback is allowed.

OT_EDGES v1 F rows contain fall late/early. Legacy F rows contain fall late,
rise late, and slew; unversioned input requires explicit --format legacy,
and its copied rise value must agree with the T row. Missing measured edges,
duplicate rows, nonfinite values, and absent measured slew fail closed.

Example:

    python tools/clk/ot_clk.py duty ARR_TT ARR_FF OUT.json --clock-cell inv2

The report retains the inherited nominal late-fall minus late-rise pulse
definition and conservative TT DFFHQNx1 minimum-pulse table. This is a phase
report, not an OCV pulse bound or a die freeze gate. TT/FF only; period833ps.

Actual retained reach17 input (no STA or route repeated):
epyc2:/srv/opentallas-scratch2/claude/codex-s81-2340/reach17/out_{TT,FF}/arr_{TT,FF}.txt
mirrored locally under /srv/opentallas-scratch/claude/codex-s81-2340/reach17.
Committed s81_reach17_shared.json: 8501 taps per corner, TT46.3976..51.9152%,
FF46.4072..54.5655%, zero duty or MPW failures, matching independent S81/NUMBER.
Historical hardcoded-BUF failure retained by S81 owner. Original route was1x;
the shared SPICE model's conditions remain separate from actual route NDR.

Validation: test_clock_duty.py plus test_ot_clk.py,43focusedPASS. Controls
exercise the original wrong-cell failure, both formats, mixed parity-aware
components and a decomposition mutant. Default build/replay paths unchanged.
