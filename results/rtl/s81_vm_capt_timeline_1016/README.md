# S-VM-CAPT-TIMELINE (claude, 2026-10-16): DECISION B capture data half vs the VM static capture lanes

Source: 6e71a3585 (codex/s81-hub-parents-0811; ctrl_c/dsfd_capt_x8_x43.sv), bench `tools/s81_vm/capt_timeline_bench.sh`,
stimuli `tools/s81_vm/capt_timeline_stim.py` (gen_stim cases with obase/ops 256-aligned = the capl ALIGNMENT CONTRACT;
`lock`/`lockmix` = every root starts on one stream cycle, one partial a cycle). Run: ot-agidock128, Verilator 5.032.

Bench: the unchanged capc_split runner (gather -> capture golden; reference capture = OLD row_local timing, split
candidate = NEW x8x timing) with the production VM capture face logic behind BOTH t_vm buses: dsfd_vm_static_cap_ctl
(flush from that side's own status lane) + 16 x dsfd_vm_static_cap_leaf PIPE 2 (CAP_PIPE 2, E 8).

Fault under test: capl flt[4] "two rows due" (two entries full on one serial edge, or a full row on a flush slot
drained+1+e of another entry) and flt[2] alias (entry key mod 8 held by a live row of another key).

| case | old faults | new faults | rows old/new | row seq ({row,mask,data}) | new - old edge | words lost |
|---|---|---|---|---|---|---|
| lock (compiled lockstep, I66 shape) | 0 | 0 | 484/484 | equal | -2..-1 | 0/0 |
| lockmix (6 phases, fmt 0-2, np 0/3) | 0 | 0 | 443/443 | equal | -2..0 | 0/0 |
| trace (I66 burst shape, roots start 0..8 apart) | 0 | 0 | 484/484 | equal | -2..-1 | 0/0 |
| rreq / err / over (fault cases) | status only | status only | equal | equal | -1 / - | equal |
| mix, mix11-13 (random per-root gaps 1..4) | alias 16 lanes, two-rows 7..16 lanes | alias 16, two-rows 11..16 | | differ | | thousands, both |

The mix cases are outside the static lane contract under BOTH timings (alias in every lane = root skew beyond the
compiled bound), so they do not qualify either timing; they are reported only as stress.
Write-bank same-edge collisions across lanes: identical old/new in every case (lockmix 16/16, pre-existing).
