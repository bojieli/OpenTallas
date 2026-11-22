# S81 C north strip round i

**Floorplan reviewed for placement.** I viewed the exact type in split7i plan `deb79547b806`. The 1,442.88 × 43.2 µm strip has no macros. Both dimensions are on the 8.64 µm PG grid. Both faces carry 6,437 data pin sites distributed over M5 and M7, with a peak of 6.99 pins/µm across the plotted 100 µm bins. The longest of the 17 planned register legs is 404.298 µm. Clock tap planning from the 6,437 source sites gives a peak load of 848/1,500 and maximum reach 86.520/100 µm. The 8.64 × 28.08 µm monitor storage band is isolated. Its mapped row capacity is a placement check.

The previous north round failed PORT_BIND on a dead START relay pin. The recovered split still needs strict bind and LATCHECK to finish. The next proof is placement only. Actual DPL, pin access, map density and GRT review remain pending. Figure is at Intel2 `/srv/opentallas-scratch2/claude/flow-stripbody-r2/strip_n_round_i_review/strip_n_round_i.png`.
