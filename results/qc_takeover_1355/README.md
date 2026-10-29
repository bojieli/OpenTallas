# QC collection and native PROG contract diagnosis, 2026-10-29 13:55 PDT

## PROG physical record is already fixed; native binding is a different open item

`claude/die-qc-36-kits-1029@4513968c1` completed the coordinator's requested freeze-record correction at13:27.
The actual intel2 `die-qc-34-kits/prog/kit_ffh10r/freeze.json` now has `rtl_signed` naming main66b68bff2,
MIF=1, the three exact SRAM blackboxes, actual routed netlistc273e187 and routed LEC34f4dfc4. Original spec/source
fields remain explicitly superseded with the original backup. No physical/LEC rerun is needed for that correction.
Physical result remains SIGNED: TT+232.16/FF+6.67,pair79.2/71.5,DRC0/slew0/PG0; routed LEC7221/7221.

However, the actual current native functional bind is MIF=0. Read-only inspection of
epyc2 `/srv/opentallas-scratch2/claude/die-qc33-bind/elab/asbuilt.json` by the import lane found:

- parent `$paramod\\qfd_dv_s8_vm8q_rp1\\MIF=...0`;
- its `u_pg` cell is `qfd_dv_s8x_prog`, `parameters.MIF = 00000000000000000000000000000000`;
- module `qfd_dv_s8x_prog.parameter_default_values.MIF = 0`.

The independently checked strict-bind recipe23ef9f36b1 has no MIF override. Main RTL likewise instantiates
`qfd_dv_s8x_prog u_pg` without an override. The RTL contract explicitly says MIF1 adds one programme read and
table-write edge relative to MIF0. Therefore the valid physical MIF1 view cannot silently replace the current
native MIF0 block. This is an existing source/timing contract issue, not an added gate. Keep the signed view typed
MIF1 and the native integration open. The earlier exact source/compiler MIF1 candidate c9cdec9e23 exists but was
default-off/unadopted. Root and Qwen source owners were informed; owner question is in CODEX-LOG.

## Inherited jobs and other QC lanes

BTAB A/B are already running; no duplicate job was launched. Both are on intel1 under
`/srv/opentallas-scratch2/claude/die-qc-36-kits/kits/qfd_dv_s8x_btab_f3bv1c_{a,b}`.
A unit294553-1793306489 is in GRT FF hold repair (last measured+6.76 before margin repair).
B try2 unit331227-1793306720 is in detailed route (~64markers at guide iteration5). Try1's EST-0104 was fixed by
moving repeaters before GRT; its failed output is retained. B/A source commits e339f3887+d5497db17 remain READY.
V1d reference is terminal NOT SIGNED (16DRC,12/2slew); V1c remains the prior best (6DRC,11/2slew).

A0 child owns a fresh exact452603b6fbb worktree. All old A0 runs are terminal FAIL; no duplicate CTS is running.
Current planned-tree failure comes from the single t7 node's tile-wide fanout; the same T11 form also feeds ten
ROM branches directly from the root with ~550um leaves. A shared four-way spread/T15 candidate is being prepared;
no CTS until rendered geometry passes. Existing graph-home placement/proof success is retained.

Import child owns current exact6ea044ed3cb7. Inherited backbone unit2823927 is live on intel2
`/srv/opentallas-scratch2/claude/die-qc36/backbone_bb1`, with existing continuation scripts untouched.
At~85k endpoints,84645passed/356failed (partial, not a final verdict). Prior mixed PG materialization/grid continuity
and strict bind were already checked; no replay was launched. Actual backbone/clock closure remains open.

Old QC-KITS, SU, mesh and PATH notes are covered by these current successors; broad type routes still await the
coherent current die event. No old failed physical wave was relaunched. No new SIGNED or freeze claim is made here.
