# dsdv_sh_lk_s10f: s10e + pin-access SRAM abstracts (parallel fallback; S81-SHLK12 2026-10-20)

Same RTL, floorplan and benches as s10e (below). The six SRAM masters use the `_pa` views: VDD/VSS M4 straps and the M4 OBS pulled back from both pin faces (1.5 / 1.0 um), the geometry of the s10c/s10d M4 strap-end shorts.

---


Why: both s10c (1b3fedddc) and s10d (87bd096d8) routes ended terminal FAIL with DRC 2 (M4 signal/VSS + macro-OBS
shorts at the right-face pins of SRAM `u_hx.g_rsz2.u_mem1`), and the mapped native census of their source had 264 / 323
roots above 32 load pins (max 597 / 526: realigner write decode, dispatch / stream-step cones, address-stage enables,
queue decodes, CSR decode, reset copies).  One failed route = structural redesign: s10e rebuilds every such structure.

## What changed (`OT_S81_SH_S10E`; shared files keep their s10d behaviour)

| block | s10e structure |
|---|---|
| stream engine | `rtl/hdc/ingest/ot_s81_ing_stream_n32.sv`: realigner ring (2 kb) in two `ot_sram_1r1w2c_16x257` (even / odd words; the registered macro output is the old stage-P window); 10 kept clone domains for the stream control (each domain's go / pop / steps from its own leaf clones, D = the master's next state); write-behind descriptor queue with registered bypass; registered dispatch family; 12-b address-stage / queue slices with per-slice enable clones; one-hot select clones (window, kind, ldie / lns); 16-b output-FIFO slices; completion queue with registered per-slice write enables and one-hot read copies |
| host wrapper | `ot_rom_host_ingest_n32.sv` (+ `dsfd_host_n32`, `dsfd_host_native_n32`): three hx_pop replicas from kept clones, request-room / marker / completion-word clones, 16-b die-face slices, 128 / 32 / 16 reset copies (`ot_reset_sync` TREE) |
| FIFOs / fence | `ot_dsdv_afifo_n32` (completion FIFO, write-behind, one-hot read copies), `ot_dsdv_host_afifo_sram` HNR 2 (have_next replica), `ot_s81_fence_n32` (write-behind queue, pop / handshake replicas, own reset copies) |
| lk leaf / sd | CSR decode from 19 kept clones of the 11 decode pin-flop bits; 32 relay copies; `dsdv_sh_sd` 20 payload copies (15-b slices) |

Pre-gate native census (gate 4, ep7 `ref_gate/dsdv_sh_lk_s10e-20261020-033526`): **PASS, 42.6k roots, max 32**
(iterations: 323 / 526 -> 65 / 88 -> 7 / 52 -> 1 / 55 -> 0 / 32).

Equivalence: `rtl/hdc/ingest/test/run_n32_lockstep.sh` (engine vs ot_hdc_kv_ingest, every output every edge, random
RAW / ROWS / IKEY incl. 16-b row / left carries and back-pressure): 12 seeds PASS, mutants BYP / GOD / WIN / KIND / FQS /
CQR FAIL; seqhost bench (golden dsfd_host_c + issuer, HSH 8 unchanged) PASS, unit mutants detected.

## SAFE-DESIGN checklist

| # | Item | Status |
|---|------|--------|
| 1 | Pins | PASS (source-registered; reset lands in 2 stages, 8 rst_n copies). |
| 2 | Reach | Outline 345.6 x 280.8: corner-to-corner Manhattan 626 um > 405.  Clones are placed by their loads; the CTS gate's placement-RC STA and the native placed census qualify reach. OPEN until the gate reports. |
| 3 | Fanout | FIXED: mapped census max 32 (all roots, reset nets included). |
| 4 | Depth | Expected <= s10d (570 ps): new cones are the SRAM -> window (8-way AND-OR) -> 8:1 byte select -> kind select -> FIFO write. Gate textbook decides. |
| 5 | Storage | FIXED: the 2048-b realigner moved to SRAM; remaining flop queues <= 4 x 228 / 8 x 64 / 4 x 288 (each < 2 kb). |
| 6 | Floorplan | Macros on the 43.2 lattice, 3 rows x 2 columns, 74-83-um column channel, 42-47-um row channels, halo 10.8 (was 5.4) on every macro. RISK: the 16x257 / 16x289 masters carry ~10 pins/um on their 39-44-um side faces (> 6/um) and every 4th pin is collinear with an M4 PG strap ending 0.276 um from the edge (the s10c/s10d short geometry); a pin-access LEF variant (straps / OBS pulled back from the pin faces) is the parallel fallback. |
| 7 | Clock | One ck root, io_hold_margin 0.03, gate must show spread <= 80 TT+FF. |
| 8 | Schedule | PASS: no edge added (lockstep and seqhost HSH 8 unchanged); the fence comes out of reset 2 edges after rn (idle then). |
