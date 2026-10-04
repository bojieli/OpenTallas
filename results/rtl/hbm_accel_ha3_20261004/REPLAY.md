# HA3: cut-through collective and fused receive-path epilogue on the HBM accelerator's SM -> collective endpoint

Branch `claude/hbm-ha3-collective-epilogue-20261004`. All hardware is new and default-off; `ot_gpu_simt_sm`,
`ot_gpu_coll_mux`, `ot_gpu_coll_endpoint`, `ot_gpu_hbm_system`, the system bench, `qwen_hbm.py` and `v41_hbm.py`
are byte-identical.

## What was built
- `rtl/hbm_accel/collective/ot_hbm_accel_simt_sm.sv`: SM successor. `HA3 = 0` behaves as `ot_gpu_simt_sm`
  (the HA3=0 Qwen system run reproduces the original record, 1,759,405 cycles).
  `HA3 = 1` adds two instructions:
  - `COLLX`: every SM contributes its lanes from a register and receives the whole result.
  - `COLLSS`: reads the fused sum of squares.
- `rtl/hbm_accel/collective/ot_hbm_accel_coll_port.sv`: the per-die endpoint.
  - A per-lane contribution scoreboard sends each 16-lane word as soon as it is complete, in word order.
  - The response is multicast to every SM.
  - Optional receive-path epilogue: x' = fl(x + red), and the sum of squares in the golden R-ARITH order, computed
    on the SM's own FP pipes.
  - The link side (records, tags, order, CDC) is the original endpoint's, so the NVLS/light-FEC switch fabric is
    unchanged.
- Lowering:
  - `tools/hbm_accel_ha3.py`: Qwen, modes `cut`, `fuse` and `fuseo`.
  - `tools/hbm_accel_ha3_v41.py`: DS z exchange and both y exchanges per layer.
- Gates and tools:
  - `tools/hbm_accel_ha3_epilogue_gate.py` with bench `tb_hbm_accel_ha3_epi.sv`;
  - `tools/hbm_accel_ha3_run.py` (system runs, `+TRACE`);
  - `tools/hbm_accel_ha3_measure.py` (per-collective sections);
  - `tools/hbm_accel_ha3_record.py` (`measured.json`).

## Results (`measured.json`)
### Exactness
- Qwen reduced system (2 dies TP2 x 2 SMs): 18/18 steps match the golden, tokens 1073 382 93, in every mode at
  FLAT 5 and FLAT 7.
- DS reduced system: position 0 gives token 2815.
- Functional machine: every layer's residual matches the golden, for Qwen at 3 positions and DS at 3 positions.
- `epilogue_gate.json`, 18 cases:
  - 9 are bit-exact against both the two-op program and the golden (uniform, wide, adversarial: cancellation,
    signed zeros, subnormals, ties, 2^124 squares);
  - 9 fail closed identically on every SM (non-finite operands, a wide set whose sum of squares overflows, chunk
    overflow).
- That gate resolves, without overwriting, the two FAILED ROM verdicts
  `qwen_async_collective_20261003/FAILED_fused_epilogue_gate_{nonfinite_ieee,wide_overflow}`. The RTL fails closed
  on non-finite values and overflow (the SM's pipes' rule), so those cases are judged by an identical fault and
  identical bits, and the finite sets are judged by exact bits.

### R3a cut-through, measured in system context
| | base cycles | cut cycles | per collective | rate |
|---|---:|---:|---:|---:|
| Qwen, 18 steps, FLAT 5 | 1,577,095 | 1,514,835 | -432 cyc = 360 ns per all-reduce | **+4.1%** |
| Qwen FLAT 7 (SS pipes; base on the HA3=1 binary) | 1,600,978 | 1,526,387 | | +4.9% |
| DS, position 0 (3 of the ~7 collectives per layer converted) | 6,395,599 | 6,330,514 | -542 cyc = 452 ns per exchange | **+1.03%** |

- The model transferred 67 ns per collective. The measured saving is larger: it removes the store, fence, grid
  barrier, single-SM reload, result store, second barrier and reload around every collective.
- Of the 432 cycles, 174 are barrier waits, which overlap HA1's boundary term.

### R3b fused epilogue on top of R3a
- Kernel level: 207 -> 147 cycles per all-reduce plus norm.
- Section level: -47 cycles per layer.
- Token: -0.01% at FLAT 5 and -0.3% at FLAT 7. **Rejected** (owner rule: below 1%). The resolved gate stays as
  evidence.

### Full-shape composition: WITHDRAWN analytic, successor `composition_switch_range.json`
- `measured.json` `composition.full_shape_analytic` (DS +15% to +79%, Qwen +1.7% to +2.8%) is **withdrawn**. It
  subtracted the reduced system's store, fence, single-SM reload, result store and reload (216-452 ns per collective)
  from the W19 token. W19 never charges that work: it lowers each collective straight from the SMs' registers after
  one 78-cycle boundary. HA3 is the hardware that makes that lowering real. Without HA3, W19 is optimistic by up to
  the measured figure per collective.
- Credited term (`tools/hbm_accel_ha3_compose.py`): only the boundary that W19 charges before a collective fed by a
  matvec run.
  - This is 168 of the 265 on-path collectives in `w19_hbm_tp96_program_oreduce.json`, at 78 cycles each.
  - Total: 10.92 us per AR token and 12.01 us per MTP step.
  - Measured basis: in the all-reduce sections, barrier wait drops from 172.7/174.5 cycles to 0. Issue to response
    stays at 35.1 -> 35.2 cycles, so COLLX adds no endpoint latency.
  - HA1/R1b is REJECTED, so the whole boundary counts. With R1b kept (firm row), 47 cycles count.
