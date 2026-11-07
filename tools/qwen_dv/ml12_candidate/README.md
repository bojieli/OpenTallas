# Private SU0 ML12/read-return candidate

Source-only research form. No child P&R, signed child/default/interface change, library replacement, plan event, or count claim.

The physical vP4 wrapper adds four stages to all outgoing fields. Read requests therefore reach their memories four clocks later. The old child uses MEMORY_ALIGNMENT=3 and READ_EXTRA=0 (head ML8). Merely moving a receiver start does not change its read sampling.

Existing ALIGNMENT=7 is unsupported and its generate branch also omits the VM3/WR1 relative alignment. Raising READ_EXTRA to4 alone reaches the real W133/D20 flop-ring limit (2527slot bits >2048). These failures are retained in E4 codex-qc-types-1107/ml12_bench/out/{guard_run,shape_run}.log and the failed guard-only wrapper fixture here.

The private source copies existing modules under private names and preserves the old D16 ring (1995slot bits). Four explicit 133-bit reply stages add532bits for D20. The narrow HW8 metadata ring grows by32slot bits and about1pointer bit: approximately565additional state bits/head,2260for four children. The original 2048-bit ring guard is unchanged. Arithmetic is unchanged. Existing production modules remain byte-identical.

Numeric proof uses the real head, independent address-derived memory responses, all five request ports, varying per-cycle addresses/destination tags, BYP/multiply/add and VM/KV writes. The baseline return contract is VM10/WR12/CROM13 clocks from request pins, derived from the real head's face/capture pipeline and checked against independent destination-tag payload goldens in BYP cohorts. Extra4request clocks and the vP4 output4 clocks are explicit adapters. A phase census measures output timing instead of assuming it.

The constant-address preliminary bench was insufficient: request-delay and operand-alignment mutants survived. Its reports are retained, but are NOT proof. The sensitive benches include a zero-request unchanged-child control, the unchanged ML8 child with request4, and private ML12 versus wrong READ_EXTRA3, request3, and ALIGNMENT7 branch controls. Fault injection and class-switch/reset-in-flight cases are not covered; fault-free arithmetic/read transport and quiescent reset are the tested domain. No child build is authorized from these results alone.

Current runtime artifacts on Intel2: /srv/opentallas-scratch2/claude/codex-qc-types-1107/{ml8_req4_job,ml12_split_job}/out_v3. Earlier failures and weak tests remain on E4 at /srv/opentallas-scratch3/claude/codex-qc-types-1107/ml12_bench. Latest scripts/logs are under Intel2 ~/codex-qc-types-1107.
