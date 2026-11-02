# StoreA source-authoritative ingress lineage and regional bounds

This is prospective repair input, with no RTL edits, synthesis, new pipeline stage, source/default activation or physical claim. It traces the exact frozen SOURCE13 B113 caller (`9c9baa…`, physical variant `b34269…`), selected top (`eb1b46…`) and actual CTL/VM/reset closure from `d55715edb`. Critical StoreA/CTL bindings are identical on both B113 variants; all ten actual peer paths are retained, rather than borrowing old C11e4 names.

The 2,256 problematic ingress bits are not all unregistered upstream:

- `store0_sw_d[2047:0]` is directly driven by CTL `g_compose_m23_q`, an always-capturing 2,056-bit register on `clk[0]`, reset asynchronously by `n6` / generated `m55.rst_n[2]`. Data bit `i` uses register bit `257*floor(i/256)+(i%256)`, excluding eight return-valid bits. There is no enable.
- The exact D of that register is `u_core_procdff_66926__D`: three 514-bit B113 `xi_…66926_D__{2,1,0}_q` input-capture banks plus `L54_i_q[509:0]` and `L127_i_q[3:0]`. Their real `ot_dp_st` payload FF are resetless and capture every `clk` edge; companion epoch FF have a separate reset and must remain intact.
- One earlier real stage is each peer `u_bout`: SU31/SU20/SU11 capture the 514-bit native `c_rr` output; SU00's two existing L54/L127 outputs reconstruct the same 514 return bits. L54's additional four control bits are preserved in the original source and are not silently treated as data. All four quarters supply 512 payload bits each after valid-bit exclusion. Thus peer output capture → B113 input capture → CTL m23 are three existing stages available for a distributed, source-priced proposal. The native source before peer output capture is retained as its actual D expression; its registration and physical reach are not assumed.
- `store0_sw_addr[119:0]` and sixteen stage-group control bits are terminal VM `m56.g_lg[g].meta[88]` FF slices `[37:8]` and `[41:38]`. Their exact D is the same slice of `meta[87]`; `meta[86]` and `meta[85]` are also actual preceding stages. They shift without enables and use `clk_lg[g]=clk[0]` with asynchronous delivered `rst_lg_n[g]=CTL rst_n[0]=B113 rst_n_t22`.
- Eight `comb32..39` stage-valid controls are combinational `expect_v & ~scalar` from terminal metadata bits `[42/43]` and `[6/7]`, not separate FF Q outputs. A strict copy of existing Q drivers needs sixteen FF bits plus eight local ANDs.
- All sixty-four `store0_sw_mask` bits are source constant one (`VM stage_mask=64'hffffffffffffffff`), not FF drivers. A local constant/tie realization needs the exact selected caller/source contract; it cannot silently replace the current general-mask native ABI.

The current StoreA reset comes from generated region 1 (`m55.rst_n[1]`). It cannot replace the region-2 reset of copied data state or the delivered t22 reset of copied metadata. A prospective native split must expose those distinct reset roles, the actual older-stage D ports and mapped clock/net/phase. Logical `TOP.clk_stream` equality does not qualify physical clocks or reset arrival. Warm/reset and all existing used outputs/epoch companions remain exact obligations.

A complete strict terminal-state private copy costs **2,200 FF per chosen region**: 2,048 data, 120 address, 16 group and 16 expect/scalar bits, plus eight local stage-valid ANDs and actual distributed mask ties. This is conditional replication cost, not an adopted count. Each additional copied existing data stage costs another 2,048 resetless payload FF per region; each copied earlier metadata stage costs 152 asynchronous-reset FF per region. Originals remain for all their used outputs. Same-edge copies do not make D reachable for free, and synthesis must not merge deliberately distinct physical replicas. No region count, copy depth, new ABI or reset/latency contract is selected here.

Exact per-write-pin regionalization bounds were recomputed on the same two-gutter layout. The source-access model optimistically permits any point in an entire 1.404×0.27 µm FF body, both row orientations, no other stdcell occupancy and independent placement. A failed row check is conservative; candidate existence is not simultaneous placement or D/clock/reset closure.

| Candidate grouping | Regions / macros per region | Maximum continuous source-point radius | Optimistic row failures |
|---|---:|---:|---:|
| Memory families | 2 / 16 | 457.116 µm | 4,256 / 4,384 |
| Left/right vertical halves | 2 / 16 | 379.380 µm | 4,256 / 4,384 |
| Memory × column halves | 4 / 8 | 275.652 µm | 0 / 8,768 |
| Memory × row halves | 4 / 8 | 403.092 µm | 8,512 / 8,768 |
| Four vertical columns | 4 / 8 | 288.648 µm | 0 / 8,768 |
| Compact 2×2 bank blocks | 8 / 4 | 221.628 µm | 0 / 17,536 |

These checks cover 2,192 variable ABI bits; the 64 source-constant mask bits are excluded, as are two separate 16-bank read controls. The table shows why neither sixteen-macro regions nor merely a point bound under 405 µm is a sufficient placement proposal. The next concrete work is to select and model existing-stage replication/placement using the actual D lineage, include all native/source/pin/clock/reset costs, and prove source equality before a fresh physical build.