- Against `tools/uarch_model.py` `hbm_switch_latency_range` (main 75456eabf), DS 1M, primary design
  `accelerator_measured_composition`, light FEC (matched to the ROM board links), tau 4.159:

| switch | AR tok/s base -> HA3 | AR gain | MTP tok/s base -> HA3 | MTP gain |
|---|---:|---:|---:|---:|
| low | 2,846.1 -> 2,937.4 | +3.21% | 6,357.0 -> 6,475.8 | +1.87% |
| central | 1,817.8 -> 1,854.6 | +2.03% | 4,765.5 -> 4,831.9 | +1.40% |
| high | 1,093.2 -> 1,106.4 | +1.21% | 3,265.5 -> 3,296.6 | +0.95% |

- KP4 FEC, the ablation, and the firm-switch row with the model's R3a/R3b credits undone are all in the file.
  - Firm-switch central, light FEC: AR +1.22%, MTP +0.86%.
- The switch scenario changes only the denominator. The removed work is on the SM side of the endpoint.
- Qwen AR: REJECT. The measured HA8 Qwen HBM-accelerator token is HBM-bound with its collectives hidden
  (`hbm_accel_ha8_20261004/REPLAY.md`). HA1, HA2, HA3 and HA6 together expose at most 0.63%.

### EPI parameter (R3a-only port)
- `ot_hbm_accel_coll_port` gains `EPI` (default 1: unchanged).
- `EPI = 0` builds the cut-through port without the rejected R3b epilogue pipes (48 fplanes).
  - A fused request latches the sticky fault (fail closed), and `s_rsp_ss = 0`.
  - The parameter is threaded through `ot_hbm_accel_coll_port_ctx`, `ot_hbm_accel_hbm_system`, the system bench and
    `hbm_accel_ha3_run.py --epi`.
- Exactness:
  - The Qwen cut runs at `EPI = 0` (`qwen_runs/run_Ce0f5.json`, `run_Ce0f7.json`) give the same 18/18 tokens and
    the same cycles as `EPI = 1`: 1,514,835 at FLAT 5 and 1,526,387 at FLAT 7.
  - The epilogue gate re-passes on the edited RTL (`epilogue_gate_r2.json`, 9 bit-exact + 9 fail-closed).

## Replay
```
python3 tools/hbm_accel_ha3.py --check --mode fuseo --npos 3
python3 tools/hbm_accel_ha3_v41.py --check --npos 3
python3 tools/hbm_accel_ha3_epilogue_gate.py --work W/gate --result W/gate.json --seeds 3
python3 tools/hbm_accel_ha3_run.py --model qwen --ha3 1 --mode cut --work W --trace --out W/run_C.json   # also base/fuse/fuseo, --ha3 0, --flat 7
python3 tools/hbm_accel_ha3_run.py --model v41 --ha3 1 --mode cut --ngen 1 --nprompt 1 --work W --trace --out W/run_C.json
python3 tools/hbm_accel_ha3_measure.py --log base_h0=... --log base=... --log cut=... --out sections.json
python3 tools/hbm_accel_ha3_record.py ... --out measured.json
```

### Source pins
- The system runs used sources at `bd3c47743`.
- The final port, `7743f6d5c`, writes the COLLX merge as a barrel shift so that it synthesises. It is equivalent:
  `tb_hbm_accel_ha3_merge_eqv.sv` gives 3,000 random contributions with 0 mismatches, and the gate re-passes on
  the final RTL.

## Revision 2 (2026-10-04): authoritative composition, physical gate, verdict REJECT
- `composition_authoritative.json` (`tools/hbm_accel_ha3_compose.py`) supersedes `composition_switch_range.json`.
  - It uses `hbm_switch_latency_authoritative()`.
  - Transport credit is 0: the Tomahawk Ultra protocol already contains the endpoint cut-through, so R3a is not
    re-credited.
  - Only the W19 SM-side boundary is credited (168 x 78 cycles = 10.92 us).
  - Primary `accelerator_measured_composition @ tomahawk_ultra_protocol`, DS 1M:
    - AR 2,562.7 -> 2,636.5 tok/s (+2.88%);
    - MTP with the measured draft 6,025.4 -> 6,122.3 (+1.61%).
- `phys3/` holds the in-context routes of `ot_hbm_accel_coll_port_ctx` (FLAT 7, 540 um, 0.833 ns, SS 60 ps / FF 25 ps),
  with per-corner OpenSTA on `6_final.odb` and `.spef`:

| | area (um^2) | SS setup WNS | SS failing endpoints | FF hold WNS |
|---|---:|---:|---:|---:|
| HA3 EPI=0 | 56,711 | -1.692 ns | 18,337 / 43,630 | -2.4 ps |
| baseline HA3=0 | 38,896 | -1.701 ns | 18,344 / 43,201 | -9.8 ps |

  - Both corners fail on the original endpoint's RX CDC -> `asmb` path.
- **Verdict: REJECT** (`verdict.json`). G-gain passes, but the routed endpoint does not close SS/FF. Under the owner
  rule there is no rescue loop.
