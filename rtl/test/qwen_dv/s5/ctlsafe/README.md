CTL successor construction from exact source1f858dec1, default HARD1/MU_NU4/MUT0. Read-only original snapshot and generic source constructor preserve every state edge and original reset release. qfd_dv_s5_ctlsafe exposes the original interface; HARD0 delegates to qfd_dv_s5_ctl(HARD0). HARD1 selects fixed full-shape qfd_dv_s5_ctl_bounded4. Unsupported HARD1 shape/mutants fail loudly in simulation.

construct.sh runs only fleet synthesis, not layout. The existing bound_math_netlist.py replicates overloaded FF and combinational roots recursively, preserving distinct identities and including their added D/reset input loads in following passes. Constructed 21,924 original cells ->22,163. Each generic root<=32, clocks excluded. Native mapped census remains required; generic counts are not signoff.

gen_tb.py generates the full interface bench. bench.sh uses exact original HARD1 versus generated bounded4, compares all19outputs on8,000edges and two midrun resets, plus independent checker mutation. PASS151,677 comparisons; checker mutation FAIL7,983. No additional steady-state or reset cycles. Existing parent production benches and d11 witnesses are separately preserved under headsctl_pickup_1020.

No layout gate or submit until native fanout, pin, reach405um and storage all pass. The generated helpers must be included once in the production source inventory. The generic constructor input JSON and mapped output/receipts are retained by the live pinned fleet job at /srv/opentallas-scratch/claude/codex-qw-ctlsafe-1020/construct3.

Separate reset-stage/cap16 successor: `qfd_dv_s5_ctl_bounded4_rst1.sv` and `qfd_dv_s5_ctl_bounded_rst1_helpers.sv`. This is fixed HARD1/NU4/MUT0 and has no parameter interface. An unreset distribution stage after the original two face-landing stages adds **one assertion edge AND one release edge**, with zero steady-state data cycles. The compiler/boot schedule must hold both reset transitions one additional clock before issuing commands. The explicit delayed-reset reference passes151,677comparisons/8,000cycles and two midrun resets; checker mutant catches7,983. Model record is `construct_rst1_16/reset_schedule_price.json`.

The cap16 constructor bounds only internally driven nets16; raw inputs remain hard<=32 and fail if replication overloads them. This leaves margin for ABC translating genericMUX selects into two native input loads. It is **not native qualification**. Child isolatedamax generic32 produced actual max64 and55internal/5raw-port violations; that evidence is on codex/qw-amax-csafe-1020, and demonstrates why native census remains binding. No failed evidence is overwritten. Helper defaultcap32 output and helper bytes were verified identical to the original zero-reset-delta source.

Live mapped jobs, preserve both:

- ot-epyc5 `/srv/opentallas-scratch/claude/codex-qw-ctlsafe-1020/construct3`, original cap32 zero-reset-delta, local ot-run2891938, unitoth-ubuntu-1492343-1792482266.
- Same remote root `construct_rst1_16`, cap16 +1assert/release, local ot-run3018469. Job logs local `/home/ubuntu/scratch/codex-qw-ctlsafe-1020/construct{3,_rst1_16}.log`. Clients are recorded in pending_results. Bench jobs are terminalPASS; no layout gates/submits were launched.

After either job exits, collect exact netlist+logs and count actual mapped loads:

```
scp ot-epyc5:/srv/opentallas-scratch/claude/codex-qw-ctlsafe-1020/construct_rst1_16/mapped.v /tmp/ctl_rst1_16_mapped.v
python3 rtl/test/qwen_dv/s5/ctlsafe/native_census.py /tmp/ctl_rst1_16_mapped.v > /tmp/ctl_rst1_16_native_census.json
```

Repeat for construct3; preserve both pass/failure evidence. Only zero offending roots satisfies fanout. Then verify rawresettwo-stage landing, every input/output registered,planned wire geometry within405um, and storage. Current source-bank census: outputoq1929bits(one-stage), inputchd1038, amaxal0912, NU4run228. Current old kit outline side alone is not proof of every-net reach. Do not gate or submit until all checks pass.
