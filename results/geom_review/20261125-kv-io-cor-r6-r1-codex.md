# KV IO_COR R6, reset and FT4 seats at c42dc52f02d8

**One place-only comparison after scoped PRE and strict bind.** Visually reviewed the exact proposed R1 plan seats over the R6 placed ring witness. Recorded plot E12 /srv/opentallas-scratch2/claude/KV-NOROW/iocor_r6_r1_1125/iocor_r6_r1_paths.png.

- Host-link and SerDes-W boundary bins now use nearest existing bootstrap depth-six taps 26 and 45. Placed proxy Manhattan legs shrink from 911.7 to 56.0 µm and from 563.9 to 110.0 µm. They no longer share the old t38 fork. The separate host-FDI endpoint at −522.32 ps remains in scope for the next exact collection.
- Existing FT4 reader stage 6 moves from (1236.6,18.606) to (1096.2,237.6), just east of the placed ring decode region. Source-to-shared inverter proxy shrinks from 375.361 to 15.967 µm. Stage 5-to-6 increases to 259.241 µm and stays below 300. New raw reset is bootstrap t34 at depth six. No new transport or reset cycles.
- Candidate seats avoid visible clock reservations and leave the fixed boundary unchanged. GP must establish the actual reader tail/decoder relation, recovery sink bins, density and any downstream cost. Route held.
