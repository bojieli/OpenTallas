# SHLK11 current-route mapped qualification

Read-only census of current retry1_2_yosys.v, no route state mutation. s10c source1b3fedddc:54,807 roots,264 over32,maximum597 (124FF/140comb),19 reset-labelled violations. s10d source87bd096d8:56,761 roots,323 over32,maximum526 (129FF/194comb),19 reset-labelled violations. Complete BUF/INV-transparent nonclock census, root source/sink examples and hashes in gzipped JSONs, same script as HWIN.

s10c four legacy enable families597/586/584/583 and OR3x558 remain. s10d removed those named families but leaves ra_wp[0]526, p_kind[1]513, realigner/ap enables512, and reset/control families. No qualification/bind under binding23:45 rule even if the existing routes close. Preserve progressing routes as evidence; not a route failure diagnosis. Carry-registered sp_acc-only successor will be insufficient. Structural redesign must distribute native state/control and reset across <=32 domains, qualify all registered pin, reach, storage and functional port requirements. Do not manufacture a review waiver.

Current route daemon states remain RUNNING ep9/ep6 after shared PG-flow retries (starts23:16/23:22). Current firstclosure/native_pin_audit/bind instructions remain pending, gated on the native census qualification. No submission, cancellation, bind or main merge performed by this collector.
