# Selector quadrant s3s_a safety and sizing

Structural successor to s3r_a/b. Source is the same 16-lane selector quadrant, with three 256x256 SRAMs; the microarchitecture and registered_s3 calendar add zero edges. Parent integration must price the quadrant footprint increase from 55,987.2 to 149,299.2 um2 (+166.7%); the prior 600x450 parent slot cannot contain four quadrants.

1. Pins: source pin landing and output registers are retained; dedicated wrapper pin stages remain disabled to avoid changing calendar latency. Two synchronization stages plus one regional tree stage release 15 source reset leaves. Reset release and first-use remain subject to the existing exact and scheduled bench receipts; no new reset waiver.
2. Reach: planned bottom cell band height149.04um and width341.28um; top macro-to-band separation at most236um. Actual placed-net reach must be <=405um before adoption; the outline diagonal alone proves nothing.
3. Fanout: unchanged exact source passed both s3r mapped all-driver Liberty censuses, max31, zero violations and zero role errors including resets. Current gate repeats the census before floorplan. No physical buffering substitutes for the source bound.
4. Depth: predecessor mapped source depth approximately 600ps; real placed timing remains required. Same kept prefix/priority hierarchy and one-hot select pipelines; no combinational input-to-output path introduced.
5. Storage: bulk 196608-bit record capacity is three real SRAMs. Source remaining words are pipeline/one-word registers and histogram counters; no new delay storage, indexed register memory or storage waiver.
6. Floorplan: LEF SYMMETRY X Y admits the chosen R0; R90 was rejected. Literal origins x86.4/y172.8,259.2,345.6 are on43.2um lattice. Vertical macro gaps45.336um; core-edge clearances >=20um. One real FENCE holds soft source cells in x2.16..343.44/y2.16..151.2. Approximate 27600um2 source area /50863.37um2 band=54.26%; actual placed cell/band coverage must be measured. Wide side buses remain <=5.49pins/um. Outline aspect1.25.
7. Clock: single clock port centered on S next to the fenced register mass. No clock exception or SDC relaxation. Measured pin-flop spread must be <=80ps TT and FF; parent boundary compensation/landing remains mandatory. IO hold margin30ps retained.
8. Schedule: static registered_s3, no credits/backpressure, +0 cycles. Larger physical parent integration and reach remain open until measured.

Original s3r terminal failures are retained in results/rtl/hbm_idx_static/selector_s3_fan32/takeover_collection/s3r_terminal_failure_summary.json with raw remote execution paths. Passing native census and bench results do not establish physical closure; s3s clock, reach, actual cell fence, GRT and full timing are pending.
