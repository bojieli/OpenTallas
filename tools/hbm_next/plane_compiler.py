#!/usr/bin/env python3
"""HBM-NEXT-CMTP: the P-lane record compiler for the next HBM die (P = 4), on the D1 compiler / price chain.

Fork, not edit: tools/hgi_sim (d4g compiler ds_mtp_verify / ds_mtp_draft / hbm_plane_model, the D1 model) is used
UNCHANGED; this module wraps its record compile (V.compile_verify, called by the verify, the DSpark draft bodies and the
SEED) with the P = 4 rules below, and runs the re-time.  Every rule is opt-in (Knobs); with every knob at the D1
value the wrapper is the identity, which the re-time checks against the D1 / STUDY records (validation rows).

P = 4 RULES (results/arch/hbm_next_1019/cmtp/isa_rows.md, HGI-1R):
  rpl   SM remainder pass (R5): an N-row SM record on P lanes costs max(1, issues / 1.374) of the AR record, issues =
        isa_rows.best_rpl(N, P, nc, rows per SM) (idle / K-split / row-split, the cheapest; D1: ceil(N / P)).  nc = the
        record's csum chunk count (K / 32 / 8 block-dot, K / 8 BF16), rows per SM = ceil(B.m / 16).
  union MoE union grouped GEMM: a union expert with c_u routed rows costs max(1, issues(c_u) / 1.374), averaged over the
        MEASURED lane histogram (MTP-STATS: verify N = 6 decorrelated estimate; users: independent mixed workloads);
        D1: the mean P_e = 6 N / U, ceil(ceil(P_e) / P).  Draft bodies (no histogram): P_e as D1, with rpl.
  m1    x-load beats + lane-major publish (D2 model gap M1): an SM record over N rows loads N x-slots (2,048-b xw beat:
        ceil(K esz / 256) beats a row) and publishes N result rows on the unchanged result port (8 FP32 words a beat a
        SM: ceil(rows per SM / 8) beats a row).  Charged EXPOSED (no overlap credit): (N - 1) x the x beats once per
        distinct x in a layer segment (the x-slot store keeps it for the other records) + (N - 1) x the publish beats
        on every SM record.  PRICED estimate, labelled.
  coll  COLL delivery lanes L (STUDY (a): L = 5 adopted, the widest the SerDes feeds; D1 4).
  hc    HC further-row II (STUDY (d): 250 priced HCP x6 = D1; UNITS gate <= 950, target 600).
  vm    VM-resident N columns (D1 / VM grown) or as-built column swaps (STUDY (b)).

    PYTHONPATH=tools python3 tools/hbm_next/plane_compiler.py retime --out DIR [--jobs N]   (fleet: ~20-40 min)
"""
from __future__ import annotations

import argparse
import copy
import dataclasses
import datetime
import hashlib
import json
import math
import multiprocessing as mp
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(TOOLS / "hbm_next"))

import isa_rows as IR  # noqa: E402

NSM = 16                         # SMs a die (d4g; hbm_plane_model.NSM)
XW_BYTES = 256                   # 2,048-b x-write beat
RES_WORDS = 8                    # result port: 8 FP32 words a beat a SM (271-b window)
STATS = ROOT / "results/arch/hbm_mtp_next_1018/stats/summary.json"


@dataclasses.dataclass(frozen=True)
class Knobs:
    rpl: bool = False            # SM remainder-pass layouts (D1: ceil(N / P) passes)
    union_hist: bool = False     # measured lane histogram for the union experts (D1: mean P_e)
    m1: bool = False             # x-load + publish beats (D1: not priced)
    coll_lanes: int = 4          # D1 4, STUDY 5
    hc_ii: float = 250.0         # D1 HCP x6 250
    vm_grown: bool = True        # D1: N columns VM-resident (grown VM); False = as-built column swaps

    def tag(self):
        return (f"rpl{int(self.rpl)}_uh{int(self.union_hist)}_m1{int(self.m1)}_L{self.coll_lanes}_hc{int(self.hc_ii)}"
                f"_vm{'G' if self.vm_grown else 'S'}")


