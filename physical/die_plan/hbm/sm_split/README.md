# HBM d4g SM internal split (HBM-QLOCAL Step C item 7)

This directory splits `ot_hbm_accel_smh_attn` (the SM, 1944 x 6955 um in r18h5) into the 4 stacked plan
partitions `q_sm<k>a..d`, each 1944 x 1736.64 um. Quarter `a` faces the VM / die centre: the `smq.rdata` and
`smq.fault` lanes land there. Quarter `d` faces the die edge: `smq.command` (command + kv_desc),
`smq.packet` and `smq.xw_*` land there. HBM-P3-SM wrote it on 2026-10-23. It is plan-stage only: no P&R and no
new synthesis.

Files:
- `sm_split.json`: the full result. It holds the children and their quarters, the cells per child and per quarter,
  the cores per quarter with labels, the crossings, the face check, the unregistered list and the calibration.
- `sm_internal_census.tsv`: the as-built internal rows, as `src, dst, bits, src/dst quarter, crossing, launch, capture`.
- `gen_sm_split.py`: regenerates both files deterministically from `inputs/` and `../die_plan.json`.
- `tools/net_analyze.py`: walks the bits through the hierarchical netlist and classifies the launch and capture of
  each one. `tools/stat_tree.py` gives the per-module totals from the hierarchical yosys stat.

## Method

1. **Source.** I used the SM view that the r18h5 die binds:
   `ot-epyc5:/srv/opentallas-scratch/claude/hbmc-r18g-1021/chainsM/syn/ot_hbm_accel_smh_attn`.
   - Source commit 4027f385f, `ENABLE_INT8=1 INT8W=1`.
   - Defines: `OT_SMH_FC_HIER OT_SMH_HIER OT_SMH_XLK OT_FP_DATA_NORST OT_SMH_DRST0 OT_SMH_RSTRELAY`. Note that
     **`OT_SMH_PINREG` is not set.**
   - The hierarchy is preserved. The netlist (35 MB, sha256 `fab96185...`) and the stat (`inputs/*.stat.gz`) were
     copied to `/home/ubuntu/scratch/hbm-p3-sm-1023/`.
2. **Cells.** These are MEASURED-SYNTH: the yosys/abc ASAP7 stat, totalled per module through the hierarchy. Where a
   sub-module has a closed run of its own (`or_capacity_runs.csv`, OpenROAD finish std cells), I added an
   EST-ORFS figure. The ratios run from 0.82 to 1.14 for compute blocks (tct, tcl_gu, bdc, pv_merge). They run from
   1.8 to 3.4 for register / pass-through blocks (pt_w, pt_e, fc_*), because hold buffers inflate those.
3. **Connections.** I traced every input bit of every SM child to its driver: a child port, an SM port, a top
   register, or a constant strap. The trace passes through the top glue. For each port bit I then classified:
   - the launch: a flop, possibly behind INV or buffer cells, versus gates;
   - the capture: flop D pins only, versus gates.
   The classification recurses through the hierarchy. Straps (`attn_column`, `xs_a*`, `xs_g*`) and the zero
   chain-ends are constants, and I dropped them.
4. **Partition.** The SM is a linear chain: `c0 c1 c2 c3 | front | c4 c5 c6 c7`.
   - Every column is 2 tiles (p0, p1) plus 1 BE. The row/beat bundles hop column to column outward from the front,
     at 3705 bits per tile and **7410 bits per column hop**. The BE result lanes (q) hop inward to the front, at
     138 bits per hop.
   - Quarters are therefore column pairs: `d = c0,c1`, `c = c2,c3 + front + int8 tile + top glue`, `b = c4,c5`,
     `a = c6,c7`.
   - The front sits in `c`, next to `d`, where the 3418 input bits land. Its 271 result bits go to `a` over 2
     registered hops.
   - Every other placement is worse. Folding the two wings so the front can sit in `d` puts 14.8k bits on every
     boundary. Putting the front in `b` adds the 3418 input bits to both c-d and b-c.

## Result (MEASURED-SYNTH, yosys cells)

The SM is **13,001,312 cells**: 2.70M flops, 1.52 mm2 of std area and 169 SRAM macros.
- 16 tiles of 770,600 each (2 x leafh 364,070, plus pt_w/pt_e/regs 42,460);
- the front, 329,283;
- 8 BEs of 41.2-41.8k each;
- the int8 tile, 9,140;
- the top's own cells, 1,203.

