# Disabled HEAD kit-wave recipe

`head_wave_kit_rtl.py` stages the existing HEAD re-kit recipe for the script
interface in `tools/autopilot/kit_wave.py`. It does not change wave configuration,
enable a type, publish a queue row, or run placement or timing.

Use an immutable full source checkout with the actual plan's native sink-bin,
macro and body-RTL assets. A tools-only checkout is insufficient. Prepare one
snapshot from the exact enriched plan/sidecar and published source cohort:

```bash
python3 -I tools/s81_head/head_wave_kit_rtl.py prepare \
  --source /immutable/meta_legal88 \
  --published /immutable/src25legal88_native \
  --assets /immutable/source_assets \
  --out /new/immutable/prepared \
  --types hd_turn_a,hd_turn_b,hd_st_str
```

The preparation snapshots every declared native sink-bin payload and rewrites
only its file pointer to that immutable copy, so the global reset solver can
read the held profiles without relying on lane worktrees. Payload SHA checks
also run at export. It applies count-strap sites and private raw-export metadata once,
and copies relative pin/domain material and selected published wrappers. The
receipt records `enabled=false` and `release=false`. CTL variants and SerDes are
rejected: CTL still needs its explicit rsel/FSM profile, and SerDes needs its
parent PMA period/view disposition.

The staged script is `physical/die_plan/s81_head/kit_wave/kit_rtl.sh`, with normal
`TYPE`, `OUT`, and `PLAN` environment variables. `PLAN` must point at the prepared
snapshot. The exporter bootstraps the exact type with that snapshot's clock
landing sidecar, applies reset aliases, and compares all RTL tokens against the
published wrapper **before** adding the private same-D flops. Comments and
whitespace are ignored; attributes, names, widths, literals and every other
token remain significant. Drift fails closed and retains the unmatched wrapper.
The export then supplies the complete bootstrap `VERILOG_FILES` and defines to
the external GEN through `kit_rtl.f` and `kit_rtl.json`.
The exact partition wrapper is first in the list, as required by `--kit-rtl`;
all other files retain their bootstrap order and unchanged bytes.

An eventual reviewed wave configuration must use the same prepared plan and
`gen_args: ["--clock-landing", "/immutable/prepared/source_sidecar.json",
"--trial"]`. Existing `gen_phys.py` detects `--kit-rtl` plus clock landing and
uses declaration-only landing, avoiding a second RTL transformation. Do not
enable this configuration until the actual source gates and each actual GEN
geometry review pass. A successful RTL export is not a physical qualification.

Initial source staging diagnosed and resolved a missing dependency: the legal88 source plan
references `results/die_head_38_1030/hd_ctl_sink_bins.json`; the global reset solver
reads it even when only turn types are selected. That exact native asset must be
included in the immutable source closure. HEAD supplied the seven exact native
payloads in `source_assets`; preparation snapshots those bytes. No placeholder
or guessed bins are accepted.
