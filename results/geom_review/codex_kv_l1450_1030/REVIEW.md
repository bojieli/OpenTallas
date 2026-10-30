# L1450 existing FF-bank PREP review

Viewed review.png: existing final bank moves left inside the clear horizontal channel; first164 low-window bits move34.02um down within that channel. All outlines, macro origins, public pins, clock/reset entry sites, stages, cycles, RTL and K values stay fixed. Full1119-site rectangle check finds0 otherFT/self overlaps and0 macro+4.32um halo collisions. Per-bit mandatory-pin path max477.599→403.565um; predecessor max386.964um. The initial center-only −40um candidate was rejected because164 actual bits still437.599um.

PASS-COND for source-plan preparation only. Actual generated/native landing/clock/reset cells, occupancy, placed G1 and timing remain required; no P&R/STA launch from this review. The3 bit-site planes are correct: internal stages1..3; stage0 follows actual input pins (ft_bit_sites.py/ft_station_probe.py).

Current mainb2 check.py ordinary G0 baseline1ERROR/2094WARN→candidate0ERROR/2094WARN, removing only L1450 mandatory-seam hop. Clock landing/branch-buffer/entry/merged-view summaries unchanged. Completeness remains20/56 clean; no dieG0C pass or timing/clock model rerun is claimed.
