# RF36 image-shaped local programme candidate — unadopted

This is a separate additive candidate derived from the recovered RF36 image
`ef51677866608d14c080d0aef73939220f5e18230a566a015d511c0f07daff2a`.
Its serial dictionary has **302** original SRAM banks. Column 28 uses four
banks and crosses the quarter-2/quarter-3 boundary, so four local producers
require **476** macros: 98, 141, 101 and 136. The 301/474 source-shaped component
proof remains separate; its observed baseline area/FF values are not inherited.

The actual mapped candidate retains 476 target SRAMs, 23,931 FF, 9,688 registered
command bits, four controller roots, 41 column roots and 476 individual macro
clock roots. Maximum internally driven net fanout is 256, including the
command gates. Standard-cell area is 12,679.27830 um², excluding SRAMs. The
increment over the actual 302-bank baseline is 174 SRAMs / 0.677530376 mm²;
the new standard-cell area is not compared with an unmeasured 302-bank baseline.

These are mapped structural observations, not native timing or source adoption.
The recovered manifest retains its own `qualified:false` scope. Exact-image
playback, fixed compiler priming/release, failing mutants, full native
composition and start-to-final-commit cost are being handled independently.
Real programme homes, pin/cut capacity, read selector/configuration routes,
per-pin clock insertion, TT setup, FF hold and DRC remain open. No token-rate
or accepted-price credit is granted.

The generic RTL is pinned to `4cceac7f5`. The new wrapper explicitly overrides
global/local counts and the actual dictionary vector; the S contract and normal
programme RTL are unchanged. `receipt.json` records the exact source, model,
parameter, manifest, checker and mapped output hashes and the admitted run.
