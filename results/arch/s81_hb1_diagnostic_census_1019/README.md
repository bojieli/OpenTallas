# Unchanged production HB1 mapped/native census

DIAGNOSTIC COMPLETE; STRUCTURALLY UNSAFE. ROOT authorized exactly one unchanged
production `ceaed19c4` / XR `cc31c2d...` HB1 mapping and unplaced native read/link.
No RTL, public helper, frozen QF input, compiler image, reset age, floorplan,
repair, CTS, route, gate, or adoption changed. The top is `ot_s81sl_xr3`,
HB=1/W=1104/V=276; only the original XR and reset relay are synthesis RTL inputs.
The generated outer wrapper inventories the inherited two-edge reset landing;
these are not two newly adopted QF data edges.

The sole mapping/native job ran through unpinned ot-run, 16GB/8threads/20GB,
on ot-epyc6 as `oth-ubuntu-3637951-1792445411`, exit0. Raw logs and all manifest
hashes are in `receipt/`; the immutable native ODB remains at
`ot-epyc6:/srv/opentallas-scratch/claude/s81-hb1-diagnostic-census-1019/out/unplaced.odb`,
SHA256 `5ed7a16d3e4b7b5580451da61f8fdcb43b509a39b7c4362855569b7c8166faad`.
The packet commits compressed raw/normalized Verilog, canonical pre-optimization
RTLIL, mapped JSON, and complete native pin/endpoint graph for independent use.

| Measured item | Actual unchanged HB1 |
|---|---:|
| Native/mapped cells | 64,383 (exact equality) |
| FF | 18,352 =17,174 HQN +1,178 ASRHQN |
| Standard-cell area | 9,250.89336 um2 |
| Native roots including transparent and clock | 69,993 |
| Nonclock nontransparent roots over32 | 73 =50 FF +21 combinational +2 ties |
| Max native FF / comb / input / tie logical pins | 2076 /2078 /1 /1179 |
| Signal pins without net; loaded nets without unique driver | 0;0 |
| Real SRAM macros | 0 |
| TT/FF/SS FF clock capacitance | 8698.411086 /9557.712796 /8181.791808 fF |

`native_census.json.gz` contains all native MTerm/ITerm directions, signal roles,
every BUF/INV-transparent root, every endpoint and polarity, every FF input
D/RESETN/SETN/CLK owner, all boundary inputs/outputs, and complete sequential
ancestors of all21 unsafe combinational roots. Native bracket escapes are
normalized only for a proven bijective18,352FF identity join to mapped JSON.
No native root is removed because its sink is asynchronous or a constant.
Clock is explicitly excluded from data fanout; its zero data-endpoint count is
not zero clock loading. Clock capacitances use actual TT/FF/SS sequential
Liberty pin coefficients, and exclude unbuilt clock-tree loads.

The two actual constant roots have meaningful original roles. TIEHI drives
1178 SETN pins plus one D pin; TIELO drives65 output pins: bo[13:20],
bo[1076:1103], ci_b[1076:1103], and x_si[7]. These are actual mapped constants,
not newly introduced stubs. Their physical tie distribution remains unsafe.
The full live1024-bit HB1 payload remains intact.

The derived source-role ledger finds1040 actual incoming-band capture FF,
1068 outgoing-band FF (36 original reserved constant output bits), all five
independent1024-bit holding states (5120FF),75 packet context FF,1027 assembly
FF, two outer landing FF and six inner reset FF (two synchronizer/four relay).
These role groups overlap and are not a partition of all state. Canonical
RTLIL preserves the complete source declarations and attributes; dead-bit
elimination is distinct from reducing the source-declared1104-bit buses.
First-use, OLD packet replacement and dated fault behavior have not been
re-proved by this diagnostic. Source captures input at K, classifies K+1,
writes selected packet/context K+2 and first qualifies unpacking K+3; any
retention successor must preserve those ages and cold/occupied-reset behavior.

The earlier XR6 HB0 routed graph had95,868cells/16,789FF. It is a different
source and physical stage, so subtracting the two totals does not measure HB
hardware cost or establish a retention result. Production has no XR6 retained
selector family/FOREG and differs in fault visibility; the source differences
remain in0f68bc609. New HB1 fixedpoint/source-retention modeling must use these
actual73 unsafe roots. It may not reuse HB0's421FF/136comb price as a receipt.

Immutable image identity is host-specific evidence here: ROOT independently
confirmed selected-host `.Id` **sha256:16470cea...ece29** and immutable
`openroad/orfs@sha256:16470cea...ece29` RepoDigest, both recorded verbatim in
`docker_inspect.json`. A shared methodology report's af971 image-ID assertion
was not authoritative for this host. The preflight verifies every declared
source/helper/config/LEF/map and all15 TT/FF/SS libs. Exact binary SHA256:
Yosys5cd52bc790d39b1e59a88112e9132ef8de338c2a26e4b0df8222d937e65bab92;
OpenROAD21eda99eeae7eccb22ca64ad28949c08a6c01dcece3ccb23e2206d635f8d2846.
RVT TT mapping uses the frozen WC-to-TC library override, 770ps, original
60/25ps uncertainty and166.667ps IO/80 load/150ps transition/260ps max slew.
`bundle/` preserves the exact source recipe; no mutable tag is used.

Yosys measured286.66MB internal peak/19.94s (ORFS time288MB/20s); whole
mapping+read/link+census wall time42.43s. Host free memory and free scratch
before/after plus scratch bytes are recorded. The outer GNU time record is
Docker-client RSS26MB, not container/native peak; native peak RSS was not
instrumented and must not be inferred from the client's RSS or admission16GB.
No runtime/address-space cap was set. Postprocessing only parsed existing JSON
and Liberty; no mapping/read-link/native census was repeated. Derived parser
failures and corrections are retained in state_analysis_initial_failure.txt:
JSON lacks cell directions, native brackets need escaping normalization, and
source aliases require transparent-chain and source-cell-name resolution.

All seven Yosys memory-to-register warnings, native Liberty output-timing
warnings, nine unused Liberty masters lacking LEF, and Python mode warning
remain in raw logs. There are no hidden warning waivers. This diagnostic
proves no equivalence, timing, physical reach405, pin spacing, clock spread,
reset recovery/removal, PG/access, parent placement or token qualification.
Next: complete actual HB1 graph fixedpoint/source-retention model, then request
a distinct source grant with exact arithmetic/lifetime/reset/retention proofs.
