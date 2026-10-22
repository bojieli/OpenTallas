# TOKSIM-QW/LINK: measured inter-die and collective cycles, Qwen3-8B, 10-19

Release RTL: origin/claude/qw-gen3-1019. The brief names 221cf90b7; the head checked is e9879afda. The only change between them is to tools/qwen_split/dv_case.py.
All runs used Verilator 5.050 on the fleet. Clock 1.2 GHz. Machine record: record.json.

| stage | grade | measured cycles | verdict |
|---|---|---|---|
| 1u compute<->KV D2D pair, per layer | REL (extracted, no rerun; 34/34 sources = gen3) | C2K 63, K2C 62, KVN 20, roundtrip 1840, KV service 1779 (stand-in), X 7, period 6842/layer (PHY9: 6850) | 35 layers bit-exact; 6 pair mutants + old C/K TXDP FAIL |
| 4u OVL D2D pair, F16 frame, codec2 | NEWEST (OVL is not in the release RTL) | H 4,026,800 / frame; users 16/15/8/7 tok -> 251,675 / 268,453 / 503,350 / 575,257 cyc/token; aggregate 87,539 cyc/token = 13,708.2 tok/s | PASS: 63,098 C->K + 57,783 K->C frames bit-exact; as-built one-playhead, collide, slot and user mutants FAIL; codec1 and cyclic-seq variants give the same numbers |
| 4u MU context real link (release serial MU image) | REL (re-run on gen3 sources) | slot->HOST 2, HOST->compute 16, slot->compute 18, decode +1, token-period spacing 249,600 | PASS; mut1..5 FAIL |
| TP8 all-reduce, 8 dies | REL (30/30 RTL = gen3; dh2 GEN lanes) | AR256 E 286 / span 797 / first-in->first-out 541; argmax E 438; LS 378 / LU 53; token 36x2x286 = 20,592 (+438 argmax = 21,030); 4u window span 38,138, E 286 (= user alone) | 12/12 verdicts OK |

OVL segment slots (cycles from the segment anchor, ovl_pass.json):
- req: C_tx -1..41, K_rx 19..59
- rsp: K_tx 1771..1806, C_rx 1805..1840
- tok_tx: C_tx 1..31, K_rx 14..46
- tok_rx: K_tx 2..256, C_rx 18..271

Stand-ins (details in record.json):
- 1u pair: the KV side is the test stand-in qkd_kvs_attn_kvs14c (LAND=0), not the GEN9 die.
- PHY is modelled in every stage.
- 1u pair: it uses diagnostic per-layer calendars, and host records are tied 0.
- The compute seam comes from the dv2f18dh2 GEN. The gen3 dv2f19g3 GEN has not finished.
- OVL: producers and consumers are modelled.
- TP8: the SerDes is 339 modelled cycles, and O_meas is 0.

Pending:
- A 4u REL link rate on the release serial MU calendar. No paired 4-user TB exists for it.
- Re-runs on the GEN9 KV die and on the gen3 seam and lanes, once those GENs exist.