D1 = Knobs()
CUR = dict(knobs=D1, mode=None, hist=None)          # the job's knobs and histogram (set before the pool forks)
LOG = []


def lane_hists():
    d = json.loads(STATS.read_text())["deepseek_moe_union"]
    v = d["consecutive_verify"]["6"]["estimate_decorrelated"]["lane_hist_frac"]
    u = {int(k): x["lane_hist_frac"] for k, x in d["independent_users_mixed"].items() if isinstance(x, dict)
         and "lane_hist_frac" in x}
    return dict(verify6={int(k): float(x) for k, x in v.items()},
                users={n: {int(k): float(x) for k, x in h.items()} for n, h in u.items()},
                sha256=hashlib.sha256(STATS.read_bytes()).hexdigest())


def sm_issue_factor(N, lanes, nc, rows_sm, rpl):
    """max(1, issues / 1.374) of an N-row SM record on `lanes` lanes"""
    if N <= 1:
        return 1.0
    if rpl:
        issues = IR.best_rpl(N, lanes, nc, rows_sm)[1]
    else:
        issues = math.ceil(N / lanes)
    return max(1.0, issues / IR.HBM_LINE_RATIO)


def _sm_shape(c):
    a, b = c.desc["A"], c.desc["B"]
    K = int(a.n)
    fmt = c.param & 3
    nc = IR.csum_chunks(K, fmt)
    rows_sm = max(1, math.ceil(int(b.m) / NSM))
    esz = 1 if fmt in (1, 2) else 2
    return K, fmt, nc, rows_sm, esz


def post_sm(out, N, lanes, union, topk, kn: Knobs, hist):
    """re-price the SM records of a compile_verify programme under the P = 4 rules; returns notes"""
    from hgi_sim import ds_mtp_verify as V
    notes = dict(sm_shared=0, sm_expert=0, x_loads=0, m1_cycles=0.0, rpl_saved=0.0)
    if N <= 1 or lanes is None:
        return notes
    U = max(topk, int(round(union))) if union else topk * N
    pe = topk * N / U
    seen_x, seg = set(), None
    for c in out:
        if getattr(c, "orig_op", "") != "SM.MATVEC" or c.mtp_kind not in ("shared", "expert") or c.npos <= 1:
            continue
        key = c.layer if isinstance(c.layer, int) and c.layer < 40 else "head"
        if key != seg:
            seen_x, seg = set(), key
        K, fmt, nc, rows_sm, esz = _sm_shape(c)
        if c.mtp_kind == "shared":
            f_d1 = max(1.0, math.ceil(N / lanes) / V.HBM_RATIO)
            base = c.base_cost / f_d1
            f = sm_issue_factor(N, lanes, nc, rows_sm, kn.rpl)
            nrow = N
            notes["sm_shared"] += 1
        else:
            f_d1 = max(1.0, math.ceil(math.ceil(pe) / lanes) / V.HBM_RATIO)
            base = c.base_cost / f_d1
            if kn.union_hist and hist:
                f = sum(fr * sm_issue_factor(h, lanes, nc, rows_sm, kn.rpl) for h, fr in hist.items())
                nrow = sum(fr * h for h, fr in hist.items())
            else:
                f = sm_issue_factor(math.ceil(pe), lanes, nc, rows_sm, kn.rpl)
                nrow = pe
            notes["sm_expert"] += 1
        new = base * f
        if kn.m1:
            extra = (nrow - 1) * math.ceil(rows_sm / RES_WORDS)
            xk = (c.desc["A"].base, K)
            if xk not in seen_x:
                seen_x.add(xk)
                extra += (N - 1) * math.ceil(K * esz / XW_BYTES)
                notes["x_loads"] += 1
            notes["m1_cycles"] += extra
            new += extra
        notes["rpl_saved"] += c.base_cost - base * f
        c.base_cost = new
        c.cmtp = dict(f_d1=round(f_d1, 4), f=round(f, 4), nc=nc, rows_sm=rows_sm)
    notes["m1_cycles"] = round(notes["m1_cycles"], 1)
    notes["rpl_saved"] = round(notes["rpl_saved"], 1)
    return notes


