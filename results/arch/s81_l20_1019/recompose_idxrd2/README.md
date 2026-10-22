# L20 idxrd2 integer recomposition (owner 12:42: 1130 -> 1070 ROM slots a die)

`python3 tools/uarch_model.py --s81-l20-idxrd2-recompose --out results/arch/s81_l20_1019/recompose_idxrd2/recompose.json`
Slot law of record (dv_price: TP4 stages = ceil(89 x 1220 / slots)), census of record (440 = 388 layer + 52 non-layer;
MU + 8 duplicated groups, a copy = ceil(layer dies / 40)), dv_price rate on the current MU3 geometry with only rom_slots changed.

| slots | TP x stages (ranks 4) | layer dies | SU dies | MU dup | MU dies | AR tok/s (record) | MTP tok/s (record) |
|---|---|---|---|---|---|---|---|
| 1130 | 4 x 97 | 388 | 440 | 8 x 10 = 80 | 520 | 1,217.2 | 3,622.2 |
| 1070 | 4 x 102 | 408 | 460 | 8 x 11 = 88 | **548 (+28, +5.38%)** | 1,210.0 (-0.59%) | 3,606.9 (-0.42%) |

MU users 47 held (II = worst group occupancy; T only grows). Static energy/token +6.0% (dies/rate); dynamic unchanged.
Sensitivity: if the 52 non-layer dies are slot-bound too, MU = 552. Grade: modelled; no fit/route claim.
