# RESTJ local selector and pin-distribution pilot

Reviewed actual candidate pin table in restj_local_0222_pins.png and the old
JOINED3D89 PLACE density / route congestion images. Verdict: CONDITIONAL PASS
for one PLACE pilot only, after source equivalence; HOLD before CTS/GRT/route.

The 427.68 x453.6 outline has no macros and keeps the original centre clock entry
(216,224.64). All current input/output face registers stay. The measured failing
selector broadcast becomes four same-cycle FF cohorts with <=8 immediate loads
per copy (1996 additional FF, roughly2% of the old111k-cell form). The existing
joined scalar-data/load/address +1-cycle bundle is preserved; PIN CYCLES0 new.

The old E/W pin-face clump is addressed structurally:3815 data pins move from M4
to M6, alternating along each edge. M6 uses the actual ASAP7 .064 pitch/.032
offset and .032 pin height. No off-grid or duplicate M6 positions were found.
Peak20um-bin track use is E M4 .2568 / M6 .336; W M4 .228 / M6 .304. N/S stay M5.
The M5 PDN is unchanged and M6 has no PG stripe obstruction in this macro-free kit.
This candidate interface is not adopted by the parent plan and is DO_NOT_COUNT.

The wide return bus arrives on N and the stage bus leaves W, with registered
faces. Actual copy-to-consumer reach, upstream io_r fanout, cell density, clock
sink centroid and dataflow crossing still require the placed DB. In particular,
the old W-to-centre control spine and E logic clump must not survive into CTS.
No route or timing closure is claimed by this static review.
