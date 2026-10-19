# PC / PC_H immutable terminal pickup

Both original gates are finished. PC is **WARN**, PC_H is **FAIL**. Neither tile is release qualified. No RTL, gate, CTS, route, REVIEW.json or submission was created by this collector. Original worktree and fleet route objects remain untouched.

The exact frozen shipping snapshot started at `0eed5271d3e716b89aa2fc6c21841cbd61b74f51`; this is an exact-content snapshot with daemon overlays, not a claim that every file equals that Git revision. Full per-file source/tool identity and archive hashes remain in each `gate_result.json`. PC manifest `338ea0f17b2a45cbb97ad5d5dca7352187cd5e7b01b522a49b89cff79f4cd602`; PC_H manifest `845d76f14c41a04a55668481f3a50bb119a26b81b665505218d504830e687317`.

| Fact | PC | PC_H |
|---|---:|---:|
| Terminal local time 2026-10-19 | 10:12:40 PDT | 09:57:23 PDT |
| Gate verdict | WARN, 0 fail / 7 warn | FAIL, 1 fail / 5 warn |
| GRT overflow | 0 | 0 |
| Worst routed layer utilization | M3 44.65% | M2 36.00% |
| Textbook cells / FF | 188622 / 41933 | 187867 / 41634 |
| Synthesized std area | 25529 um² | 25445 um² |
| Textbook utilization | 31.70% | 31.59% |
| Diagnostic TT placement setup | +88.325 ps | +107.341 ps |
| Diagnostic TT placement hold | **−4.323 ps** | **−17.616 ps** |
| Textbook estimated depth | **641.8 ps / 16 levels** | 590.1 ps / 14 levels |
| Textbook reach estimate | 211.4 um | 236.4 um |
| Raw external reset sinks, each port | 2 | 2 |

The setup/hold values above are the gate's TT placement-RC path-class diagnostic, not final routed TT/FF signoff. FF setup/hold, native launch <=220 / capture <=190 ps, electrical checks, DRC/antenna and parent compensation remain unqualified. The copied `physical.json` files were emitted during the initial floorplan-stop stage (before final CTS/GRT); their negative timings and `not_met` statuses are preserved as earlier-stage evidence, not silently treated as final metrics.

Each clock must be assessed separately. Numbers below are native boundary-flop measurements in the original gate; insertion is absolute pin-to-flop delay, not a parent-matched launch/capture proof.

| Tile / clock | TT boundary min..max / spread ps | FF boundary min..max / spread ps | Clock-spread result |
|---|---|---|---|
| PC core_clk | 373.9..427.3 / 53.4 | 306.0..356.5 / 50.5 | <=80 |
| PC hclk | 369.9..407.7 / 37.8 | 301.7..335.8 / 34.1 | <=80 |
| PC_H core_clk | 352.3..397.6 / 45.3 | 289.0..332.8 / 43.8 | <=80 |
| PC_H hclk | 369.7..450.8 / **81.1** | 301.6..377.6 / 76.0 | **TT FAIL** |

The gate headline uses hclk, and must not replace the separate core_clk measurements. Insertion >300 ps and 21520 hclk sinks alone are guidance, not a reason to split a tile. PC_H's TT boundary spread actually exceeds the 80 ps rule.

## Safe-design checklist and personal PNG inspection

