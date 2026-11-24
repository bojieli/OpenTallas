# KV A5t3 PV v5ne placed geometry (11-24)

**BAD.** Opened the exact placed geometry from E11 `KV-D29/private/KV-ALLFIX/kv3_pv_v5ne_1124043625` (spec stamp `1124043641`). It shows dense west-side crossings and a narrow vertical central throat. The placed scan found 40 NEED-STATION groups and 8,698 bits over 405 µm, with a longest R2R hop of 2,063.88 µm. The occupancy model estimates H3.774/V3.543 peak demand. The scan also reports 2,492 unregistered pins, ten macro-top clock entries and south pin density of 10.5/µm. The exploratory route probe timed out. Keep the geometry hold.

The existing `vport_W_N_vo` three-stage row is seated at x≈578 µm with its first stage at y≈352 µm. Its modeled source was a south-edge pin. Exact mapped fan-in comes from 159 west payload bits around y1123–1138 and 128 east-V-port high bits around y665–790, plus one reset. The longest west ingress hop is about 1,355 µm. All 288 FIRM cells are present in each of the three stages.

A draft re-seats the three existing stages at (51.84, 1006.56), (311.04, 1088.64) and (453.60, 1308.96) µm. The projected longest direct data hop across the retained per-bit graph is 365.607 µm. The estimated rectangular detours for ingress, the two internal hops and egress have maxima of 365.607, 344.088, 376.230 and 361.395 µm. These estimates include the perimeter turn along the west macro edge and the middle turn around the upper bank. The seat sketch shows center connections. Track capacity and the placed sites remain to be measured on the successor.

The current raw reset driver remains 1,194.318 µm from the draft first stage. Actual reset-driver walks from t110, t145 and t130 reach the same root in the same eleven physical relays as current bootstrap tap t43. Their modeled distances to the respective draft stage centers are about 29.7, 129.6 and 23.7 µm. Existing generation repoints FIRM reset sinks to a reachable same-role launch. Use the next exact placement to check the selected drivers, their depth and the full data and reset hop graph. The draft adds zero cycles and addresses one of the 40 measured groups.

- [Exact placed area and crossings](kv_a5t3_pv_v5ne_actual_1124.png)
- [Draft seat sketch](pv5ne_vport_W_N_vo_reseat_1124.png)
- [Per-bit projection and reset candidates](pv5ne_vport_W_N_vo_reseat_static_1124.json)
