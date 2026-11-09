PRIVATE LEP vF calendar / compiler packet, 2026-11-08 takeover

Source candidate: intel2:/home/ubuntu/OpenTallas codex/head-lep-reserve-form-0222@41a81fe176.
Actual physical provider: intel1:/srv/opentallas-scratch2/claude/codex-head-lep-0222/kit/hd_lep0N_vF_reserve/rtl/ot_s81hd_lep0N.sv:820.
The noidx_core instance has CH_B1111, PAIR1, KTX0000, KRX1220, TXI1221, PIN2, POUT3, PLW3, COL0=2.
Its candidate source rtl/dsrom_sys/s81_head/ot_s81hd_lep0N_core.sv documents each explicit tuple/credit stage and forwards all these parameters through noidx_core.
Current selected wave source_plan.json hd_lep0N contents only declares CH_B/PAIR, so full parameter adoption is OPEN. The actual physical vF keeps collective0 pins on N; a historical N-to-W alternative is not required.

lep_calendar.py prices each explicit register leg and coherent tuple, including reverse credits. It requires caller-supplied absolute source dates. Default Stages() adds0; VF is opt-in. It does not invent FIFO residence, ROOT/X/START dates, reset release offsets or a whole-token period. Internal geometry/core-tap fix cb13e19342a adds0 functional cycles. Existing physical PIN_CYCLES are inherited from vE, not a new vF charge.

Scope of executable evidence:
- Current physical vF mapped LEC107757/107757 EQUIVALENT (HEAD lane); physical closure still open. Large initial CTS miss diagnosed as empty bracketed core taps; patched CTS resume running. No signoff claim in this packet.
- Historical actual plan_c0 small source programme uses vD+COL0=2: PASS, ri+11/+10, handoff idle margin1 vsreference3 (COORD queue 11-07/08). These are that programme's measured output dates, not all transactions' constant delta.
- Actual old token all-tail diagnostic and fixed static replay PASS1420ri/80lw and removed-reservation mutant CAUGHT. It uses STRESS KTX3333/KRX4444/TXI4444/PIN4/POUT4/PLW4/COL0=2. Frozen idle gaps106/118/217 and first/last ri+24/+142 therefore do NOT qualify vF's production schedule. require_matching_receipt rejects that transfer.
- Existing files: intel1:/srv/opentallas-scratch2/claude/codex-token-0222/lep/{drain_measure,static_replay,no_reservation_mutant}.log.
- check_calendar.py:25 explicit leg calendars, nibble order, zero-depth credits, two controls caught: importing stress reservations into vF, and blanket whole-transaction+3.

HEAD owner prepares the actual private plan event preserving actual bus faces/windows and adding exact source parameters, macro sites and station placement. This packet composes into that event; no POR change is made here. Remaining numerical gate is vF selected production programme with actual direction handoffs/tail drains plus compiler ROOT/X/START/epoch leases, under the exact vF stage tuple. Measure the minimum actual mechanism, then freeze its static source dates; no readiness-driven production issue.
