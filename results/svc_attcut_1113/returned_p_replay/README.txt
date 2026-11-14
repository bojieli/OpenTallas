Returned real feedback P frame→actual outer/native replay PASS

Uses the numerically qualified4b3430fb52 compiled model, with no native RTL
rebuild. Original archive is preserved and checksum-checked. A private archive
copy weakens only the compiled SV testbench main/stimulus-entry symbols; their
machine text remains byte-identical. A small external C++ testbench replaces
that one timed stimulus coroutine (exactly1interposition required), retains
the original clock and all UUT machine code, and drives only TB reset/q_v/q_d.
No UUT state or memory backdoors. Original SV numerical fixture verdict is not
used; independent C++ checks apply to the new returned-frame programme.

Fresh decoded CFG/WIN/SEL/ROWS/Q/GO programme uses the same Q/K/V data as the
real-score source. Runtime WINtag1 matches the staged P packet's tag1; tag
identity is not claimed because the cached tag output is unobservable.
Actual GOcycle402, pre-edgephase1, PO800/PVO1024 are declared late test dates.
All256FP32 freshSCORE fields plus row/mask/flags and every dateGO+77..84 exactly
match the trace consumed by the staged SX/SM/P proof aa7281b932. Actual outer
accepts the generated P header atGO+725 and all8 bodywordsGO+726,728,..740
(pw8). Native Ploader consumes4 pairs atGO+801,803,805,807; pr8.

Independent exact oracle: staged head0 e coefficients are32 exactBF16 ones,
otherheads0; V is one in all32rows/dimensions. RawP.V is therefore head0=32
(FP32 42000000) in every dimension, otherheads0, flags0. All256rawP.V fields
across8beats pass, atGO+892..899. Done1, productionfc0, actualfault0 across
allfour H8 expanders. Live drain controller produces40slots (8header/32body),
indexsequence1,2,3,4,0 atGO+1026..1065. Original archive SHA remains unchanged.
E7unit oth-ubuntu-2708886-1794615981 exit0.

Scope correction retained: firsthelper FAIL42 (unit2645992) read cached tagj
and pv_od outputs left unconnected by the original SV testbench. Generated
C++ has only their random-reset declarations, no assignments: those bits are
not observable in this cache. The failure was1tagcheck+40payloadchecks+final
countpredicate; freshSCORE/P.V and frame acceptance already passed. Exact
failed helper/log/archive receipt are under first_checker_fail/. Final helper
checks live p_i drain scheduling only and explicitly EXCLUDES tag identity and
drained payload contents. Decoder/drain RTL source was not changed, but source
identity does not substitute for an observable output proof.

This closes the selected head0 staged arithmetic/transport partition. It does
NOT establish global minimum PIO/PVO, allhead feedback, SO normalization,
host/tree packet delivery, epoch fencing, drained payload exactness or die G5.
Data producer/consumer are staged runs with actual score/payload equality.
Capsule epyc7 hard-s81-svc-1/returned_p_replay/{out_live,first_checker_fail};
large private/cache archives stay there, not in git. Source/hashes in receipt.
