# Qwen L20 SU native control prerequisite

Status: PASS, address/enable/mask component capture only; no numerical or physical adoption claim.

The current source-preserved `ot_hdc_vstream`, lane and reducer execute 14 fully static compiled L20 SU instructions independently, at SW64/LV7/AW24/NW18. The generator removes only FP add/multiply/SFU arithmetic instances, ties their unobserved outputs to zero, and retains every native address, enable, tag, class, ready, inflight, retire and reducer pair/pass statement. The extracted vline is unchanged. The summary pins all inputs and each removed instance; generated sources are reproducible in the runner output directory. Every selected instruction has A sourced from VM, so WR64 does not affect observed address/valid behavior. Production embedding dimensions are not qualified here.

After reset, go is asserted for the rising edge at cycle 5. Events are recorded immediately before each rising edge. Original instructions' dependency flags remain in the summary; they are not executed as a parent issue calendar. Each operation runs to native idle. All three operand read enables are observed, including reads of arithmetic-unused operands. Every active lane address, partial vector mask, scalar write and reducer destination is checked against the decoded affine instruction. Arithmetic values do not enter these control predicates: lane valid travels independently of arithmetic and the reducer pairs/passes based on valid, last and held-valid. Arithmetic faults are unobserved and not qualified.

Across the selected instructions, the trace contains 90428 scalar read requests, 29204 SU scalar writes and 13 reducer writes, over 738 active PRE-edge events. Observed scalar addresses span 0–97135. This is not a proof of selected live extent or the full architectural capacity.

For word = scalar >> 4, bank = (word ^ (word >> 7)) & 127, row = word >> 7, the peak is **three distinct read rows in one bank**. PCs19 and27 exhibit this at local cycle39, bank0, rows0/1/3. The peak of distinct write rows per bank is one. The maximum combined distinct rows is three. Duplicate simultaneous scalar writes are rejected; word write masks combine enabled lanes and the reducer. No SU/reducer write overlap occurs inside these independently reset operations; inter-operation overlap remains open. Raw native requests are counted before any hypothetical unused-operand suppression or arbitration.

Excluded dynamic instructions: PC3 (KV write base), PCs7/9 (RoPE constant address), PCs8/10 (RoPE and KV bases), and PC12 (context-dependent inner count). Their bindings remain prerequisites. Parent issue overlap, ME, MX, embedding, finite queue capacities, bank response timing, read-after-write/port semantics, protection and full model composition remain open. A bank with one read port cannot serve the observed three-row demand in one cycle without a measured, priced change. No bank RTL or new P&R job is introduced.

Reproduce from the repository root:

```sh
python3 tools/qwen_rom_vm_su_control_trace.py --root . --out /tmp/qwen-su-positive
```

Three mutation controls are available with `--mutant read_enable`, `--mutant write_address`, and `--mutant reducer_address`, using a distinct output directory per run. Each must fail: observed failures are recorded in `negative_controls.json`. They respectively inverted the B VM-read enable, shifted a lane write destination, and shifted the reducer destination. These checks validate the address/enable scoreboard, not arithmetic exactness.

`events.json` preserves every active lane/operand tuple and per-word scalar-write mask at its native PRE-edge cycle. Inactive buses and idle cycles are intentionally omitted. The raw CSV and generated control/bench sources are reproducible, not required as duplicated evidence.
