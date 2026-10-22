# Production FFN combine and POST row binding

Implemented the missing software producer placement and command encoding against
the actual p4l source. This closes an arithmetic/row-binding component, not a
layer, token, die, or physical qualification.

The previous generic GAP_FOLD conflated two different operations. Attention wo_b
is split by input columns and needs a four-rank arithmetic reduction. FFN down
is split by output rows:1280 per rank,80 per source slice. Its canonical combine
adds the six routed expert outputs in ascending expert-ID order, then shared,
then rounds to BF16. Existing VS13 already implements that chain; no arithmetic
RTL change, extra storage macro or data cycle was introduced.

`tools/s81_dv/layer_prog/final_ffn.py` now emits the real capture map,4480
eight-word source/destination RD pairs, unique global64-element ownership,
VS13 command, and VP POST with a0=1009/a1=448. It preserves pre1008. A subsequent
480-beat result allgather copies combined rows to the other three ranks, whose
four residual copies are replicated. It carries61440 data bytes, in addition
to143360 bytes in the local assembly map. These are data volumes, not a qualified
line schedule or token price.

The opt-in `xs_calendar.py cap --final-ffn-placement` binds actual down capture
CFGs to these rows. The actual L0 generation passes64 phases and336 modified
slice configurations with zero cap decode faults; unrelated configurations and
frame tags remain identical. Phase leases reuse dead VPX rows. The lifetime
checker rejects overlap, and local lowering requires all56 pair arrivals for
the destination and refuses a combine on a non-owner rank. `lower_vpx.py`
exposes the actual templates but emits zero engine calendar rows while current
transport paths/reservations are missing. Pending cycles explicitly refer to
the VP input pin, so they cannot be mistaken for seq_host issue cycles.

Verilator5.050 on the fleet, actual saved L0 checkpoint down/residual/HC values:

- All80 global beats pass the real VP+VS13 arithmetic cut:5120/5120 combined
  values. Every measured command-to-last VS write is75 edges.
- All80 pass the composed actual VS13→VP POST→VN residual SRAM→HSTORE/RDOUT:
  5120 combined values,20480 residual BF16 values, and retained pre1008/post1009.
  POST command-to-last h write is63 edges. These are component pin ages;
  current fixed test slots reserve100 edges and are not an adopted token price.
- Wrong owner and shifted source rows each fail192 comparisons in the composed
  beat37 cut; wrong POST a1 fails128, swapped comb coefficients fail64.
- The full mapping/lifetime guard rejects88 causal errors. Real cap output
  comparison and opt-in lowering guards also pass.
- Pure shared-first reordering is numerically insensitive on the tested beat0
  BF16 values and PASSES. That log is retained as an insensitive control; it is
  not counted as a failing mutant or a proof that arbitrary reorder is legal.

The first POST test failed because its readback overlapped the final HSTORE
cycles. Its raw logs remain under logs/post_failure. The successor uses a fixed
idle calendar edge before readback; it does not wait on runtime ready or add
producer backpressure. Arithmetic RTL is unchanged.

Reproduce generation with `vs/gen_final_ffn.py --fixtures <L0> --out <vec>
--beat <0..79> --post`, then `FINAL_FFN_POST=1 bash vs/run_vs_bench.sh <repo>
<build> <vec>`. All builds/binaries are preserved on ot-epyc8 under
`/srv/opentallas-scratch/claude/s81-final-fold-1019`; use ot-run unpinned for
subsequent heavy work. No HOP build or binary was changed.

Next actual integration: schedule the generated RD assembly and peer allgather
on current16-slice/end-link paths, reserve every CTL/line/write-port slot, prove
producer completion and VPX leases, and compose host-to-VP pin ages. Then run
the actual G8 head norm with real gain provisioning, NX/XB reservations and
owner/drain proof. Previous-layer pre transfer, full head vocabulary/return,
draft and IDX helpers, native timing and physical closure remain open.