1. **PARTIAL / OPEN:** raw rst_n and hrst_n each reach two landing FF; gate `reset_landing.ok=true`. Strap capture pc_sr/st_sr exists in the frozen source. Pin-register opt-outs explicitly retain pc__ki (depth 3), x__est__0_1 (depth 1), pc__fi (sticky fault); complete actual fixed-face FF ownership is **UNKNOWN**. Prior 5.050 source benches and causal mutants are described in copied specs; no new simulation was needed for terminal pickup.
2. **ESTIMATE ONLY:** old textbook reach 211.4/236.4 um and zero estimated violations; uncapped actual routed every-driver reach is **UNKNOWN**.
3. **FAIL:** preserved textbook metrics already expose FF QN roots with 2405 logical loads (`front.g_ra[8/4].u_rp.q[0]`), sched.tr[1] 2179, sched.hgo 1994 (1986 flop sinks), plus comb roots 2023/1801. These are a partial diagnostic list, not the required uncapped BUF/INV-transparent every-driver logical-pin census. Complete counts/roles remain **UNKNOWN**; absence of a gate high-fanout FAIL is not source safety.
4. **PC FAIL / PC_H ESTIMATE PASS:** PC 641.8 ps exceeds ~600; PC_H 590.1. in_to_out_bits=0, in_to_reg_levels=2, reg_to_out_levels=0 in the old textbook metrics. Exact actual mapped stage-depth proof is open.
5. **FAIL / source repair required:** textbook clock-root records include front.g_storage bank_mem FF groups totalling 9216 bits (2112+2400+2400+2304), with roots recorded under pc__front_hbm_data[0:3]. These exact records need source/native tracing; do not reinterpret them as ordinary ck/hck clocks. No SRAM macros exist in this gate. Storage mapping and architectural throughput must be resolved before a successor gate.
6. **PARTIAL / FAIL utilization:** personally viewed all four copied PNGs. Both outlines 267.84×300.24 um, aspect 1.121, no macros (43.2 lattice inapplicable); continuous full-core standard rows without islands. Full-face average pin densities PC N/S/E/W 5.776/4.155/4.583/2.082 per um, PC_H 5.776/0.127/4.583/2.082. Original pin geometry checked 4659/3580 signal+clock pins, zero inaccessible/outside/missing. Full-face averages do not prove local per-port spacing or FF face ownership. Actual ~32% utilization misses the 40–60% sizing rule; do not merely shrink a failed design.
7. **PC_H FAIL / PC INCOMPLETE:** clock positions are exactly east-face ck(267.798,10.956), hck(267.798,30.828) um, low on the east edge. Density images show most standard cells in the upper area and sparse bottom cells; clock beside the actual register mass is not demonstrated. A FF-only centroid audit is absent. Separate boundary spreads above, io_hold_margin=0.03; parent-native matching and release/reset phase not proven.
8. **UNCHANGED / OPEN ADOPTION:** this collector adds zero cycles and changes no schedule. Any source/storage/local-control redesign must preserve or explicitly price all static chain, boot, reset, completion and HBM ages. No credits/backpressure or masks are authorized.

## Fresh successor scope

Retain the original routes and all helpers/errors. Before any new physical gate, independently trace the actual mapped front storage clocks/data and every FF/comb/top-input/reset/macro/constant/clock driver through BUF/INV to logical pins, with no truncation or role-based omission. Enumerate each fixed boundary bit's exact FF identity before assigning physical faces. The observed 2405/2179/1994-load roots and >2 kb storage require structural source changes, with exact source equations/reset/initialization, production-shape correctness and causal mutant evidence, updated area/clock cost and cycle model. A tiny clock-location tweak or repeated hold repair cannot qualify this source.

`remote_objects.json` binds mapped Verilog, raw Verilog, original synth ODB and final GRT ODB hashes. Exact remote bases are on ot-epyc8:

- `/srv/opentallas-scratch/claude/ref_gate/qkd_kvs_pc_rl1-20261019-064619`
- `/srv/opentallas-scratch/claude/ref_gate/qkd_kvs_pc_h_rl1-20261019-064619`

Each source snapshot is under `src/`; mapped source and native ODBs are under `routes/gate/work/orfs/results/asap7/opentallas_qkd_kvs_{pc,pc_h}_asap7_ref_gate/base/`. `1_synth.odb` is suitable for independent mapped source extraction; `5_1_grt.odb` preserves actual terminal gate geometry. ROOT alone may merge evidence. No review approval or source/physical adoption is implied.

Rebuild the compact summary and evidence manifest using `python3 tools/qwen_kv_die/kv_pc_terminal_packet.py`. This is metadata bookkeeping only; no EDA is invoked.
