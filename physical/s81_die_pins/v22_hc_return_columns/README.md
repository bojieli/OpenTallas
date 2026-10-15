# Provisional HC return-column pins: parent reach blocked

These are candidate pin assignments for the provisional v22 shapes, not routing grants. The shape grant remains conditional on GEN18r legality and pin alignment. No native timing or parent closure is established.

The exact successor at source commit `46d0620d8` moves the A merge registers into COLUMN0 and adds the real `peer_fault[2:0]` / `peer_hnz[2:0]` inputs. All eight source port sets and widths match these files. Changing the peer flags to two bits is rejected. Every pin passes face bounds and 0.096-um spacing on each face/layer. Each leaf retains its own serial clock root; actual insertion R and delivered phase remain unresolved.

The files in `c0` through `c3` contain the same RTL master names with their respective COLUMN parameters. Do not combine these directories as one master assignment: the COLUMN-specific pin coordinates differ. The actual kit must select its own directory and exact parameter.

The audit uses the real CLOSED CTNL/CTRn/CTPL LEF pins and the v22 row origins. Source bit ownership is explicit in each JSON; no source pin is relabelled as a local producer. The constant-zero shifted input slice in A columns0/1 is excluded; the unused A header outputs in columns1–3 are also excluded.

| Leaf | Examined joins | Assigned pins >500 um | Rectangle lower bound >500 um | Worst assigned hop um |
| --- | ---: | ---: | ---: | ---: |
| A0 | 2992 | 598 | 598 | 804.852 |
| A1 | 1588 | 57 | 48 | 660.672 |
| A2 | 1652 | 533 | 396 | 645.582 |
| A3 | 1652 | 892 | 786 | 789.762 |
| B0 | 1644 | 880 | 828 | 778.932 |
| B1 | 1644 | 660 | 413 | 642.356 |
| B2 | 1644 | 188 | 124 | 671.502 |
| B3 | 1644 | 236 | 172 | 815.682 |

All local HRQ legs meet the 500-um geometric bound. The failures are the global YB inputs, the existing CTRn payload/header ordering, and A0's request/control copies to columns2/3. Of 4,044 violating assigned joins, 3,365 have a Manhattan lower bound greater than500 um to *any point within the destination leaf rectangle*. Pin packing alone cannot resolve those joins. This is a conservative connected-port geometry audit, not an optimized mapped dependency census; mapping may remove unused global inputs. Global capture, command/reset and peer-flag joins are not included and remain open.

The next bounded step is an exact mapped dependency census per COLUMN to remove genuinely unused interfaces. Remaining CTRn ordering and broadcast/control paths require a real die-window repin, distributed control or explicit forwarding stages with proof and cost. No unchanged route submission is justified by this diagnostic.

Reproduce from the source containing the successor:

```sh
PYTHONPATH=tools python3 tools/s81/hc_return_column_pins.py --rtl rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_return_columns.sv
```
