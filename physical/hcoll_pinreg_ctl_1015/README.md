# Native controller physical candidate

The current production-source candidate is `ot_hgi_coll_static_capture_ctl`
(TX6/RX2, source f7280c70d), with every normal input first captured before any
guard, epoch or CRC fork. Its stored payload input directly feeds the existing
q_pin first-capture register. Generic mapping measures 4,421 clock sinks.

`capture_geometry.json` freezes the requested 324 x 216 um outline and every
port pin coordinate. The controller sits below four 207.36 x 129.60 stores,
with 20 um channels; bank order is bottom-left 0, top-left 1, bottom-right 2,
top-right 3. N-face bank input/output bits interleave by lane so neither wide
bus is grouped into one half of the face. E/S ports are placed individually.
The requested composed outline is 434.72 x 515.20 um.

Using the store owner's frozen ordered S/N pins, the longest requested
Manhattan hop is 385.913 um. A 4 um snapping allowance leaves 110.087 um of
the 500 um total for pin-to-flop access. This is a requested pin model; actual
exported LEF coordinates and compensated routed timing must prove the hops.
The model makes no routed reach claim.

The original TX5 diagnostic mapped 3,207 sinks and 2,539 um2 standard cells.
Its 324 x 216 footprint has sparse utilization: the footprint serves physical
pin pairing and channel reach, and its full area must be priced. The older
200.88 square was never an assigned or measured controller contract. Its gate
also exposed raw external reservation paths before first capture. The TX6
successor fixes that structural input branch before physical qualification.

The first exact-pin TX5 attempt failed in the Tcl helper because a caller-local
block variable was incorrectly read as global. The helper now queries the
block inside its procedure. Both original gate records are preserved. The
current recipe uses reference-tile recipe 2, signals and PG through M5,
measured boundary IO, 833.333 ps TT setup, FF hold, and SS sensitivity. Native
endpoint positive and stale full-sequence controller mutant are attached as
behavioral gates. No gate threshold is changed.

CTS/pre-route and the final route are separate evidence. No physical closure,
FEC, CDC, or token-rate qualification follows from this candidate plan.
