# Actual C18 qbank/sstn placement review

Both current-clock-access prototypes completed PLACE with RTL/SDC lint, face guard and synthesis LEC passing. qbank: 1813/1813 comparepoints, no differences/undecided; sstn: 1707/1707. No timing/sign-off claimed at PLACE.

The floorplan and density images in dsfd_qbank_S_c18/ and ot_s81_sstn_base566_c18/ were VIEWED. Both place data flops in the north/south pin bands with an open middle for the structured clock tree. No macros, slivers, walls or unreachable channels. Continuous PG vertical stripes cross the middle. Density is concentrated in the intended face-flop bands, with no geometric displacement of the wide buses; internal connections remain short. Clock-entry access lies centrally inside the clear middle. The renderer does not label the 1-bit-bus clock consistently; the ODB rectangle below is the authoritative clock location.

Full combinational r2r connectivity census (unbounded BFS, no dropped large cones): qbank3021arcs, max73um, zero>405; sstn1761arcs, max80um, zero>405. Cell lower-left coordinates are used, immaterial to these large reach margins.

Actual ODB confirms the source fix acts after the later pushdown hook: qbank ck[0] M5 rectangle(30.228,12.720)-(30.276,13.200), centre(30.252,12.960); sstn ck M5 rectangle(42.084,14.880)-(42.132,15.360), centre(42.108,15.120). Both are 0.048x0.48um, on the exact kit M5 track. The original failed c16 ODB used0.032x0.192 and off-track centre; failures retained.

Verdict PASS-COND for continuation to one trial route each, after the exact5b S81 flow canary releases. Routed clock access and real TT/FF sign-off remain required. Old unstarted original-kit queue rows are withdrawn; new rows point to these actual placed copies, so synthesis/placement is not repeated.
