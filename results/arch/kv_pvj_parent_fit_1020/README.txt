PVJOIN parent envelope model, actual GEN9d9q snapshot 75171867d, 2026-10-20.
MODEL ONLY: no new gate, route, leaf binding, cycle adoption, or release claim.
Actual case host is qkd_host_rt y26462.16, not SerDes y26846.91. Previous 283.23um
host-clearance projection used the SerDes position. Simple square expansion overlaps actual
host by101.52um plus seq,embgw,kvs_ctl and pvfin; fixed-face expansion fails more broadly.

Grown alternatives preserve all functional macro clearances in this placement model:
Square216 leaf redistribution (params packet a5a2d1a3b): block604.8square, pair1641.6x12700.8;
PVW x shifts outward-center -43.2, southbase56.16 unchanged, AHUB/PVFIN/northpair +691.2y;
northband(at or above oldEMBGW25205.04) +1382.4y; die13476.672x29814.48, +18.630151mm2.
Exact pair-envelope area delta4.344607mm2 is a subset, not total die area.
Fixedfaces216x280.8 leaf: block604.8x669.6, pair1641.6x13737.6, analogous diegrow3456, +46.575378mm2.
External PVfork/PVtap candidate anchors move outward43.2 and north by pairheight delta;
final group-specific anchor positions remain part of real route regeneration.
All moved functional frames: zero NEW hard overlaps and zero out-of-die frames both alternatives.
Original existing overlaps, if any, are reported separately by per-parent collision lists.

This is not a legal complete floorplan: square leaves243/377 existing relay obstacles under
PVW0/PVW1 plus41 under AHUB; fixedfaces336/336 plus0. Those stations must be replanned,
not deleted or masked. The nested PV pairs' entire relay placement must be regenerated too.
A leaf has zero added edges; parent ages remain UNQUALIFIED. Actual changed-pin per-bit
<=405um reach, every registered relay hop, static ages/calendars, reset windows and firstvalid
contracts must pass before any adoption. No zero-edge parent or scalar performance row is issued.

Immutable actual input copy and full staged model outputs retained:
ot-epyc6:/srv/opentallas-scratch/claude/codex-kv-parentfit-1020/{input,model4}; SHA256 in packet.
Original progressing GEN9 jobs and Claude worktrees were only read, never edited.