def install():
    """wrap V.compile_verify (verify, draft bodies, seed) and M.ds_compile (to know verify / users)"""
    from hgi_sim import ds_mtp_verify as V
    from hgi_sim import hbm_plane_model as M
    if getattr(V.compile_verify, "_cmtp", False):
        return
    orig_cv, orig_dc = V.compile_verify, M.ds_compile

    def compile_verify(recs, cf, P, **kw):
        out, st = orig_cv(recs, cf, P, **kw)
        kn = CUR["knobs"]
        if kw.get("sm_mode") == "slots" and P > 1:
            mode = CUR.get("mode")
            hist = None
            if mode == "verify" and P == 6:
                hist = CUR["hist"]["verify6"]
            elif mode == "users":
                hist = CUR["hist"]["users"].get(P)
            nt = post_sm(out, P, kw.get("sm_k"), kw.get("union"), kw.get("topk", 6), kn, hist)
            st = dict(st, cmtp=nt)
        return out, st
    compile_verify._cmtp = True

    def ds_compile(N, cfg, union, kv="upper", users=False):
        prev = CUR.get("mode")
        CUR["mode"] = "users" if users else "verify"
        try:
            return orig_dc(N, cfg, union, kv, users)
        finally:
            CUR["mode"] = prev
    V.compile_verify = compile_verify
    M.ds_compile = ds_compile


def apply_knobs(kn: Knobs):
    """set the module-level knobs BEFORE the pool forks (fork context: children inherit; the fleet's Python 3.14
    default forkserver would drop them -- STUDY's process-pool bug)"""
    from hgi_sim import hbm_plane_model as M
    from hgi_sim import plan_study_price_1017 as PS
    from hgi_sim import ds_mtp_verify as V
    M.d4g_env()
    PS.VARIANTS["b"]["split"]["lanes"] = kn.coll_lanes
    M._ENV["kn"]["lanes"] = kn.coll_lanes
    M._ENV["vb"] = PS.VARIANTS["b"]
    V.HCP_II = float(kn.hc_ii)
    CUR["knobs"] = kn
    install()


def case_jobs(st, P=4, kn: Knobs = D1):
    u6, uu = st["verify_union"][6]["mean"], st["users_union"]
    sw = None if kn.vm_grown else True
    return [("ds", "AR", "verify", dict(P=1, N=1)),
            ("ds", "MTP", "verify", dict(P=P, N=6, union=u6, kv="upper", swap=sw)),
            ("ds", "draft", "draft", dict(P=P, overlap=True, union=u6)),
            ("ds", "MU", "verify", dict(P=P, N=P, union=uu.get(P, 6.0 * P), users=True, swap=sw))]


def _job(job):
    from hgi_sim import hbm_plane_model as M
    name, res = M._any(job)
    return name, res


def run_case(kn: Knobs, st, jobs_n, P=4):
    from hgi_sim import hbm_plane_model as M
    apply_knobs(kn)
    with mp.get_context("fork").Pool(jobs_n) as pool:
        res = dict(pool.imap_unordered(_job, case_jobs(st, P, kn), chunksize=1))
    mh = M._mh_ctl()
    ar = res["AR"]["cycles"]
    d = res["draft"]
    v = res["MTP"]["cycles"]
    step = v + d["draft_cycles"] + d["seed_cycles"] + mh - d["overlap"]["credit"]
    mu = res["MU"]["cycles"]
    return dict(knobs=dataclasses.asdict(kn), ar_cycles=ar, ar_tok_s=round(M.CLK / ar, 1),
                mtp=dict(verify_cycles=v, draft_cycles=d["draft_cycles"], draft_by_kind=d["draft_by_kind"],
                         seed_cycles=d["seed_cycles"], mh_ctl_cycles=round(mh, 1),
                         overlap_credit=d["overlap"]["credit"], step_cycles=round(step, 1),
                         tok_s=round(M.TAU * M.CLK / step, 1), unit_busy=res["MTP"]["unit_busy"],
                         compile=res["MTP"].get("compile")),
                mu=dict(step_cycles=mu, per_user_tok_s=round(M.CLK / mu, 1), agg_tok_s=round(P * M.CLK / mu, 1),
                        unit_busy=res["MU"]["unit_busy"], compile=res["MU"].get("compile")))


