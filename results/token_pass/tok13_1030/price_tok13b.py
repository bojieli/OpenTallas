"""TOK-13b 2026-10-30: EXACT-exposure HBM pricing on the accepted DS native S2 model (same model/traps as TOK-8..12:
base clean 576702.4178 asserted; record R = A+B COLL (EP_S1 34/cross + coll q0 32 reduce / 17 other per cross) + IDX+31
+ SU+3 = 610734.93 cyc = 1799.79 tok/s asserted).

Difference vs TOK-12 (bounds): each plan-cycle delta is charged only to the records whose path crosses it, with the
per-record crossing map of the accepted H-DIE relay method (tools/hgi_sim/ds_relay_latency.py crossings()) and the RTL:
  SOUTH  d40h L700 18 (NE->NW: VMS SE.ccw_out + COLL ring B hcollb NE.ccw_o) / L701 21 (NW->NE: VMS SW.cw_out +
         hcollb NW.cw_o) vs Northern L4 11 (VMS NE.cw/NW.ccw + COLL ring A pr_*). COLL ring B is a 2-stop NW<->NE ring
         (tools/hbm_b2/make_wiring.py W-RING): a 1-cross COLL phase exchanges both ways at once -> max(+7,+10) = +10;
         a 2-cross op (ALL_REDUCE_SUM / GROUP_REDUCE_MCAST: reduce then multicast) crosses once each way -> +7 +10 = +17.
         VMS ring (ot_vms_rstop_static, sid SW0/SE1/NW2/NE3 -> rank ring SW-SE-NE-NW): a mirror goes cw to rank+1,+2
         and ccw to rank-1, so every VMS mirror path has <= 2 hops and AT MOST ONE hub<->hub hop (same +10 max).
         Exact charge per COLL record: +10 (1-cross) / +17 (2-cross); TOK-12 pair17 per cross = +17 / +34 (bound).
  EP     d41c L720 17 (hub->spb0 tx 632 b) / L722+L723 19 (rx 615 b): parallel to EP_S1 root<->vsN0 L200/L201 19/19
         (same 632/615 b flit buses, still in d41c), which the record already charges (+17/+17 per cross over the
         2-flop bound). Per cross max(tx) 17 <= 19, max(rx) 19 = 19 -> +0 (no credit taken for tx -2).
  SM     d41c L721 sm3->hub request 7 = L123; sibling request lanes L120 7 / L121 8 / L122 8 -> max 8 unchanged -> +0.
         d38s L28/L28m 28->29 (+1, SM per TOK-12) kept.
  SFU    only SU records whose template uses the SFU (r.sut['sfu'] != 0: q_norm.rs, kv_norm.rs, attend.exp_sum,
         attend.den, router_act, swiglu x40 + engram 6 = 246 records; crossings() SFU_CORE x2). FUSED records do NOT
         use the SFU core: FUSED.HC_* = HC_CORE/HC_ENG (tnode term below), FUSED.QDQ = 0.
         Per-record SFU critical path (ot_hgi_sfu_core_split2_sp2: VM via the SU LG pair tap, bridge read return
         TAP_RR + 2(LG_PATH+1), write TAP_WR + (LG_PATH+1); lanes are register-direct to the engine):
           tap->ctl read response + ctl->lane + lane->ctl + ctl->tap write  (request leg and hub->ctl compiler control
           are issued ahead by the static calendar)  vs the alternative lane->hub kv gather path; each leg = plan cycles
           - 2 (record = 2-flop bound for the then-unplanned SFU pairs; planned L5/L23/L81/L184/L185 vs record cycles).
  TNODE  Codex N1: FUSED.HC_PRE_NORM +48 / HC_POST +32 per record (source-derived, unchanged).
  IDX    L1 IDX chain 1 + 2 + 6 = 9 replaces record 31 (serial per IDX record, unchanged method).
Run at repo root: PYTHONPATH=src python3 price_tok13.py OUT.json"""
import sys, json
sys.path[:0] = ['tools', 'tools/throughput']
import accepted_cost as AC
from hgi_sim import timing as T
from hgi_sim import ds_native_timing as DT
from collections import Counter
res = AC.ROOT / 'results/arch/hgi_sim_20261010/g25_proof'
d, recs = DT.load(res / 'ds_rank0_program.json'); recs = T.rebuild_waits(recs)
rg = {}
for x in json.loads((res / 'ds_full.json').read_text())['results']:
    for s_ in x.get('row_gather') or []: rg[x['layer']] = s_
DT.apply_dyn_counts(recs, rg); cf = DT.NativeCost(d['ops'], recs, row_gather=rg)
CROSS2 = ("ALL_REDUCE_SUM", "GROUP_REDUCE_MCAST")
def cross(r): return 2 if r.op in CROSS2 else 1
REDUCE_OPS = CROSS2 + ("TOPK_MERGE", "ARGMAX_MERGE")
def is_sfu(r): return r.unit == "SU" and isinstance(r.sut, dict) and r.sut.get("sfu", 0) != 0
TN = {"HC_PRE_NORM": 48, "HC_POST": 32}
def run(ab=True, extra=None, south=0, sfu=0, tnode=False, fused_all=0, coll_once=0):
    def g(r, dyn, L):
        c = cf(r, dyn, L); t = c[0]
        if r.unit == "COLL" and ab:
            t += 34 * cross(r) + (32 if r.op in REDUCE_OPS else 17) * cross(r)
        if r.unit == "COLL": t += (south * cross(r) if south != "exact" else (10 if cross(r) == 1 else 17)) + coll_once
        if extra: t += extra.get(r.unit, 0)
        if is_sfu(r): t += sfu
        if r.unit == "FUSED": t += fused_all
        if tnode and r.unit == "FUSED": t += TN.get(r.op, 0)
        return (t, c[1], c[2])
    return T.schedule(recs, DT.POS, 'S2', cost_fn=g)['total_cycles']
