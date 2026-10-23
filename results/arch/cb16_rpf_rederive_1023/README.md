# Frozen CB16 rpf structural geometry recovery

Current die slot:2445.12x5227.2um. Sixteen reviewed rpf A0 children:457.92x1157.76um, same lattice, same capacity. Current parent has237 hard children. No RTL or static schedule change is proposed.

The first fleet packing retains all current hard-child shapes and fits237/237 at20um pair clearance with no overlaps; however moving108um-wide ring tiles out of146.88um vertical corridors causes up to2786.4um displacement. This is a failed reach strategy, not a gate-ready parent.

The same step starts a concrete replacement: ring514/516 shape90.72x64.8um (+26% area, i/o <=5.972pins/um on the existing M5 faces), xstn/xstnw43.2x302.4um (+11% area; b_d and a_d/tap_d on separated vertical-face windows <=4pins/um). Same source/top/parameters, zero added cycles, no old view alias. Fleet narrow packing also fits237/237,20um pair clearance and zero overlaps; maximum displacement768.96um. Displacement is NOT wire reach. These are new physical children requiring their own native/gate/route/view qualifications.

Files plan.json/packing.png preserve the first result; narrow_plan.json/narrow_packing.png preserve its executed replacement. Complete pin-to-pin connectivity, current rpf A0 pin snapshots, obstacle routing, scalar/reset placement and real clock references remain prerequisites to a parent gate. Unknown current synthesis density is explicit. Independent geometry review is requested on the four child SHAPE plans, not on a fabricated complete parent or a permission to P&R.

Fleet:ot-agidock128:/srv/opentallas-scratch/claude/codex-cb16-0404-1023. Initial unit3891514 completed packing then rendering failed missing matplotlib; exact plan.json preserved and rendered locally. Corrected narrow unit3893344-1792753455 exits0. No synthesis or simulation ran locally.
