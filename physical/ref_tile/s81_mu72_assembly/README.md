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
endpoint/lane diagnostic implementation root; MU landing memory now has a real
external `ck_ML` root and fixed-latency regional crossings.

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
The first two carry553b each direction plus valid/credit/status. They remain
unlanded pending actual relay/landing placement. Their return signals are
credit pulses, not ready levels: endpoint TX consumes finite CRED8 credits and
receivers return one credit per freed slot. Fixed-latency transport must preserve
every pulse and charge increased credit RTT; no new handshake or credits are
introduced. The third connection is repaired in source as described below. The172.8µm central corridor and
311.04µm right cell band remain reserved. Clock/reset landing sites, external pin
projection, PG composition, GRT and corner timing remain actual die obligations.

No new test, audit, validator or closure campaign was added. No elaboration,
route or physical qualification is claimed for this source-only step. The
existing die integration flow consumes it and reports actual failures.

## Implemented MU landing memory crossing repair

`ot_s81_mu72_land.sv` uses the existing chunk8 D4/K2 landing writers/readers,
local reset forests and real source/destination clocks. No new flow control or
storage protocol is introduced. Each instantiated crossing has exactly3
added destination edges under the existing phase/offset contract:

| Crossing | Bundle | Added edges |
|---|---|---|
| K→ML write | `{mwv,mwd[1103:0]}` |3|
| K→ML command | `mu_rc[10:0]` |3|
| ML→K return | `{mf,mrv,mrd[1103:0]}` |3|

The replay command and write both move by3, preserving their relative full-slot
ordering. Original `rc`→first returned valid/data latency4 becomes10 edges,
**+6** through command and return transport. The compiler must shift endpoint
replay-use and the associated user/position control schedule by6 before release;
merely issuing a delayed read with the old identity-use schedule is invalid.
MU capture write completion shifts by3. The existing CAP5+12 price remains
separate. Actual compiler integration is OPEN, not implied by this source.

The endpoint N face and MU memory S face are separated172.8µm. The three bank
sets have an explicit soft-cell reservation `(1468.8,2116.8,561.6,172.8)` inside
that gap. Actual native placement, phase spread, PG and timing remain unmeasured.
The external `ck_ML` clock/reset is not tied to K or replaced by an SDC alias.
No hard child source, dimensions or ports change. No new validation campaign
was launched; ongoing die integration can exercise this next source generation.
