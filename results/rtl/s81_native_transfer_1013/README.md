# Native H transfer component candidates

Not a native120 dispatcher qualification. No accepted cost row or price change.

`ot_s81_htransfer` observes full-row H_STORE writes at the **VM commit** boundary,
starts the queued HIDDEN descriptor at an eight-row watermark, and holds each
subsequent VM request until the requested row is committed. A producer can stall
arbitrarily after the watermark. `ot_s81_htransfer_boundary` combines this with
the pin-registered FD16 landing tee from throughput candidate **8a3a18070**.
Apply that dependency before integrating the boundary.

The boundary expects the actual HC queue HEAD descriptor. Current hierarchical
cseq has `e_d[83:0]`, argument `e_d[30:7]`, slot `e_d[83]`, and descriptor
acceptance `e_v && e_r`. H_LOAD input-present can be early only for the exact
landing base of that slot. Post-Engram and other bases retain normal dependency
checks. The latest external `c_cmd` is not the head. Those head/accept signals
are not yet exposed through the physical parent; changing its pins requires
coordination with the HC and die leads. Hop return-valid mode is required, and
its maximum outstanding requests must be at most HDEPTH. The stage compiler
must queue the ordered hop descriptor before H_STORE crosses the watermark.
Slot reuse requires prior message completion, as in the package controller.

The faithful **component** gate uses production 640x512-bit payloads, the actual
32-bank VM (behavioral SRAM contents, native control/address pipelines), VM
adapter and hop framer. HC arithmetic is outside this test: committed rows are
golden stimuli. Base and eight-cycle relay plus stalled link each deliver 641
flits/640 exact rows, one completion, zero early reads and no faults. Producer
pauses 40 cycles every 16 rows. The early-read mutant fails with 633 errors;
the incomplete-mask mutant faults and cannot emit a message. This proves the
cut-through control mechanism; it is not a measured native layer cost.

The FD16 landing gate uses candidate8a3a18070, overflows before the late consumer
asks, queues all slot0 requests before the landing completes, starts slot1
landing while slot0 fallback drains, then loads slot1 and reuses slot0 in stream
mode. All 640 rows of each load match, zero early reads/faults, one streamed and
two VM-fallback loads. Early-VM and response-data mutants fail. The VM here is a
row scoreboard, so these are landing-controller assertions, not VM qualification.

`native_transfer_audit.py` hashes all 59 committed immutable stage programs.
They contain 80 abstract HC POST operators in 41 groups, and zero explicit
H_LOAD/H_STORE commands. This does **not** establish native transfer counts.
The deployed native120 program/engine lowering, coefficient split bindings,
field/link/collective timings and measured full composition remain missing.
The boundary candidate is not physically qualified, slot-bound or adopted.

Heavy gate: ot-run4GiB EPYC1 unit oth-ubuntu-176023-1791945789, exit0.
Landing initial run: ot-run2GiB EPYC1 oth-ubuntu-197126-1791945982 completed all
three simulations; its first parser rejected Icarus's trailing finish line.
The corrected parser independently validates all preserved raw simulation logs.

Corrected full landing gate rerun completed through ot-run2GiB EPYC1 unit
oth-ubuntu-199813-1791946017, exit0; all three raw traces and final receipt are
preserved. It was admitted after a verified 60-second memory wait.
