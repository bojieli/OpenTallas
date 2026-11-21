# FAM-S81-SLICE handoff (11-20 23:5x PST)
Rep: slice_station__t36 (synth 215k cells). Held by die owner; J5 cannot sign (monitor pin 2057 um from seat); J6 monitor-home + FSTART rows cover it.
Blocked on: J6 gates C3c/C3d (epyc10 s81-j6 gate.sh, queued, no gates/ dir yet). Next: when s81-j6/candC3d/physical/die_plan/s81/plan_of_record/native_bind/out is rewritten by bind, copy p1_kit.sh (epyc9 fable-fix-s81-slicec) with T=slice_station__t36, SRC/BASE=candC3d, gen args per kit_wave gen_args, run under ot-run --priority plan to grt, read post-hook CTS (START broadcast was -244/-182 on t37/t51).
C slice types 430-530k cells: separate; propose no-growth split for J7 if c1x_C stalls (see FABLE-FIX-S81-SLICEC-0045.md classes A-D).
Successor needed: any Sonnet/Opus lane to continue.
