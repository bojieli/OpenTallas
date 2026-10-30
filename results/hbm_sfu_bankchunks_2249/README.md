# SFU bank-chunk source and native inventory

The current operand-major store cuts create long traffic between SFU lane groups. Four independent four-lane memories would change the selected hardware's semantics: its N=16, M=16 bank network permits lane 0 to read any bank, and other lanes select from `{l, l^1, l>>1, (l>>1)+8}`. This prototype instead exposes four-bank source components while preserving that existing network.

The selected source parameters come directly from the current b29d Yosys cache: operand groups use N=16, M=16, LWB=15, NS=8, NLW=0; the output group uses NS=2, NLW=16. `build_bankchunks.py` extracts the original group/bank modules and changes only bank hierarchy. The complete selector, priority, conflict checks, reset and data state are restored byte-for-byte by its constructor invariant. Original source modules remain available. No arithmetic or cycle is changed.

The actual M=16 one-operand-group vehicle initializes all 32,768 words in 16 real SRAM models, exercises every candidate-bank family, all eight sector ports, initialized reads and write conflicts. It passes 2,567 edges and 196,608 known read bits with zero differences. A wrong-write-bit mutant in chunk 0 is caught on 402 edges. The clock is exactly 833 ps with 1-fs simulation precision. This is the minimum shared group needed to exercise all candidate-bank routes, rather than a full SFU array.

Native Yosys inventories use the actual macro blackbox library, not behavioral SRAM contents:

| Component | SRAMs | Standard FF bits | Scope |
|---|---:|---:|---|
| Four-bank component | 4 | 12 | 225 input bits including clock, 128 output bits |
| Full operand-group interface | 16 | 538 | Includes the exposed drain interface |
| Actual operand-group constants | 16 | 497 | Unused drain/stream/lane-write ports folded as in the selected source |
| Actual drain-only output group | 16 | 61 | NS=2, NLW=16 |
| Four operands plus output | 80 | 2,049 | 240 bank-select FFs and 1,809 shared steering/state FFs |

The four-bank source component can be reused 20 times per half. Grouping four banks from each of the five stores yields 20 SRAMs and 60 local bank-select FFs per spatial cluster. Shared steering and conflict state are still required; this artifact does not eliminate or independently qualify them. Small constant `cbank` lookup memories remain in the intermediate native counts and map to logic in the normal synthesis flow.

The actual aligned SRAM LEF is 172.824 × 41.064 um. A preliminary, unreviewed one-column four-bank outline of 198.72 × 224.64 um can leave raw macro gaps >=10.8 um, occupying about 63.6% macro area. This is arithmetic sizing only. Boundary timing, pins, clock entry, halos, PDN, routed geometry and all physical gates are NOT RUN. The die owner retains the existing narrow opstore repack until a full source/plan change is composed.

Runs and full native netlists are retained at intel1 `/srv/opentallas-scratch2/claude/codex-hbm-bind-2249/bankchunks`. The passing production files are `tb_actual.sv`, `run_actual{0,1}.log`, `synth_abstract_v2.*`, `synth_group_actual.*`, `synth_drain_actual.*` and `synth_operand_context2.*`. Earlier M=8 runs are diagnostic only and retained. The first native-count launch selected a behavioral macro file and omitted default-branch macro declarations; it failed before hierarchy completion. The corrected actual blackbox inventory passes. A wrapper-generation quoting failure was repaired before the passing source-context count.

## Current ring ID contract evidence

`ring_qid_actual.json` resolves the actual native cut's qid through each selected source hierarchy port. NE is **2'b11 (3)** and NW is **2'b10 (2)**. Terminals are `hb_coll_{NE,NW}.u_body.u_ring.qid[1:0]`; g4's native cut exposes those exact bits as `strap_qid[1:0]`. These are source identities despite the physical core's `__q0` name. The die owner is applying the existing static strap contract to remove two wrong-face boundary FFs in the fresh ring kit. No source ID was guessed or changed here.
