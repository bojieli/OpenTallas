"""TOK-HBM-3 2026-11-03: tok/s price of HBM plan events d44t (DIE-HBM-59 FT S0 re-site: 34 lanes +1..+4) and d44x
(= d44t + R8 bus groups L168_word/L168m_word: L14/L167 (+m) padded 8 -> 10), on the TOK-13d model unchanged
(DS native S2, base 576702.4178 + record 610734.93 asserted; needs a FULL results/arch + results/rtl tree: a sparse
tree silently changes the base to 557291.4). Reference row = TOK-13d A1 (1677.0 tok/s, the accepted HBM ceiling).

Charge per changed lane = increase of the MAX leg of its model term (every record of the term sees the slowest leg):
  SFU   L730/L730m ctl(b113)->lane(b112) 42->44 is the max ctl->lane leg: +2 on one leg of 2(tap-2)+2(lane-2) -> +2;
        L731 ctl->su20 17->18 below the max tap (su11) -> +0 (bound case charges +1).
  IDX   L6/L6b/L6c (+m) hub->b100 R8 group 8->9: +1 (serial IDX chain); L12m/L12ms root->NE_hub idx link 13->14 NE only
        (NW L12 stays 13): +1 (max of the two hubs); d44x L14 (b000->b001 scorer -> gc leaves) 8->10: +2 bound.
  SM    L28/L28m hub->sm0 29->30 = max hub->SM leg: +1 (L100 sm3 7->8 below max -> +0).
  COLL  L36/L36m hub->su00 14->18 (hb_coll del_flit/obase/valid + cic inj) becomes the max hub->SU delivery leg
        (L0 su01 14): +4 per COLL record.
  FUSED L36 also carries hc lg_rq/lg_wq -> hc_NW0 c_rq/c_wq: +4 per FUSED record (bound: every FUSED record);
        L168 (+ d44x L14/L167) hcb chain b000->b001 +2: bound +2 more; L181 su31->hub 5->6 below the 8-cycle max -> +0.
  status/fault/obs (L117 L138 L206m L735 L736 L202 L203 cfg) -> +0 (off the per-token path; L202/L203 col_idx.prm
        is boot-time config).
Run at a full repo root: PYTHONPATH=src python3 price_d44t.py OUT.json"""
import sys, json
sys.path[:0] = ['tools', 'tools/throughput']
import accepted_cost as AC
from hgi_sim import timing as T
from hgi_sim import ds_native_timing as DT
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
def run(ab=True, extra=None, south=0, sfu=0, tnode=False):
    def g(r, dyn, L):
        c = cf(r, dyn, L); t = c[0]
        if r.unit == "COLL" and ab:
            t += 34 * cross(r) + (32 if r.op in REDUCE_OPS else 17) * cross(r)
        if r.unit == "COLL": t += (south * cross(r) if south != "exact" else (10 if cross(r) == 1 else 17))
        if extra: t += extra.get(r.unit, 0)
        if is_sfu(r): t += sfu
        if tnode and r.unit == "FUSED": t += TN.get(r.op, 0)
        return (t, c[1], c[2])
    return T.schedule(recs, DT.POS, 'S2', cost_fn=g)['total_cycles']
base = run(ab=False)
assert abs(base - 576702.4178) < 0.1, base
rec = run(extra={"IDX": 31, "SU": 3})
assert abs(rec - 610734.931155155) < 0.1, rec
tok = lambda t: round(1906 * base / t, 2)
def sfu(tap, lane): return 2 * (tap - 2) + 2 * (lane - 2)
A1 = dict(extra={"IDX": 38, "SM": 1}, sfu=sfu(42, 46))         # TOK-13d A1 row (accepted ~1677)
CASES = {
    "A1_ref_d44s": dict(dIDX=0, dSM=0, dSFU=0, dCOLL=0, dFUSED=0),
    "d44t_expected": dict(dIDX=2, dSM=1, dSFU=2, dCOLL=4, dFUSED=4),
    "d44t_bound": dict(dIDX=2, dSM=1, dSFU=3, dCOLL=4, dFUSED=6),
    "d44x_expected": dict(dIDX=2, dSM=1, dSFU=2, dCOLL=4, dFUSED=4),
    "d44x_bound": dict(dIDX=4, dSM=1, dSFU=3, dCOLL=4, dFUSED=6),
}
out = dict(basis=__doc__, base_cycles=base, record_cycles=rec, record_tok_s=tok(rec), rows=[])
ref = None
for name, c in CASES.items():
    e = {"SU": 3, "IDX": A1["extra"]["IDX"] + c["dIDX"], "SM": A1["extra"]["SM"] + c["dSM"],
         "COLL": c["dCOLL"], "FUSED": c["dFUSED"]}
    t = run(extra=e, south="exact", sfu=A1["sfu"] + c["dSFU"], tnode=True)
    ref = ref or t
    row = dict(case=name, deltas=c, extra=e, sfu=A1["sfu"] + c["dSFU"], cycles=round(t, 2), tok_s=tok(t),
               d_cycles_vs_ref=round(t - ref, 2), pct_vs_ref=round(100 * (ref / t - 1), 3))
    out["rows"].append(row); print(json.dumps(row), flush=True)
json.dump(out, open(sys.argv[1], "w"), indent=1)
