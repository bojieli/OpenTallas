# Private VN_b registered-chain-input candidate

This is a source/proof proposal, not an adopted child interface or physical view. The exact native instance is `u_bound.u_u_vn_u_b`, LA=6, LM=5, HW_STAGE=0. The inherited native define set does not enable OT_S81_VN_CONST_ZERO.

The candidate lifts the existing 31-bit `c_s_q` capture and one-bit `c_v_q` valid capture into the parent. The child exports its exact `rs_c` reset feed; the parent valid capture therefore asserts and releases reset at the same events as the original child capture. The payload capture remains unreset. No reset relay is duplicated or moved. The arithmetic and all downstream child state are unchanged.

The private child ABI renames c_s/c_v to c_s_q/c_v_q and adds one output, chain_rs_c. There are still exactly 32 capture flops and zero added cycles: child clock sinks -32, parent clock sinks +32, total state unchanged. Parent before/after instance excerpts are included. `make_candidate.py` extracts the actual child and capture processes, checks the exact instance and parameters, and writes the complete private child plus parent candidate from native input files.

The smallest composed four-state proof checks the exact changed 32 cut bits before and after every active edge and on asynchronous reset assertion, with the actual ot_rst_relay implementation. It passed 6000 cycles and 12063 strict checks, including 62 mid-run resets and 207 words containing unknown payload bits. A direct-data bypass mutant is deliberately checked after startup and fails at cycle13; using external rst_n instead of the child's rs_c feed fails at cycle3. Fleet unit: intel2 `oth-ubuntu-4140552-1793364288`. This establishes the changed cut identity; it does not claim a newly qualified whole-child view.

The R2 timing interface changes substantially despite the zero cycle cost. The old VNa-output-to-child-input-capture path becomes VNa-output-to-parent-capture, followed by a parent-registered-input-to-child-combinational arc. ROOT must review an explicit registered-input contract. The new child needs new ABI/pins, source/native qualification, clock modeling, timing and physical review; the parent needs composed STA. No old native view is reusable and no input-flop guard waiver is requested. Physical improvement has not been measured.

The source parent is the actual frozen inherited native bound body from `intel2:/srv/opentallas-scratch2/claude/codex-s81types-1030/kv_bound.sv`. Its hash is recorded in impact.json. Types' separate inherited594/current597 parent external width mismatch remains held; this proposal makes no current parent ABI claim. The generated full private parent is retained in `/srv/opentallas-scratch/claude/codex-vnb-rin-1030/candidate/parent_candidate.sv` and its fleet copy.

Reproduce source generation from the repo root:

```bash
python3 results/s81_vnb_rin_1030/make_candidate.py \
  --rtl rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vn.sv \
  --parent NATIVE_BOUND.sv --relay rtl/lib/ot_rst_relay.sv --out OWN_OUTPUT
```

Compile `cut_miter.sv` with the actual `rtl/lib/ot_rst_relay.sv`, top tb, Icarus `-g2012`. Run default, `-DOT_VNB_RIN_MUT_DATA`, and `-DOT_VNB_RIN_MUT_RESET`; the latter two must fail with CUT DIFF. No physical stage has run.