**One <= 400k core per quarter is therefore impossible.** Each quarter holds 3.2-3.5M cells as 20-22 planned hard
cores plus flattened glue. The core budget is <= 350k yosys cells, the convention in taps_cores_v2.py.

| quarter | children | cells | cores | max core | glue (measured) | glue + new regs (EST) |
|---|---|---|---|---|---|---|
| a | c6, c7 (4 tiles, 2 BE) | 3,165,858 | 20 | 244,462 | 83,458 | 83,458 |
| b | c4, c5 | 3,164,985 | 20 | 244,462 | 82,585 | 83,185 |
| c | c2, c3, front, int8, top | 3,504,611 | 22 | 244,462 | 92,928 | 130,306 |
| d | c0, c1 | 3,165,858 | 20 | 244,462 | 83,458 | 90,294 |

The cores in each tile are as follows. All 16 tiles share one paramod, and the straps are tie cells in the glue,
so there is one core type per role.
- `ln` = `ot_hbm_sm_attn_native_col`, 2 per tile. MEASURED-SYNTH 244,462; EST-ORFS 233,798.
- `lx` = leafh minus native_col (xs + bdc + leafh glue), 2 per tile. MEASURED-SYNTH 119,608; EST-ORFS 120-172k.
- `tp` = pt_w + pt_e + pass/gather regs, 1 per tile. MEASURED-SYNTH 42,460; EST-ORFS 109,204.

Front cores, in quarter c only:
- `fs` = `ot_smh_static_front`. MEASURED-SYNTH 165,789; EST-ORFS 307,701.
- `fa` = the attention front (kv_line, i8w, pstore, desc, row launch). MEASURED-SYNTH 163,494; no closed run.

The glue is the 2 BEs per quarter plus the new pin/relay registers. Quarter c also holds the int8 tile and the top
select. The leafh itself (364k) is over the 350k budget, so it is split as `ln` + `lx` along its existing hard
children.

Internal crossings: every one is between adjacent quarters, once the relays below are in place.

| boundary | bits | dominant | registered? |
|---|---|---|---|
| a-b | 7,848 (b->a 7,710, a->b 138) | c5->c6 rows+beats 7,410; q 138; be_cmd relay 29; SM-output relay 271 | all |
| b-c | 7,894 (c->b 7,710, b->c 184) | front->c4 rows+beats 7,410; c4 q->front 184; be_cmd 29; SM-output pin regs 271 | 3,272 NOT (R1) |
| c-d | 10,995 (c->d 7,439, d->c 3,556) | c2->c1 7,410; q 138; be_cmd 29; SM inputs 3,418 | 3,418 NOT (R2) |

**Unregistered crossings: 3 rows in 2 groups, 6,690 bits.** Only the first group (2 rows, 3,272 bits) exists as built; the second is created by the split.
1. Front `rl`/`rr` (row bundles) -> c4 tiles: 2 x 1,636 = 3,272 bits. As built, these are a mux after the launch
   flops (`attention_q ? a_rows : merged`). The `bl`/`br` beats (4,138 bits) are flop-driven, and the tiles capture
   in flops.
2. SM inputs relayed d -> c: 3,418 bits. The front feeds them straight into gates: the feed, kv_line, the int8 packet
   select (`command[116]`) and the x-write.

All other as-built crossings are flop -> flop: tile -> tile, tile -> BE, BE -> BE, and BE -> front `ql`/`qr`.

As built, two connections are non-adjacent (c -> a), and both get a relay in b:
- `be_cmd` -> the c6/c7 BEs, 29 bits;
- the SM outputs -> the `a` lanes, 271 bits. `rdata` and `schedule_fault` are gate-driven.

`request[42:0]` is unconnected on the die: no census row and no plan lane.

