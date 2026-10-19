# SAFE checklist: no gate admission

1. Pins/reset: existing registered data boundaries retained; XR reset relay is
   existing, rstop raw reset load2505 is UNSAFE. Reset/abort mechanism tests PASS.
2. Reach: no new channel width. Complete model uses real V bridges2/5/6, but
   actual geometry/clock phase and883 unlanded end-lane traversals remain OPEN.
3. Fanout: FAIL. Mapped XR38Q/96nets>32, rstop9Q/57nets>32. Kept distribution and
   actual source/native reset ownership are not implemented by this minimum cut.
4. Depth: OPEN. Synthesis only; no actual path-depth/native timing qualification.
5. Storage: mechanism PASS for real SRAM read/write semantics; no new payload
   buffer, +7 mappedFF/XR versus baseline, original rstopFF count unchanged.
   Full programme scratch480..487 and capture/assembled/combined/pre/post leases
   still need actual lifetime proofs. Existing storage is not globally waived.
6. Floorplan: OPEN. Measured standalone area is source sizing only. No geometry,
   pad/band fill, pin-face, parent slot, PG or physical route admission.
7. Clock: OPEN. No CTS/native/parent clock qualification. Source component pin
   edges are precisely named and exclude DL4/Vlanding/PHY/native phases.
8. Schedule: minimum fixed pin calendars PASS including sustained4/2-pair
   traffic and causal violations. Complete shared line/CTL/XQ/XB/CI/SRAM-port
   calendars remain unreserved; global admission remains false.
