# Preserve landing placement while removing repeated reservation scans

The old all-cells landing allocator stored every historical row reservation separately. Each new cell rescanned those ranges from the band corner. The change stores their exact sorted union, merging only overlapping or touching intervals. Every positive gap and every existing fit, footprint, capacity and alignment rule stays unchanged. It adds no RTL, flops, pins or cycles. Existing live jobs are untouched.

An actual coll_ucie pre-GPL native trace supplied 10,000 consecutive cell footprints, 56,817 initial fixed obstacles and 3,176 real rows. Both old and new allocators reproduced every actual native coordinate and orientation: zero old/new or native differences. The same-host replay measured placement time632.359s ->11.928s (53.01x); setup0.240s ->0.667s. The real physical trial remains independently gated by its actual placement review; this is an allocator equivalence/performance receipt.

Four further mixed-width/multirow cases test row and column packing with and without cursors, nested/touching/overlapping reservations and the legacy zero-width point behavior: all32 coordinates match in every case. The39 focused landing tests (33existing +6new gap/footprint/multirow checks) pass.

Reproduce from the repository root with a scratch output path:

```sh
python3 results/cland_union_0336/replay.py results/cland_union_0336/baseline.tcl tools/die_plan/landing_placement.tcl results/cland_union_0336/actual_trace.json.gz /srv/opentallas-scratch2/claude/cland-replay.json
python3 results/cland_union_0336/cases.py
```

Base:mainadada000244. Native source:the isolated QC46 fully fixed PHY trial, saved2_floorplan.odb plus complete captured placement prefix; no running physical job was restarted or edited. Valid replay:epyc2 ot-run unit3119919, output benchmark.json.
