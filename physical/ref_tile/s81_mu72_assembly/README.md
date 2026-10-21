# Actual selected72 MU assembly source

This is an **unhardened diagnostic assembly**, not an old parent view and not a
CLOSED record. The three parameterfree tops represent E host, E no-host and W
copy-A ends. W source can serve both north/south copy-A positions; the die binds
only actual used output ports. Copy-B/AB is outside this two-lane envelope.

The 2505.6 × 6825.6 µm reservation preserves the normal source envelope at
(43.2,43.2), 1252.8 × 6739.2. Its actual hard descendants are flattened under
`u_sl` by `tools/s81_slice/mk_mu72_assembly.py`; an unavailable normal parent view
never delays diagnostic integration. The normal source is CAP5 commit
663783aa82568d6a8d029e2ac88f65878b004e9d, spec commit3c4721d69. It exposes all10
actual normal clock roots: C/L0/L1/L3/L4 plus CAP RT/CW/CE/RN/RS. C is connected to
parent `ck_S`; the other9 are independent external pins. `ck_K` remains the
existing endpoint-side diagnostic implementation root, pending physical repair.

Right stack, unchanged hard-child envelopes, all R0:

| Instance | Origin µm | Envelope µm |
|---|---|---|
| u_ln0 |1468.8,43.2|725.76 ×583.2|
| u_ln1 |1468.8,799.2|725.76 ×583.2|
| u_lep |1468.8,1555.2|561.6 ×561.6|
| u_land |1468.8,2289.6|475.2 ×216|

The generator accepts explicit module-to-view bindings (`--bindings`) and carries
these immutable references into the placement list. Omitting them writes
**UNBOUND** rather than inventing a child view or copying a historical parent
closure. Child geometry is a reservation, not permission to resize a real LEF.
All current normal source children, including any explicitly marked stand-ins,
retain their existing status. Exact actual views can replace their entries as
soon as they close while the die team continues GEN/GRT/STA independently.

Existing sourceLP from aefbb0ca3 is reused with exactly its3-edge1104b S↔K rings,
3-edge fault crossing and2-edge fault output. It now instantiates the actual
CAP5 normal source. The accepted CAP5 schedule costs+12capture cycles against
CAPC2; no additional K-link latency is claimed before that transport is built.
The normal nested reset retains its actual reset forest; its added startup age
must be included in the die reset release calendar. Data paths are not reset by
new wrapper logic. No new tied functional port or false path is added.

**Physical repair holds:** K currently spans three long bundles: lane0↔endpoint
centreΔ(82.08,1501.2)µm; lane1↔endpoint(82.08,745.2); endpoint↔landing(43.2,561.6).
The first two carry553b each direction plus valid/ready/status; the third carries
1104b each direction plus write/read valid/fault. Their real pins and clock
regions must drive fixed-latency transport with matched data/control/ready ages.
They are unlanded in this diagnostic source; the assembly JSON records the nets
and positions for immediate parallel repair. The172.8µm central corridor and
311.04µm right cell band remain reserved. Clock/reset landing sites, external pin
projection, PG composition, GRT and corner timing remain actual die obligations.

No new test, audit, validator or closure campaign was added. No elaboration,
route or physical qualification is claimed for this source-only step. The
existing die integration flow consumes it and reports actual failures.
