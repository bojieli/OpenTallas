# S81 SERDES current pickup, 2026-10-19

**FAIL at PDN, before CTS.** Source `247c97136`, kit `s81lk_serdes_col_lp`, lpk2,
remote `ot-epyc5:/srv/opentallas-scratch/claude/ref_gate/s81lk_serdes_col_lp-20261019-122601`.
The actual 12:29 terminal error is `PDN-0006 VDD on M4 is blocked by obstructions on M5 for u_prx`.
The request's `--cts` never reached CTS; no routed timing, final ODB or layout PNG exists.
The immutable shipping archive SHA256 is `7ccf1a7f50b92b138a1c7b9687e57477c5315c4ae6b8f8d891d9a3533355f7cf`.
`textbook_execution RC=[]` is a second unresolved evidence-scope error; this packet does not alter helpers.

The latest fleet lockstep run (`oth-ubuntu-2128867-1792438012`, Verilator 5.050)
compares 8,880 outputs over 3,000 cycles: MUT0 PASS, MUT1/2/4 each FAIL with 2,960 mismatches.
MUT4 now targets `u_enc`. Earlier MUT4 at `u_live_t` was unobservable and PASS;
`bench2.launch.log` preserves that unsuccessful witness alongside corrected `bench3.launch.log`.
MUT3's six-stage encoder-fault status pad is still unobservable in this continuous-valid traffic;
its waiver is narrow historical scope, not proof of status timing or fault propagation.
Source-pinned mode0/1/2 two-die 300-ppm link logs already record 6,000/6,000 PASS each.
Neither bench establishes final physical closure or a production SU/MU token calendar.

`model.py` reproduces the root cause from both source LEFs: each PMA has 935 VDD and
934 VSS M4 rectangles, all completely covered by its M5 obstruction. Thus all 3,738
PMA supply rectangles lack the required parent M4-M5 via access, including TX, which
the first RX failure prevented the gate from reaching.

`stage_terminals.tcl/log` uses the original native `2_3_floorplan_tapcell.odb` with
OpenROAD 26Q3-1510, the gate's pinned image, through unpinned ot-run fleet unit
`oth-ubuntu-2230771-1792443216`. It enumerates all seven hard instances and all 14
PG ITerms. Digital-child M5 VDD/VSS rectangles per net are chn40, dly44, enc40,
out46, syn40; the two PMAs use M4 935/934 each. All ITerm nets are NONE in this
pre-PDN stage, before generated `global_connect`. The intended domain in generated
PDN is CORE: VDD power and VSS ground. This audit deliberately makes no final
terminal-connectivity claim. The initial diagnostic invocation used a nonexistent
PATH executable and exited127; the corrected absolute binary exited0.

The bounded structural option in `model.json` preserves all old M4 supply terminals,
signal pins, outline and logical edges. It reserves actual same-net M5 supply stems,
retains the remaining M5 obstruction, and exports supply on M6 for parent M6-M7
connection. Every old supply rectangle receives an internal via45/via56 connection;
the .288-um enclosure box is a design budget requiring exact native-rule validation.
This would reserve two .432-um internal corridors and M6 wiring, with zero extra FF
or data cycles if feasible. Internal analog reservation, RC, current capacity and
native via/spacing geometry remain unproved. No source, LEF, Liberty, PG generator,
helper or gate was changed. Root must select the complete model before implementation.

Whole-parent obligations remain explicit: all native nonclock roots<=32; actual
registered pins and <=405-um single-edge wires; all macro/register clock pins and
neighbor timing at TT/FF; terminal-level PG connectivity; physical escape and
capacity; the real 4096-bit indexed gray FIFO's SRAM/lifetime implementation; and
encoder-fault status coverage. README assertions of construction or storage waivers
are not measurements. Synthesis reports 19,514 FF; LP record separately prices
12,734 landing +9 pad +49 reset +514 output FF. Existing compiler offsets are TX+3,
RX/status+7 and reset release+5; installation into the actual parent/token calendar
is still open. Preserve distinct core/recovered clocks and the actual gray FIFO CDC.

Next owner: LEAD-S81, root structural-model choice first; source/view implementation
and fresh checklist/PNG review follow only after model selection. No gate is live here.