**Face check (risk).** The SM traffic alone is 4.0 / 4.1 / 5.7 pins/um on the 1944-um faces (a-b / b-c / c-d).
The die plan already routes die lanes through the SM stacks, at up to 7,088 bits (NW_sm1 a-b) and a median of
2.5-3.9k. Worst case, that makes 7.7 / 6.5 / 8.1 pins/um, against a budget of 6.0, so it fails. The median groups
come to 6.0 / 5.5 / 6.9. Two fixes:
- **R2-alt.** Re-land the input lanes L185/L186/L215/L216 on quarter `c` (a side face, or M8/M9 over `d`). This
  takes c-d to 7,577 bits, or 6.4/um in the worst group.
- **Die plan.** Move the SM-stack feedthrough lanes to M8/M9 (`ft_reserved`).

R5 below could also remove 2,069 bits per boundary.

## RTL changes (Step C), with cycle cost

- **R1. Front row-bundle launch.** Make `rl`/`rr` leave from flops. Add one output register stage on `rl`, `rr`,
  `bl` and `br` together, so the rows and the x-write beat stay in step.
  - Cost: +14,820 flops, about 30k cells in `fs`/`fa`.
  - **+1 cycle** on every column's rows. `BE_DELAY` becomes +1, the front result deskew is unchanged (uniform), and
    command -> result is +1.
  - The 0-cycle alternative: move the `attention_q` select ahead of the existing launch registers. That needs the
    merged path one stage earlier, so check it first.
- **R2. SM input landing in c.** Add 3,418 pin registers in `c`, plus the relay registers in `d`.
  - **+2 cycles** on command / kv_desc / packet / xw, all in step. This is a compiler schedule offset only.
  - R2-alt: re-land the die lanes on `c`. That costs **+1 cycle** (the standard die landing register) and removes
    3,418 bits from the c-d face.
- **R3. SM output pin registers in c, plus a relay in b.** These cover rv / rrow / rdata / fault / schedule_fault,
  271 bits. **+2 cycles** on results.
- **R4. `be_cmd` relay in b** for the c6/c7 BEs. 0 cycles: `CONTROL_DELAY` -1 on those two BEs.
- **R5 (candidate, not verified).** One shared beat chain per column hop. The p0 and p1 tiles both carry the x-write
  beat: `bl[0]` = w0 + A/M/O, and `bl[1]` = w0 through fc_xl/xr/b. If those beats are the same data, p1 can take its
  beat from p0 inside the column, after a local delay match.
  - Saves 2,069 bits on every boundary.
  - 0 cycles if the delay match is exact.
- Each SM partition also needs its own reset sync and epoch alignment, per the die plan reset rule. The children
  already use per-region `ot_rst_relay`.

Total latency: about +4-5 cycles from command to result per SM op, or +3-4 with R2-alt. Throughput is unchanged,
because the pipeline is static, and the owner accepts 5-10+ cycles.

**Benches to rerun:**
- smh_attn: `rtl/test/hbm_accel/sm_attn/tb_hbm_smh_attn.sv` and `tools/hbm_sm_attention/sm_attn_bench.py run
  --shape ds640|ds128`, with the kv/pv mutants;
- PV merge: `rtl/hbm_accel/sm/attn/run_pvacc.sh` (`tb_pvacc`) and the sm_attn_bench PV path;
- SM token layer: `rtl/test/hbm_accel/svg_rel/tb_toksim_smhbm.sv` and the d4g per-layer token pass
  (`tools/hbm_die_v16/d4g_layers/`).
- Also the INT8 (`smh_int8`) exact and mutant benches, because R2 moves the int8 packet select's inputs.

## Alternative: one 6.96-mm SM partition with internal 2-cycle hops

A single 1944 x 6955 um partition (13.5 mm2) holds the same 13.0M cells. At the same core budget it is 82 cores:
32 `ln`, 32 `lx`, 16 `tp` and 2 front. Its glue would be the 8 BEs, the int8 tile, the top and the relays: about
343k as measured, and about 383k with R1 and the relays. That is close to the 400k cap, against 83-130k per quarter
in the 4-way split.

Advantages:
- No seam pins. The 7.4-11.0k internal bits per boundary stay on M2-M7 inside, which removes the face-budget
  overflow above.
- 1 partition type per SM group instead of 4.

Disadvantages:
- The single tap is 3.48 mm from the ends (4.45 mm L1 to a corner), against the <= 1.2 mm per-tap rule. It needs at
  least 6-8 internal taps, the same clock structure as the 4-way split but without plan-checked boundaries.
