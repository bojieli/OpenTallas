# XR6 is structurally unsafe: 357 nonclock roots exceed 32 logical pins

This is an immutable diagnostic and model packet, not an RTL repair or gate authorization.
The original XR6 and fallback results remain valid timing observations, but neither is a SAFE tile.
No new synthesis, simulation, placement, or route was launched. No RTL bytes changed.

Source: `7ef9383db5788cbb9428ccc264bb34484071b541`, branch `claude/s81-safe-fix-xr1-1019`.
The local source and the exact gate snapshot both hash to
`b10a2c142dbf31e465f382b7f6cd3c6b354cd90be536ae015d159bcfe9f1bee6` for `ot_s81sl_xr.sv`.
Original remote gate: `ot-agidock128:/srv/opentallas-scratch/claude/ref_gate/s81sl_xr1-20261019-113126`.
Read-only native analysis used its `routes/gate/work/orfs/results/asap7/opentallas_ot_s81sl_xr1_asap7_ref_gate/base/5_1_grt.odb`, SHA256
`078ca172072d4158e7ae2e53b07fad9c2756932f211b79534efe7856794532ba`.
The short original analysis failed on an unconnected clock-load buffer; the retained analyzer explicitly counts that buffer's input pin as a terminal. Its completed rerun was ot-run unit `oth-ubuntu-1929781-1792439387` (exit 0).

`native_census.json.gz` contains every root and every terminal pin; `offenders.json` contains all 357 offenders, including complete sequential ancestor sets for the nine combinational roots. Counts traverse BUF/INV/HB cells without treating a buffer as a logical fanout boundary. Distinct native input pins count separately even when they belong to one cell. Clock pins are excluded from data endpoints; the clock input and its 680 terminal dummy-load pins are explicitly classified as clock. Top input max is 8, tie max 2. This census does not prove unconnected-net absence, placement legality, or timing.

The native design has 95,868 cells, 16,789 FF, and 88,098 roots. There are 348 offending FF roots and nine offending combinational roots. Important families:

| Source family | Offending roots | Maximum pins |
|---|---:|---:|
| registered RD write-enable `rwe_c` | 160 | 92 |
| registered unpacker read selects `un_c` | 85 | 70 |
| registered packet write-enable `pkw_c` | 32 | 64 |
| registered row write select `rwr_c` | 20 | 94 |
| registered ENG one-hot `eoh` | 15 | 34 |
| registered injection select `cis_c` | 9 | 64 |
| input ENG valid `ev_c` | 5 | 197 |
| input partial valid `pv` | 5 | 66 |
| local reset relay | 4 | 270 |

The two largest combinational roots `_50814_`/`_50831_` have 1043/1039 endpoints and originate in the E/W RD classifier (`eb`/`wb` header, valid, and `sid_oh`). `_87931_`/`_87924_` have 548/545 endpoints from E/V kind/valid classification. Source comments saying 32-bit chunks imply 32 loads are false for enabled-register/mux mappings: one data bit often consumes two select pins. Reset relays have 270, 171, 79, and 52 endpoints.

## Cost and reset model

A clone-only arithmetic lower bound is 408 additional FF and 154.66464 um2 of native FF area, with at least 408 additional clock sinks. This is not a feasible completed design: it excludes upstream useful decision logic, reset/clear feedback, input-copy pressure, clock wiring, and buffer costs. Clock capacitance and complete fixed-point cost remain NULL in `model.json`.

A naive independent duplication of every sequential ancestor of each broad combinational root, at 24 endpoint pins per group, adds 4995 FF and 1554.8112 um2 before the FF-root repair. That proposal is rejected: it would make repeated header input bits drive more than 32 same-edge capture copies. It is not an upper bound or an area quote for a safe tile.

A bounded reset-only proposal partitions the current consumers into 25 final relay copies rather than four. All final copies sample the same existing sync stage: two sync edges plus one relay edge remain three; the kit's separate two face landing stages are also preserved. This proposes +21 FF, +7.96068 um2 native FF area, +21 clock sinks, raw reset 25+2=27 loads, and final sync 25 D loads. The slot allocation is in `model.json`. Its leaf target is 32 reset bits, which is not yet a 32-logical-pin proof because reset polarity/next-state logic can add pins. No source implementation is retained or claimed verified. Any useful-copy expansion changes this allocation and requires a fresh fixed point.

The next source model must jointly partition registered input headers, actual useful classification decisions, consumer bit groups, and reset leaves. Independent input capture copies should each drive a bounded group of independently computed useful decisions; merely preserving equal-D combinational copies is not a sound physical boundary. Either prove the same-edge topology preserves all ages or price an added decode/payload stage in the compiler and token model before building.

## Storage and full SAFE review

The unpacker has five independent 1024-bit captured packet banks, total 5120 bits. Each captures one packet, then selects one of four 256-bit chunks with `un_c`; these are chunks of one packet rather than four generations. Read and write on the same edge observe the OLD contents under nonblocking semantics. `ub/un/ul` allow a replacement on the final consumed-pair edge and flag early overwrite. A blanket 5x1kb waiver has not been adopted: prove each independent bank's lifetime/OLD collision or replace with a real SRAM organization whose read/capture ages preserve the external stream. The aggregate capacity and indexed read cannot simply be ignored.

| SAFE item | Exact current result |
|---|---|
| pin registers / reset | Existing input/output capture plus two face reset stages; complete pin-by-pin ancestry not requalified here |
| reach <=405 um | Not requalified; no source-mapped stage-wire certificate in this packet |
| all logical-pin fanout <=32 | FAIL, 357 nonclock roots |
| depth / TT stage budget | Original gate TT setup +23.1 ps; no successor depth proof |
| storage | HOLD: packet-bank lifetime / independent-bank interpretation or real macro replacement |
| outline / band / faces / PG | Original pin-bound 311.04x395.28 gate; no new floorplan or parent-fit approval |
| clock / boundary | Original spreads 56.5/55.1 ps; inherited insertion requires actual neighbor compensation; no new native approval |
| static schedule / token rate | No RTL change, no data-edge change; successor and composed token prices remain NULL |

Next: complete the whole-source useful-copy/reset fixed point and unpacker lifetime model, then implement one bounded opt-in source successor and run the existing 5.050 positives and four mutants. Only after full mapped-role, depth, storage, and geometry evidence should a new gate be considered. Never submit current XR6 based on its WARN timing result.
