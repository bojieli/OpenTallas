# Near-HBM attention for the verify block: lane sets and the causal in-block mask (replay)

This is step 2 of the Qwen3-8B ROM DSpark stream. It is NEW and DEFAULT-OFF. The parent engine (`rtl/hdc/nearhbm/ot_qwen_nearhbm_attn_stack.sv`, its bench and its records in `results/uarch/qwen_nearhbm_attn_rtl_20261003/`) is untouched.

## What was built

- `rtl/hdc/nearhbm/ot_qwen_nearhbm_attn_stack_vp.sv` is the successor stack. Every module carries a `_vp` suffix.
  - `VMASK = 0` (default) keeps the parent's behaviour. `TM` is then ignored.
  - `VMASK = 1` adds the causal in-block mask. The stack still iterates over `T`, the block's longest context. Position i sees only rows `t < TM = pos0 + i + 1`.
  - A masked row stays out of the score max. Its e is written as +0, so it adds +0 to Z and V x +0 = +0 to P.V. This is the golden's zero-padded tree at context TM.
  - The schedule depends only on T. Copies with different TM therefore run in lockstep on one K/V stream.
- `rtl/test/nearhbm/ot_qwen_nearhbm_attn_die_tb_vp.sv` is the bench top. It has VP lane sets, each with its own stacks, hub and links, its own q and its own TM.
  - Copy 0 drives the HBM, and every response is broadcast to all copies.
  - The request streams are compared every cycle. Any difference sets `fault[5]` (lockstep check).
- `rtl/test/nearhbm/tb_qwen_nearhbm_attn_vp.cpp` and `build_nearhbm_tb_vp.sh` are the harness and build script.
- `tools/qwen_nearhbm_attn_verify_ref.py` writes the block vectors. Position i's golden is `hdc_golden` attention at T_i, called through the parent reference's `golden_die`. It is asserted equal to the partitioned scheme at T_i.
- `tools/qwen_nearhbm_attn_vp_gate.py` builds the gate record. `tools/qwen_nearhbm_attn_vp_area.py` computes area and power.

## Exactness (`vp_gate.json`): PASS, 82/82 runs bit-exact, 0 faults

Each run checks 1,024 outputs per position.

| bench | cases | lane sets |
|---|---|---|
| HD 128, R = 1, host-float stand-ins | ctx0 1, 126, 510, 4095, 8189 (x4 kinds), p = 4 | VP 1 (each position), VP 2 (2 passes), VP 4 (1 pass) |
| HD 128, R = 8 and R = 6 | 8189 normal and peaky | VP 1, VP 2 (R = 8); VP 2 (R = 6) |
| HD 16, REAL RTL arithmetic units | 6 cases, p = 2 and 4 | VP 2 |

- The blocks cross the 128/512 stack and round boundaries, and include 8189..8192.
- **Negative control:** `negative_control_nomask_hd16_vp2.txt`, the same bench with `VMASK = 0`, mismatches in every case. A missing mask is caught.
- In `meta.json`, `unmasked_differs` shows that the unmasked golden differs for positions before the last.

## Cycles against the model (`pricing.json`: m_attn = 1 costs +1,512 per extra position; m_attn >= p costs +112)

These are measured at ctx 8,189-8,192, with the HBM at 750 B/cycle per stack and 16 cycles of latency.

| row engines per stack | p = 1 | p = 2, 1 lane set | p = 2, 2 lane sets | p = 4, 2 lane sets | p = 4, 4 lane sets |
|---|---|---|---|---|---|
| R = 8 | 1,824 | 3,648 (+1,824) | 1,824 (+0) | 3,648 (+608 per position) | (R = 1 only) |
| R = 6 (floorplan) | – | – | 2,022 | 4,044 | – |
| R = 1 | 8,728 | 17,456 | 8,728 (+0) | 17,456 | 8,728 (+0) |

- **One lane set** costs a whole pass per extra position: +1,824 at R = 8, against the model's 1,512. The pass is HBM-bound, because each position re-streams K/V.
- **Lane sets >= p** measure +0 to +8 cycles in this bench, against the model's +112.
  - The bench gives each copy its own q link and return link.
  - If the q and return links were shared, their serialisation would add the model's q 40 + return 72 per extra position.
  - The model's 112 is therefore the right figure for a shared-link design.
- At p = 4 with 2 lane sets, the block takes 2 passes.

## Area (`area_power_vp{2,4}.json`)

| basis | per extra lane set, row FIFO shared |
|---|---|
| floorplan r1 row-engine frames (24 x 0.656 mm2) + hub | **15.55 mm2** |
| pre-layout synthesised units | 11.42 mm2 |
| model | 14.7 mm2 |

- VP 4 adds 46.6 mm2 on the frame basis, or 34.3 mm2 on the unit basis.

## Power density

The limit is 2.0 W/mm2 nominal, from the IEEE EPS HIR Thermal chapter v0.9, as used in floorplan r2 at ced04cd96.

- **Peak:** each lane set sits in its own frames at the parent's lane density, so the in-phase peak stays at 3.92 W/mm2 in scenario A. That is a PDN load: tau is 1.22 ms, far longer than the phase.
- **Time-averaged:** at most the AR value of 0.92 W/mm2. Each lane set runs once per verify step, which is at least one AR token. This passes against both the 2.0 nominal and the 1.0 conservative limit.
- **Duty cap:** a sustained 100%-duty strip still needs the r2 duty governor (<= 0.483) or a MAC energy <= 1.92 pJ. VP does not change that bound.

## Replay

The host was ot-epyc1tb at `/srv/opentallas-scratch/claude/qwen-rom-dspark-attn`, from source 7e55cac85 (git archive). `epyc_chain/` holds the manifest, chain script, job list, STATUS and raw results (`res.tgz`).

```
NHB_HD=16 python3 tools/qwen_nearhbm_attn_verify_ref.py --ctx0 C --p P --seed S --kind K --out v16/C_P_K   # HD 16
python3 tools/qwen_nearhbm_attn_verify_ref.py --ctx0 C --p 4 --seed $((C*3+4)) --kind K --out v128/C_4_K   # HD 128
rtl/test/nearhbm/build_nearhbm_tb_vp.sh OUT HD R dpi|real VP [VMASK]
OUT/Vtb VECDIR FIRST 16 750 2000000
python3 tools/qwen_nearhbm_attn_vp_gate.py --res res --vectors-root . --source-commit 7e55cac85 --out vp_gate.json
python3 tools/qwen_nearhbm_attn_vp_area.py --vp 2 --out area_power_vp2.json
```

## Open items

- SS/FF closure of the successor in context. The mask adds one compare per score and per exp read. P&R has not been run, and the parent's row-engine P&R is itself stopped. Not adopted until it closes.
- A shared q/return link design, with its +112 per position measured.
- The row FIFO and request generator shared in RTL. The bench keeps per-copy copies in lockstep.