base = run(ab=False)
assert abs(base - 576702.4178) < 0.1, base   # model trap guard (TOK-HBM-11 README)
REC = {"IDX": 31, "SU": 3}
rec = run(extra=REC)
assert abs(rec - 610734.931155155) < 0.1, rec
tok = lambda t: round(1906 * base / t, 2)
out = dict(basis=__doc__, base_cycles=base, record_cycles=rec, record_tok_s=tok(rec),
           records_per_unit=dict(Counter(r.unit for r in recs)),
           sfu_records=dict(Counter((r.tag) for r in recs if is_sfu(r))), n_sfu=sum(map(is_sfu, recs)),
           coll_ops=dict(Counter(r.op for r in recs if r.unit == "COLL")), rows=[])
def case(name, extra=None, **kw):
    e = dict(REC); e.update(extra or {})
    t = run(extra=e, **kw)
    row = dict(case=name, extra=e, kw=kw, cycles=round(t, 2), tok_s=tok(t),
               pct_vs_record=round(100 * (rec / t - 1), 3), pct_vs_1812_4=round(100 * (tok(t) / 1812.4 - 1), 3),
               above_floor_1721_8=tok(t) >= 1721.8)
    out["rows"].append(row); print(json.dumps(row), flush=True)
    return t
# TOK-13b (COORD 16:0x): L1 not buildable (HBM-LOC-1 PARKED 15:57) -> plan of record = d41c + V-A lanes.
# SFU exposure per SU.sfu record = 2*(max tap - 2) + 2*(max ctl<->lane - 2) (tap read+write, broadcast + gather legs,
# minus the 2-flop bound); hub->ctl assumed issued ahead (bound row adds it).
def sfu(tap, lane): return 2 * (tap - 2) + 2 * (lane - 2)
V = {}
# V-A hop chains (HBM-LOC-1 README S0 col, from DIE-HBM-37): taps su11 42 / su31 41 / su20 <=41; ctl<->b112 46, b110 44, b111 19
V["VA"] = (sfu(42, 46), 80)
# (a) su31 tap fix to a 27-cyc planned lane each way: su11 42 stays the max tap -> no gain
V["a_su31fix27"] = (sfu(42, 46), 80)
# (a') su31 27 + su11 22 planned (both far taps)
V["a2_su31_27_su11_22"] = (sfu(27, 46), 80)
# (b) core re-home, no partition move (d41c geometry, direct ceil(gap/405)+2 on new planned lanes):
#     SFU ctl+opstores -> b111 (5-lane strip): lanes b110 25 / b112 38 / b113 13; taps su11 32, su20 2, su31 21, su00 13; hub 10
#     IDX scorer glue b100 -> b102 with the gc leaves: hub->glue 2->13 (+11), glue->gc 0 (was 47), b103->b101 32 V-A kept
V["b_rehome_ctl_b111_idx_b102"] = (sfu(32, 38), 11 + 32 + 1)
# (b) alt: ctl -> b112 (other 5-lane strip): lanes b110 14 / b111 38 / b113 28; taps su11 2, su20 33, su31 15, su00 23
V["b_alt_ctl_b112"] = (sfu(33, 38), 11 + 32 + 1)
# (b) alt IDX: gc leaves into b100 next to the glue (+ b103 tail stays): IDX = b103->b101 32 + 1
V["b_alt_idx_gc_to_b100"] = (sfu(32, 38), 32 + 1)
# sensitivity: no core move, plan direct lanes for the existing pairs (ctl b113): lanes 37, taps 32
V["sens_C0_direct_lanes"] = (sfu(32, 37), 30 + 30 + 1)
# (a)+(b)
V["ab_rehome_plus_su11fix"] = (sfu(21, 38), 11 + 32 + 1)
out["variants"] = {k: dict(sfu=v[0], idx=v[1]) for k, v in V.items()}
case("w_sfu_plus1", sfu=1)
case("w_idx_plus1", {"IDX": 1})
for k, (sf, ix) in V.items():
    case("POR_d41c_%s_tnode" % k, {"SM": 1, "IDX": ix}, south="exact", sfu=sf, tnode=True)
case("POR_d41c_VA_notnode", {"SM": 1, "IDX": 80}, south="exact", sfu=V["VA"][0])
case("POR_d41c_VA_tnode_plus_hubctl28", {"SM": 1, "IDX": 80}, south="exact", sfu=V["VA"][0] + 28, tnode=True)
case("POR_d41c_VA_tnode_south_pair17_bound", {"SM": 1, "IDX": 80}, south=17, sfu=V["VA"][0], tnode=True)
json.dump(out, open(sys.argv[1], "w"), indent=1)
