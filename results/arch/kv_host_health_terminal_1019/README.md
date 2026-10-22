# Actual host health source-to-terminal audit

Evidence only, pinned to GEN7 `4db097403`, canonical die SHA `7006cbd0d11ffb755902c588eec474a1a7c27d7ad77212cebe3be1fcae5aae7e`. No RTL, roles, fault membership, schedule, or physical views changed. Original strict FAIL **45863 unread / 69 open port types** remains. This packet follows inventory `4072f9d57`; minimum357 including DCAL is not a complete fault inventory.

The selected HOST has SERVICE=NATIVE=TOKEN=1, NL2. Its nested package controller is **MU0, ND8, DONE_REG1, WDOG4194304**: control_packet_admission does not pass a MU override; control_prompt_observed retains MU0. This HOST profile must not be attributed MU1 behavior simply because other die blocks use MU.

## Actual missing consumer

`qkd_host_root_admission` line578 routes record/peer/coordinator/rootmux faults into rank physical_fault. Rank-services line97 adds boot/completion/ingress/program/commit/host-observer/peer-link faults to observed_physical_faults. However, guard.bad is exactly `protocol_fault || internal_bad || |next_sticky`; **pf_q and tf_q do not participate**. They only reach physical_diag/transport_diag. Fullcontrol forms c_fault_vec, which goes to fault_src and the full32bit CSR diagnostic input, not package-controller fault/ready. CSR latches it and can interrupt according to masks; soft_reset is an explicit AXI write, not an automatic fault action.

Consequently the physical/transport **summary path** has no proved terminal-failure, cancellation, or subsequent-admission predicate. Some original sources have additional effects (program faults independently block program_ready; codecs can refuse traffic; coordinator identity_fault blocks request admission). Those effects must be traced per source; the missing summary consumer is not a claim that every source has no other protection. The minimal simulation specifically injects physical/transport input flags and demonstrates healthy completion through this mechanism. It does not inject a real record decoder fault or prove fullhost healthy completion under every internal failure.

## Service health and terminal conditions

All25 service_fault bits are enumerated in `source_terminal_graph.json`. Guard samples raw→fm at E1, fm→fs at E2, and at E3 latches sticky/abort, taints guarded_tk88, and lowers service_ready. Host-reset clears these; a source held high relatches. Protocol faults have a separate captured pin/internal path. No functional cutoff masks continuous health.

The actual local role0 chain then has two collected registers (lt then tk8), one ctl_service input register, one qkd_host_ctl input register, one DONE_REG reduction register, package die_fault/eng_done, and response pin register. **The reduction requires d_done AND current generation AND d_fault.** These are logical edge counts, not a physical/reset or unconditional latency bound. With a matching report already present, the raw-fault E1→response E10 chain follows from these registers. A fault with DONE low does not itself complete/fault the package. A report that never arrives reaches a watchdog policy, not a priced fixed STATUS bound. MU1 additionally gates die fault detection on a new drained-generation report; it is not the selected nested HOST profile.

Service_abort feeds captured controller **ready**. Existing work does not test ready; a subsequent START is rejected after the observation pipeline. Sticky guarded_tk can fault a later matching completion, while an already emitted healthy terminal cannot be retroactively changed. Late-fault overlap and subsequent-completion policy therefore require explicit full consumer/retirement proof.

Package_abort is ctl_res1. In collected token service it becomes abort_q, then abort_seen; grant/peer-token acceptance rejects the abort state. Cancellation needs a genuine retained request, allocated tuple match, all four actual drains, and an unconsumed cancellation. It emits exact stage37 identity, cancel_fault1/done0. The rank codec sends it to the coordinator; acceptance/release needs real identity, drains and reservation return. These conditional protocol paths are recorded as **unbounded/unpriced** here, not converted into a fixed completion claim.

The linked engine's original result_fault enters coordinator result transport, rank result decoder, native endpoint result validation, local_tk, guard, collected status, controller and host retirement. The native endpoint's fault_q comes from result_fault/protocol_fault; there is no direct global host physical/transport/service input into the engine fixed STATUS in this graph. A default-off redesign must explicitly choose and wire the required predicate before assigning any terminal latency.

## Source and reset ownership

`source_terminal_graph.json` retains exact top HOST clock/reset pin expressions. Guard/collected/controller/peer/records/coordinator use n_clk_core_c0 logically; some raw service sources originate PHY/host/ingest roots, so their actual synchronizer and native observation bounds remain mandatory. Guard/controller clear on derived host_rst_n; coordinator, peer codec and retained ownership state also use por_n. Warm HOST reset is not equivalent to clearing all original sticky sources or retained identities. No native skew/phase, loaded reset delivery, finite POR/admission counter, AHUB hf clear+34/37 relay drain, STATUS edge, or cutoff is admitted. recovery_complete/readiness/epoch/certificate are prerequisites, never error bits to OR.

`sources.json.gz` + `manifest.json` pin19 exact source files; the13 selected HOST bodies match the original archive, and six transitive sources were independently hashed in the actual GEN7 source tree (`transitive_remote.sha256`). Root proof and raw native pin sources remain in predecessor inventory. The machine graph records missing consumers and nullable timing obligations explicitly.

## Minimum mechanism witness

Fleet unpinned ot-run unit `oth-ubuntu-1838032-1792432902`, Verilator5.050: **21 checks PASS**, three causal mutants FAIL. The vehicle contains actual guard/FIFO and actual ctl_service→qkd_host_ctl→pkgctl. A single guarded TK is replicated8 ways only to exercise the ND8 reduction; actual packet/link transport is **not** simulated or qualified. Source trace, rather than this fixture, establishes the production collected registers.

Checks cover physical/transport diagnostic arrival with no terminal fault, raw synchronizer exact three edges, inflight service fault with DONE low, matching-DONE failure, sticky health, late fault after healthy completion, subsequent-start refusal, and reset clear. Mutants drop raw faults (actual guard MUT1), bypass late admission health (actual ctl_service MUT1), or retain sticky health across reset (one source mutation). Committed logs retain each exact failure. `audit.py` checks immutable source premises and witness text. No gate or submit ran.

ROOT review is required for a terminal predicate mechanism, not a public-port OR or diagnostic waiver. Every selected source/consumer must enter the fixed STATUS and reset/native pricing; the next source must include explicit observer ownership, all deadlines, loaded clock/reset bounds, source clearing and drain, and counter-width/age pricing. DCAL successor owns its separate added fault and fixed-image cal_ready/adm_done obligations.