CASES = [
    ("D1 reproduction (L 4, D1 SM rule)", D1),
    ("STUDY L5 reproduction", Knobs(coll_lanes=5)),
    ("+ union histogram", Knobs(coll_lanes=5, union_hist=True)),
    ("+ M1 x-load / publish (cost)", Knobs(coll_lanes=5, union_hist=True, m1=True)),
    ("CMTP P4 headline: + rpl (K-/row-split)", Knobs(coll_lanes=5, union_hist=True, m1=True, rpl=True)),
    ("headline, HC II 600 (UNITS target)", Knobs(coll_lanes=5, union_hist=True, m1=True, rpl=True, hc_ii=600)),
    ("headline, HC II 950 (UNITS gate)", Knobs(coll_lanes=5, union_hist=True, m1=True, rpl=True, hc_ii=950)),
    ("headline, VM as built (column swaps)", Knobs(coll_lanes=5, union_hist=True, m1=True, rpl=True, vm_grown=False)),
]


def retime(a):
    from hgi_sim import hbm_plane_model as M
    st = M.load_stats(STATS)
    CUR["hist"] = lane_hists()
    out = dict(schema="opentallas.hbm_next_1019.cmtp.retime.v1", generated_utc=datetime.datetime.now(
        datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), rule=__doc__, P=4, targets=dict(
        ds_ar=1905.4, ds_mtp=3363.5, mu_agg=4365.3, mu_per_user_floor=1000.0),
        study_refs=dict(D1_P4=dict(mtp=3363.5, mu_agg=4365.3, per_user=1091.3, ar=1905.4),
                        STUDY_L5_P4=dict(mtp=3459.9, mu_agg=4481.6, per_user=1120.4, ar=1949.7)),
        hist=CUR["hist"], cases={})
    sel = [c for c in CASES if not a.only or any(s in c[0] for s in a.only.split(","))]
    for name, kn in sel:
        r = run_case(kn, st, a.jobs)
        out["cases"][name] = r
        print(f"{name:45s} AR {r['ar_tok_s']:7.1f}  MTP {r['mtp']['tok_s']:7.1f} (verify {r['mtp']['verify_cycles']:.0f}"
              f", draft {r['mtp']['draft_cycles']:.0f})  MU agg {r['mu']['agg_tok_s']:7.1f} / user "
              f"{r['mu']['per_user_tok_s']:7.1f}", flush=True)
        a.out.mkdir(parents=True, exist_ok=True)
        (a.out / "retime.json").write_text(json.dumps(out, indent=1, default=str) + "\n")
    srcs = ["tools/hbm_next/plane_compiler.py", "tools/hbm_next/isa_rows.py", "tools/hgi_sim/hbm_plane_model.py",
            "tools/hgi_sim/ds_mtp_verify.py", "tools/hgi_sim/ds_mtp_draft.py", "tools/hgi_sim/timing.py",
            "results/arch/hbm_mtp_next_1018/stats/summary.json"]
    out["sources_sha256"] = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in srcs}
    (a.out / "retime.json").write_text(json.dumps(out, indent=1, default=str) + "\n")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("retime")
    r.add_argument("--out", type=Path, required=True)
    r.add_argument("--jobs", type=int, default=4)
    r.add_argument("--only", default="")
    a = ap.parse_args()
    return retime(a)


if __name__ == "__main__":
    raise SystemExit(main())
