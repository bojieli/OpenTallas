# CB16 structural source/model continuation (not gate ready)

Original fullk4ccb8574e gate failed ODB-0359 moving FIRM soft-ring cells. New reserved-bay legal region hook lets GPL own ring cell positions with runtime row-capacity<=35% guard; DPL legality checks retained.

Initial actual geometry review found8 hard station overlaps in old138-bay plan and inherited4.32um station origins. Binding43.2 required. New qc_fullm_kit.py applies43.2 to every hard origin/reach repair and rebuilds exact hard occupancy AFTER repairs (old F occupancy was stale). Same3067.2x5486.4 outline/16.828mm2; hard per-bit single-cycle max398.9um,0>405. RTL exact modulo topmodule rename (normalized SHA matches original) with zero added data/reset edges.

NOT GATE READY: previous bank data/vld multi-cycle setup2/hold3 masks must not carry into successor. Current separated-half bank far corners1136.2/1002.2um are not ordinary405um safe. Complete all-bit hard/soft endpoint model has0 unknown writer bits, main138halves/69banks/5soft edges, fallback108halves/54banks. Joint physical bank placement solver is next. Actual mapped FF inventory:653 scalar reset sites; rings reader693/695 and writer2286/2294FF. Need bank/hard/control all-hop proof405, no macro/bay overlaps, exact reset copy site proof and no data masks before gate.

A0 children remain stand-ins in this diagnostic parent lineage. Qualified A0 views and full-parent functional lockstep remain prerequisites for release. No REVIEW/submission/route approval.
