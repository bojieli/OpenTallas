# HBM next-event plan d49a_io_reform_1111 (DIE-HBM-100 / HBM-COMPOSE-2, 2026-11-11) DO_NOT_COUNT

Plan die_plan.json.gz (decompressed sha256 e9ae418c06ca08cbddb07d328746d63e5ffc25b85b8efe746eb39b1726abda57) = d48a_postcut2_1111 plan t19 (6391dea6a0b3) + deltas/io_reform_delta_on_t19.json.gz.
The delta is DIE-LAYOUT-HBM's NW_io/NE_io re-form (claude/die-layout-hbm-1111@1637f6ae938b, physical/die_plan/hbm/die_layout_1111/io_reform/, ladder_delta format; apply with its ladder_delta.py).
Serialization note: json.dumps(indent=1) with NO trailing newline gives e9ae418c06ca (the author's sha); ladder_delta.py apply appends a newline and gives 53f28c4f7338 for the same object.
Form: NW_io 648x1814.4, NE_io 648x1425.6, new transit-only NW_iorly 648x2505.6 at (0,7879.68) and NE_iorly 648x2894.4 at (27751.68,7490.88); L8008 +1 cycle (69 -> 70); L8007/L8006 unchanged; die stays tiled.
Gates (compose host epyc8, pure main src_hbm_main_fe0002fac6, same tool as the t19 baseline; main has since moved to 65ef7507d2):
- G0 check.py: t19 554 errors -> 554, 0 new (1 message renamed NW_io.N -> NW_iorly.N 12.70/um, su01-facing window), 0 pending-view.
- Strict bind two-pass R8 (script bind_t20io.sh = bind_t19.sh with the plan swapped): BIND_OK, 92 partitions, 420 crossings, n_errors 0, stale 0, uncovered 0, pad_flops 945867 (= t19). bind_SHA256SUMS.txt = bind_t20io/SHA256SUMS; table hbm_arch_B2o_r8_landing_t20io.json.gz.
- stscan t19 -> t20io: no new phantom / miss>405 / misattr (stscan_t20io.tsv); route_supply: no WORSE row vs t19; classify_vs_t19.json: only NW_io, NE_io changed + NW_iorly, NE_iorly added.
- L8008 is in no latency contract (hbm_lat_contract.json and bind_latency_consumers.json name no L8006/7/8) and no token path; only consumer is ot_hbm_host_cp_rxs RXLAT (configuration path, default 101, not wired from the plan).
Kits: re-kit NW_io, NE_io; new pure-FT kits NW_iorly (~8.9k station flops) and NE_iorly (39 flops).
