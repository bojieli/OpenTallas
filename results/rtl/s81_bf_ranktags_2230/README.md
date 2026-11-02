# Disabled actual H10 nonzero-row BF label witness

Actual current CAP-safe u_f_0L01 phase110 owns WOA rows6..11 but its unmodified
CFG return labels are0..5. The existing FP rank-image tool explicitly skips
BF phases. This experiment shows that the native selected BF path can
transport the exact source-owned labels without changing any payload, date,
programme descriptor, other CFG bit or RTL cycle. It does not establish the
production collector's namespace or source/capture lifetime contract.

The initial join requires byte-identical current phase metadata and all33
actual BF weight/CFG images against the retained source vector. Those joins
pass. The experiment reuses the existing measured H10 native static binary,
selects the actual phase110 input vector, installs the existing measured
OFF4 descriptor with this phase's real ROM base, then runs three cases:

- Baseline: six actual outputs, local labels0..5, faults0.
- Disabled image overlay: labels6..11, exact same six dates and payloads,
  faults0. All non-row CFG planes (including the upper24 descriptor planes)
  are preserved. The native returns match the independently transformed
  baseline words bit for bit, with only the declared14-bit row identity
  changed.
- Wrong-first-label control: leaves local0 instead of6. The native path
  still runs; the exact ownership oracle rejects its output.

Epyc2 ot-run unit2415638-1793599875 passed exit0. Actual dates are
412,415,424,427,428,436; there are no added clocks or stages. The selected
source scope remains the retained BF-active/Q-idle experiment with explicit
GB_PROVIDER_UNDER_TEST=1 and Q_CPR=1. The native provider is not qualified.
No RTL, production remapper, canonical image, manifest, active ROM directory,
cohort or model default is changed. The candidate helper writes only a fresh
one-phase overlay and refuses an identity-map phase.

The observed source namespace uses actual row_index/tie values from the
same field. Extending this to all phases/frames requires the production
collector's chosen namespace, real source epochs/activation residency, BF
partial/fold/capture rules and reset/profile correspondence. These are held;
this result is not whole-mission or token closure. The helper currently
admits only the actual WOA rank-zero field experiment where row_index and
fixture tie output IDs coincide. Router/other ranks are not generalized.

Exact source, binary hash, output words, mutation and image-change records
are retained in native_receipt.json. Full original logs/images remain at
`epyc2:/srv/opentallas-scratch2/claude/codex-ds-bf-ranktags-2230`.
