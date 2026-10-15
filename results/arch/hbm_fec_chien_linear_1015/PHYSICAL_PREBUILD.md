# FEC physical prebuild: actual large steering is a structural blocker

Scope is the exact standalone full wrapper counted by `full_census/receipt.json`.
The joined endpoint, 613/487 gearbox, production calendar and delivered clock
family remain outside this receipt. No physical area or routed closure is claimed.

## Actual prebuild evidence

The admitted full generic-netlist analysis (`generic_prebuild.json`) sees 149,972
combinational cells. Its conservative scalar-expansion sizing model assigns
15.65 million units, principally to 114 shifts and 57 variable read selectors
(12.08 million units). These are deliberately conservative sizing units, not
mapped gates or area. Generic whole-cell connectivity also couples independent
bits conservatively; exact cross-root pin counts await the scalar graph.

One source-bound bit-mapping attempt was run from the already completed full
census netlist. At 03:34:30 PDT, the kernel killed Yosys in its 64 GiB cgroup with
66,967,380 KiB anonymous RSS. The tool returned 143 when its scope terminated.
`physical_prebuild/bit_mapper_0` preserves the input binding, map script, last
Yosys log and authoritative kernel OOM report. No scalar netlist was completed.
There was no larger-memory retry of that source.

The offending source structure includes 55 sequential variable-position
read/modify/writes of a 5,440-bit word, each correcting a 10-bit symbol. A safe
physical candidate must expose bounded, local symbol wiring rather than assume
these operations fit an old SerDes gap.

## Distinct structural successor

`gen_fec_static_correction.py` generates an actual combinational correction bank.
Existing 55 Forney values and hit bits enter fixed, symbol-owned 10-bit slices.
The existing cc=0..9 phase selects the slice group, with only 49 valid symbols in
phase 9. A balanced exact popcount counts the same valid hits. It adds no state,
clock input or cycle. Original and first linear-candidate sources remain intact.

Direct numerical proof exercises 16,144 vectors: every cc=0..15 value, error-value
basis, hit basis, all codeword input basis bits and random vectors, compared with
the original dynamic-write semantics. It passes; an actual steering-wire mutant
fails at phase 0/vector 0. Full actual FEC passes 2,048 words with unchanged age
102 and 2,376 decoded words checked; actual Forney MUT2 fails at cycle 302.
Proof logs are under `static_correction_proof/`.

The new full census is running as unit `oth-ubuntu-1799123-1792060811`, output
`/srv/opentallas-scratch/codex/fec-chien-linear-1015/static_correction_census_0`.
Its exact flattened state and scalar expansion remain unproven until collected.

## Placement and partition alternatives to measure

1. **Twelve root regions:** retain the current root-owned state as twelve hard
   leaves, allowing no leaf to inherit physical closure from the source count.
   Place capture -> syndrome -> four BM units -> Chien -> emit/CDC according to
   actual registered connections, with the TX collect/encode/codeword chain
   beside its own PMA pins. This is the simple comparison, not a demonstrated fit.
2. **Symbol-owned receive banks:** distribute the 5,440-bit current/original
   codeword registers into ten phase banks, nine of 55 symbols and one of 49.
   Match the emit capture banks to these banks, and place the four BM codeword
   stores beside the corresponding Chien bank faces. Keep the real BM polynomial
   arithmetic beside syndrome/coefficient interfaces. The new static correction
   steering enables this topology without adding an arithmetic edge. Actual
   cross-leaf buses, pin faces, area, clock delivery and legal geometry still
   need explicit RTL/physical interfaces before it is a hard-leaf inventory.

Both alternatives preserve current arithmetic, reset semantics and cycles.
Shared combinational logic must have an explicit owner or priced replication.
The exact scalar graph tool reports state-to-state logic levels, registered
source-bit crossings, external interfaces and shared/unique sink-root cones;
it refuses a combinational cycle or residual non-scalar primitive. Its method
is checked on a twelve-root graph with exact cross-root and two-level paths.
A successful source-bound scalar map is required before applying it here.

No route is authorized by this document. Next gates are: successful new-source
full census; bounded scalar expansion; exact state/clock and interface graph;
explicit hard-leaf source partition; actual TT library area and timing; geometric
pin/channel fit; then pre-route admission. Wire delay, reset delivery, recovered
clock phase, and joined endpoint roots remain separate mandatory checks.
