# HEAD rank merge SIMULATED on the generated die top (TOK-ALL-16, Tue Oct 27 05:13:59 PM PDT 2026)

Settles the TOK-ALL-15 open item: rank_merge was a composed row (model 361; TOK-15 lane re-derivation >= 373, UNCHECKED).
Here it runs in RTL from the measured spine result at the ctl b_i pin to the final 4-rank argmax.

Vehicle: the TOK-15 bench (results/token_pass/head_die_spine_1027). The generated wrappers are byte-identical to TOK-15
(gen_sha256.txt == TOK-15 hashes; tools/die_plan/gen.py rtl of main die_plan s81_head @542a4f321).
What changed vs TOK-15:
- ot_s81hd_mesh_ep_core (mesh0S / mesh7S / mesh7N) is now REAL (it was stubbed). It contains best64 decode, 2 x
  dsfd_coll_lane_w_safe8_ntf (link_ep CRC/replay + gearbox), the copy FIFOs and beat_tx.
- ot_s81hd_serdes_link (all 12) is now REAL: ot_pdie_serdes = KP4 RS(544,514) enc/dec + rate matcher. Only the analog PMA
  is behavioural.
- The ctl driver (src/ctl_core_rm.sv) is the TOK-15 driver plus:
  - at the b_i result edge R it registers the own BEST record (edge R+1);
  - three REAL ot_s81hd_best64_tx on a_tx_o / b7_tx_o / n_tx_o;
  - three REAL ot_s81hd_mesh64_rx;
  - the REAL ot_s81hd_rank_merge_hsf0 (own slot + 3 peers x 2 copies, 2-level registered compare, tag/copy/NaN checks).
- Ring by pad loopback (src/tb_die_rm.sv). One die stands for its identical neighbours:
  - ES0/ES1 pads -> WS0/WS1 = the west peer's east transmission;
  - WS -> ES = the east peer;
  - EN -> EN = the diagonal peer.
  Each tx lane therefore carries that peer's record, the golden per-rank argmax of the ctx1048576_head.npz logits:
  - rank1 33100/41345fd2 (east, a_tx);
  - rank3 103774/414142e8 (west, b7_tx);
  - rank2 93642/41363460 (diagonal, n_tx).
  Every peer transmits at the own rank's static edge.
- Channel: standalone ot_pdie_serdes coll tx -> far coll rx = 79 cycles at K 0 (logs/serdes_lat.log; K 100 -> 179).
  K = 172 extra PMA cycles makes serdes leaf -> serdes leaf = D = 251, the model's tp_mesh hop (HOP_D, full-KP4 cable).

## Result (logs/run16_pos.log, 2 positions)
- Spine is unchanged: GO -> b_i 8,691, 21946/4173a558.
- **b_i result edge -> rank-merge valid = 419 cycles**, final 21946/4173a558 = golden global argmax. pos id is correct;
  0 tag/copy/NaN/overwrite faults, 0 endpoint/codec faults.
- Copy arrivals after R:

  | Peer | Copy A | Copy B |
  |---|---|---|
  | diagonal (EN) | +307 | +328 |
  | east (b7_rx) | +390/391 | +411/412 |
  | west (a_rx) | +391 | +412 |

  The merge fires 7 edges after the last copy: frame -> pin flop -> hold -> landed -> fire -> 4 merge edges.
- Comparison with the plan lane sums for the same peers:
  - west path: m7S_tx 46 + ES1_d 12 + D 251 + WS1_u 13 + m0S_rx 51 = 373 -> copy B lands at 412, +39;
  - east path: m0S_tx 49 + WS1_d 12 + D + ES1_u 13 + m7S_rx 47 = 372 -> lands at 411/412;
  - diagonal path: 268 -> lands at 307, +39.
  The extra ~39 edges per hop are the endpoint and codec internals that no model row carried. They are:
  - own BEST issue: 1 edge;
  - best64 2 beats;
  - mesh best64 decode;
  - lane adapter + link_ep/gearbox, tx and rx;
  - landed/slot/decision 3 edges;
  - beat_tx 2 beats + rx.

## Controls
- DROP_N (the diagonal peer never transmits): no merge, RANK_MERGE FAIL. CAUGHT.
- Peer wins, east 7f000000:
  - with the golden expectation, FAIL. CAUGHT;
  - with the expectation set to that peer, PASS: 33100/7f000000 at the same 419.
- Peer wins, west 7f000001, expectation set to that peer: PASS, 103774/7f000001 at 419. This proves that peer records
  really cross the RTL ring and merge.

## Per token
xb_ingress 162 + die spine 8,691 + rank_merge 419 + mtp/token 6 + out hop 4 = **9,282 cycles (7.735 us)**.
The calendar window is 10,357, so the slack is 1,075.
- Composed, not simulated: xb_ingress, mtp_seq_token_former, out_hop_issue, and the ctl-internal hsf0 issue/final
  formation (the driver issues 1 edge after b_i).
- D = 251 is taken as the serdes-leaf-to-serdes-leaf hop. If D already contained the lane endpoint cycles, the measured
  path would count them twice. The number is linear in D: rank_merge = 168 + D.
- Plesiochronous clock offset is not modelled: rck = ck.

## Model rows to correct (results/uarch/s81_head_die.json, tools/s81_head_die_model.py)
- rank_merge 361 -> 419 (+58). The model's 251+49+51+10 omits:
  - the copy-B lane via the ES1/WS1 coll stations;
  - the mesh endpoint/codec ~39 per hop;
  - the 7-edge merge.
- x_fill_and_return + bundle + tile_merge_pipe + spine_merge_fire = 8,663 -> measured 8,691 (+28, TOK-15).
- Total 9,186 -> 9,282 (vs_calendar -1,171 -> -1,075).

Raw: intel1:/srv/opentallas-scratch2/claude/tok16-head-rm (obj16, obj_sl*, run16_*.log).
Build: ot-run on intel1, 811 s, 8.0 GB, Verilator 5.050. Run: 18.8 s, 32 MB.
