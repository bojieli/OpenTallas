# CTLM existing-producer reset contract: bounded observation

The existing production reset sequencer captures a short pulse while its clock is stopped and holds CTLM reset after clocks resume. This resolves the cause at the sequencer input; it does not close safe2 reset, epoch, timing or first-use obligations. No production RTL, helper, SDC, macro, kit or calendar changed. ROOT selected this existing-contract investigation before the fleet component build.

## Exact source and scope

`source_receipt.json` pins the unchanged modules: qfd_rstseq from rtl/qwen_split/qfd_link_slots.sv at 4d2cb6301; ot_qwen_rst_rep at the same commit; actual landed primitives at 911a17fa6 (the previously observed safe2 source). Copies here contain exact extracted module bodies; the common primitive file is copied whole. There is no alternate reset implementation.

`die_reset_receipt.json` pins production dv2f18dh2 die SHA 7b1bdfc5fd26c2e6f17fe6aa5b1d68bd9e2fa05bc3ecf408b9f163eb600bbde7. Actual tt_ctlm is the old single-clock qfd_tt_ctlm_dv on r54, rst_n=n_rst_seq_ctlm__t25. Its upstream sequencer output rso_ctlm reaches that leaf through ten qfd_rst_rep nodes, 20 nominal registered edges. Node names and clock ownership r54/r474/r476/r55 are retained in the bench. The old die does not bind the successor safe2's two clocks: choosing diagnostic core=c54/hr=c55 is a fixture, not a production binding or a measured phase receipt.

qfd_rstseq has asynchronous assertion on rsi. Its two synchronizer bits, 11-bit counter and five reset outputs retain the assertion even when ck stops. CTLM release requires s[1] and n>=FLUSH+3*STEP=1280 with unchanged defaults FLUSH512/STEP256. The exact nonblocking edge ledger reports release at n1281. The production behavioral qfd_ckbump always toggles its PLL clock independently of rs (20ns cold reset), but it is not a physical PLL relock or independent-child-clock-stop contract.

The sequencer input itself is n_rst_fwd_s__t12, downstream of qfd_rstsync and another registered tree. This bench injects at sequencer rsi. It does not prove arbitrary package reset pulses propagate through that upstream path. A pulse asserted only at the final landing leaf remains unsupported when that clock is stopped.

## Fleet evidence

Verilator5.050, unpinned ot-run ep4 unit oth-ubuntu-3573333-1792439567; original setup attempt's stdin tar transfer failed before any build, preserved in setup_failed_client.log. The corrected source was synced to seven eligible hosts before unpinned placement. The run built once and executed 14 cases: phase -2000/-1000/-500/0/500/1000/2000ps, initial reset release100000/102000ps. All 14 report ROOT_CONTRACT PASS with assertions enabled. These are deliberately diagnostic 8000ps periods, not the production833ps period or native timing proof. c474/c476/c55 have phase/3,2phase/3,phase relative to c54; exact values and selected phase are available in the bench.

The source is first allowed to become genuinely warm: all four slots valid and registered output0x3c. All clocks then stop; a10ns pulse at rsi is asserted and released while stopped. The sequencer retains reset0/counter0. The tree, landing warm/valid, and registered output initially retain their old state, as expected for synchronous downstream state. After all clocks resume, the stretched root reset traverses the actual ten-node path and safe2's existing regional pads/rq; vld, warm and output become zero. A distinct value0xa5 is then captured and observed on the registered output after normal release, with no new warm-up comparison mask.

Phase0 ledger (ps): root assertion23110000; stopped output3c/leaf1/warm1/vld1111; leaf assertion23454000; explicit resumed flush23700000 has root0/leaf0/wrq0/rrq0/warm0/vld0000/o00; root release33558000; leaf release33718000; writer and reader rq release33750000; first writer capture33758000; first output observation at the following monitored falling edge33778000. The output observation is not the capture instant. No asynchronous output clear is claimed: stale output persists during the stop and initial propagation; production consumers must remain within their independently proven reset/admission contract.

`leaf_negative.log` preserves the exact negative: same warm state and stopped clocks, pulse injected only at leaf; warm1/vld1111/output3c survive and LEAF_PULSE_LOST exits1. Positive and negative statuses are in statuses.tsv; wrapper exit0 is not interpreted as a positive verdict for this negative.

Additional unique initialization build (--x-initial unique --x-assign unique), runtime random-reset2 seeds1/17/131, passes the same isolated component at phase0. Unit oth-ubuntu-3577245-1792439624. This does not resolve the existing full-source startup assertion failure before regional reset propagation (911a17fa6): all original full-source failures remain preserved.

## Model and remaining contract

No hardware is added; additional area, clocks, data edges and reset release edges versus existing source are zero. Existing sequencer source state is18 async-reset FF bits (2 sync+11 counter+5 outputs); those are generic source bits, not verified mapped native FF types. Ten selected path repeaters instantiate30 source FF bits, with unused output optimization and additional live branches requiring the whole-native census. Regional pads retain5 FF bits; no inherited reset stage is removed.

The full26 crossing inventory remains952 payload bits,3808 ring data bits,952 reader bits,56 local groups. Their source functional state is5936 bits plus672 assertion epoch bits. The local control state is1176 bits (21 per writer/reader group), including112 rq bits and1064 synchronously reset counter/selector/valid/warm bits. This aggregate source accounting is not a storage exemption, a mapped area estimate, or fanout qualification. Logical banks max748 bits; independently indexed >2kb storage and existing real macro policy remain unchanged.

HOLD before a new kit:
- Actual production first ss5 edge relative to the successor writer's rq. The real first19 token loss/first20 acceptance remains separate; no root stretch automatically grants the required producer age.
- Source-pinned safe2 ck_core/ck_hr binding and native TT/FF phase/insertion plus reset release epochs. Neither old FAILED dh2 nor these diagnostic phases qualify that contract.
- Upstream bump/qfd_rstsync/tree delivery; all-phase asynchronous pulse width, recovery/removal and native mapping. Independent child stops while the source root continues are not covered.
- All actual CTLM outputs, complete arbitrary-initial-state startup and abort/warm-reset production joins, registered pin and source admission proofs. A stale retained output cannot be called immediately cleared.
- Every native nonclock root including reset and copy-D fanout, native FF types, full clock/area cost and exact source-to-slot-to-read ownership. Blanket writer-to-reader MCP remains forbidden.
- Dense64x512 macro face10.2pins/um and DPL failed geometry remain structural HOLD. No unchanged reroute, helper adoption or reset hardware approval follows from this packet.
