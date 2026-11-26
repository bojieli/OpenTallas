# KV G6 static, IO, PC and PV source review

The bounded G6 seed is private. Live G5 is `KV-A5t9-r8-g5-1126` with plan `87d01254579e5c18ef6ca10490b743694b0ec75c46b6193cf43a4d2bdc6ec3bf`. The candidate plan is `1daab8832a53da8993708ded70051a8d99d399000deef2e9b5186bbca1c1201c` under Intel2 `/srv/opentallas-scratch2/claude/kv-allfix/pub/kv_a5t9_r8_g6_static_io_pc_pv_private_1126/physical/die_plan/qwen_kvsys/plan_of_record/plan_a5t9_g6_static_io_pc_pv_1126.json`. The source seal is `a4a57eed0c5dd34af255c204f3911f8e45a89aae3612869ed38aa0a1c4fb2672`.

| Types | Source changes |
| --- | --- |
| `kv3_io_cor`, `kv3_io_ft`, `kv3_io_ft_v1` | Apply 18, 12 and 11 qualified parent-tied strap positions, respectively. |
| Six PC variants | Apply 366 qualified count-strap positions. The two PCV1 variants also move the west FT0 and east DN first-bank seats within their existing stages. |
| `kv3_pv_v4`, `kv3_pv_v5ne` | Replace 7 and 441 station positions that G5’s physical scan placed inside hard macro bodies. The separate exact two-type check brought those 448 intersections to zero. |
| `kv3_pv_v2`, `kv3_pv_v6` | Carry forward the qualified footprint-matched native sink bins, collector wiring and tap offsets at the same stage depth. |
| `kv3_sys_c` | Apply 62 physical strap positions and four single-register KVN placement fences. |

The candidate retains all top-level partitions, ports, lanes and latency records byte-for-byte. Component receipts and exact change guards are under Intel2 `/srv/opentallas-scratch2/claude/kv-allfix/a5t9/r8_g5_ship_1126/clean_scope_composed/composed_receipt.json`.

I opened all 14 stock plan renders and all three exact geometry change plots under that same directory, in `render/` and `changed_render/`. The affected IO straps, PV relay and tap seats, and SYS_C fences were visible in the detail plots. Stock PCV1 views still show long inherited legs across the macro stripes. All four PV stock views show projected corridor pressure from 2.84 to 5.99, and SYS_C shows 3.29 across the upper band. The four plain PC models do not estimate bus heat. These are plan views. The existing route holds remain in force, including the Hub, parity, RESET seam and unproven token packages.

The reviewed source packet passed the E8 scoped gate in unit `oth-ubuntu-2974338-1795691654`. Strict binding emitted all 14 requested types and recorded zero errors. Bound PRE found zero failures and 253 advisories. The generator dry run passed all 14 bound RTL kits. All 2,908 data crossing ages, 2,567 landing-pad records and the full bus group file match G5. The PV v2 and v6 reset trees change tap assignments but preserve reset depth 10, one entry stage and release age 11. Gate outputs are under the same scratch2 path on E8 in `bind/`, `pre.json`, `pre.log` and `scoped_gate.r2.otrun.log`. G6 remains private and no placement or route job was started.