- The inputs still travel about 2.6 mm from the d edge to the front, so latency is the same: the "2-cycle hops" are
  R2/R3 under another name.
- One OpenROAD assembly would carry 82 macros, plus about 383k glue on a 13.5-mm2 top. The largest closed block in
  our archive is 517k cells and 0.40 mm2, so nothing comparable has closed.

**Recommendation: the 4 stacked partitions.** That means front in `c`, R1-R4, and R2-alt where the die plan can
re-land the inputs. The die plan must take the SM-stack feedthrough lanes off the inner SM faces (M8/M9), or R5
must be verified, before G3.

## Implemented (HBM-P4-SM, 2026-10-23): `QSPLIT`

R1, R2-alt, R3 and R4 are in `rtl/hbm_accel/sm/attn/ot_hbm_accel_smh_attn.sv` behind the opt-in parameter `QSPLIT`
(define `OT_SM_QSPLIT`). The default, 0, leaves the netlist and the behaviour as before. R1 uses the +1-cycle form; the
0-cycle form was not proven. Every new register stage is a named `ot_smh_qs_reg` instance with its quarter in the name:
- `u_qs_c_land` (c): R2-alt. All 3,418 input bits, including the int8 select `command[116]`, land in one register.
- `u_qs_c_r1l` and `u_qs_c_r1r` (c): R1. `BE_DELAY` becomes +1.
- `u_qs_c_pin` (c) and `u_qs_b_out` (b): R3.
- `u_qs_b_becmd` (b): R4. `CONTROL_DELAY` becomes -1 on c6 and c7.

`QSMUT` 1-4 are bench negative controls:
- 1: R1 on the west side only.
- 2: no landing stage on the packet.
- 3: R4 without the `CONTROL_DELAY` -1.
- 4: no relay stage on rdata.

Cost:
- Command -> result: **+4 cycles** (R1 +1, R2-alt +1, R3 +2, R4 0), uniform across ops.
- Top glue: +18,809 flops (14,820 + 3,418 + 542 + 29). That is +38.6k yosys/ABC ASAP7 cells, of which about 18.8k
  are QN inverters (1,229 -> 39,815 top cells, children black-boxed).

**Structural check.** `tools/qsplit_check.py` elaborates the top with yosys, with the children as black boxes, and takes
the child port kinds from the measured classification. Results are in `qsplit_check_q{0,1}.json`.
- `QSPLIT=0` reproduces the census groups: `rr` 3,272, the inputs, and the c->a outputs and `be_cmd`.
- `QSPLIT=1` **PASS**: no unregistered and no non-adjacent quarter crossing.
- `QSMUT` 1 and 4 FAIL the check, as they should.

**Benches** (Verilator 5.050 via ot-run, source 8617e0378). Records are in `qsplit_benches.json`.

| bench | default (QSPLIT=0) | QSPLIT=1 | delta | mutants (all FAIL as expected) |
|---|---|---|---|---|
| smh_attn element (`sm_elem_bench.py`, `tb_hbm_smh_attn`), ds640 and ds128, qk_sm0 + pv_sm0 | PASS | PASS, bit-exact | first result +4 in every op | M1: pv faults, 8/512. M2: schedule_fault. M3: qk faults. M4: every word mismatches. |
| SM token layer (`toksim_smhbm.py` L00, `tb_toksim_smhbm`), 20 ops | PASS 20/20 | PASS 20/20 | every op span +4 | M4: 0/20 |
| INT8 SM.MATVEC (`qwen_sm_mv_unit.py` L0 qkv/o/gu/down, ENABLE_INT8) | PASS 4/4 | PASS 4/4 | +4 per op (3206 -> 3210 ...) | M2: schedule_fault on 4/4. Compiler `late`: 4/4 FAIL. |
| wide INT8 (`--i8w`, INT8W=1) | not run | PASS 4/4 | not measured | M2: 4/4 FAIL |
| PV merge (`run_pvacc.sh`) | PASS | n/a | n/a | MUT1 FAIL. `ot_hbm_accel_smh_pvacc` is not in the SM top, so this is a regression check only. |

`sm_attn_bench.py` builds `tb_hbm_sm_attn`, a sub-assembly without `ot_hbm_accel_smh_attn`, so QSPLIT does not touch it.
