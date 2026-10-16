# Source-bound SU/HC home inventory, candidate only

Reproduce with `python3 tools/s81/suhc_homes_inventory.py --model /tmp/sdiehub/model.json.gz --out DIR` and then `python3 tools/s81/suhc_compact_leaf_screen.py --inventory DIR/inventory.json`. The model SHA and source commit are embedded in the archived inventory. Full per-pin XY manifests are generated alongside it; existing copies live at `/home/ubuntu/artifacts/s81-suhc-homes-0811`.

Inventory includes 90 actual historical real LEF/insertion views, the 69 current die incident buses, all v23 SU/HC slots and CTH row geometry. Endpoint directions in the die model are not authoritative; use actual RTL and LEF directions. The current die SU wrapper instantiates the flat SU, so hierarchical child counts are a constructive design input, not proof of current die elaboration.

The three SU placements contain 711 individual source-reviewed hierarchical arithmetic leaves, each bound to its real view, R0 outline, clock and pin manifest. Every pair was checked for overlap. Existing real-leaf area is 18.6891 mm², with explicit pinNS/SMLu65/SMDu65 and other variants. At conservative 43.2 µm streets, outlines are 4104 × 8901.36, 5184 × 7339.68 and 6048 × 6393.60 µm. These shelf placements provide conservative starting homes, not the final optimized grouping. RX, glue and relays remain outside these counts; do not present their envelopes as complete new SU shapes.

The v23 HC sublayout uses 790.56 µm while individual CTH reservations retain 758.16 µm, and a newer candidate has literal 835.92 µm. A folded HC must first select its exact native child set and make the parent/child dimensions consistent. Scaling a legacy HC rectangle cannot establish that.

Next: optimize complete incident pin graph inside the owner’s coherent hub layout, allocate real relay masters/clock roots, prove cuts ≤ 0.60 and the exact fixed-cycle calendar, then regenerate realviews/full native trial with TT setup, FF hold and DRC 0. Owner reviews the Explorer candidate before adoption. No timing, native completeness, die shape grant or throughput claim is made by this study.
