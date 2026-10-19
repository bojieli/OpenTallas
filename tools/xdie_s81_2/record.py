#!/usr/bin/env python3
"""XDIE-S81-2 (10-19; copy of tools/xdie_s81/record.py, TOKEN-XDIE-S81): measured cross-die collective cycles from
tb_xdie_s81_2 LAND lines (current die RTL G8R2 + current lane tile + the die's lane legs) + the S81 part of the token
composition, and the MU-S81 multi-user summary (--mu NAME=GOLDEN_DIR:RUN_LOG, repeatable): per user E per collective,
the user's stage-hop h message (80 tagged beats per endpoint on its copy A / B), shift invariance (every user's E equals
user 0's) and user 0 against the single-user run.

    python3 tools/xdie_s81/record.py --golden G/golden.json --run RUN/run.log [--run ...] --name CFG --out record.json
          [--dag results/arch/token_path_20261009/ds_rom.json] [--stages 97]

Per collective instance (from the LAND lines: inst src dst k issue land deadline):
  L_first  max over streams (src -> dst) of first land - first issue  (one-crossing latency, first word)
  E_meas   last land over all streams - first issue over all streams  (the collective, issue of its first word on any
           die to its last word landed on any die: what a consumer waiting for the whole result sees with no overlap)
  E_last   max over streams of last land - last issue                 (dispatcher form: producer's last-word issue to
           the consumer's last-word land)
  drain    (last land - first land) / (beats - 1) per stream, max      (cycles per beat at the lane rate)
  AR       E = E_RS + FOLD + E_AG; FOLD = the owner's die-internal fold (TOKEN-PASS-S81 die run; 0 until measured)
Two repetitions must give identical cycles (static schedule determinism).

Composition (S81, AR workload): T_xdie = sum_x n_x * max(0, E_meas(x) - O(x)), O(x) = the token DAG's overlap window
for the node: 0 on the critical path, (cycles + slack) off it (DAG = the composition basis the token page uses; the S81
DV compiler's static schedule replaces it when TOKEN-PASS-S81 publishes per-layer issue cycles).  delta = T_xdie -
the DAG's priced cycles of the same nodes (exposed part only) -> tok/s change against the p4l price of record.
Scaling: TP group = 4 = N (no scaling for the TP collectives); stage hops are point-to-point and identical per hop
(n_hop x E_hop); argmax is the TP4 merge on the head dies.
"""
from __future__ import annotations

import argparse
import collections
import json
import math
import re
from pathlib import Path

# DAG op -> vehicle collective (n per token from the DAG; the switch crossing applies to every one of them)
DAG_MAP = {
    "attn.a_allgather": "a_allgather",
    "ffn.router_allgather": "router_allgather",          # expert DISPATCH: router scores gathered for top-6
    "attn.out_allreduce": "allreduce_20480",
    "ffn.combine_allreduce": "allreduce_20480",          # expert COMBINE
    "attn.idx.topk_merge": "idx_topk_merge",
    "attn.rows_allgather": "rows_allgather",
    "attn.cand.merge": "cand_merge",
    "eng.rows_allgather": "eng_rows_allgather",
    "head.argmax_merge": "argmax_merge",
    "substage_hop0": "stage_hop", "substage_hop1": "stage_hop", "head.hop": "stage_hop",
}
F_CLK = 1.2e9
OFFCHIP = 453            # modelled cycles per crossing (2 x PMA model + channel = 377.5 ns at 1.2 GHz)
# on-die leg (PRICED, p4l plan; outside the vehicle, whose boundary is the end slice's inward port): the farthest
# slice -> end slice and end slice -> owning slice, each worst_slice_to_edge 11,673 um = 29 stations of 405 um on
# half-cycle relays (14.5 cyc) + 7 landed ring links (1 + E 4.5 each: 38.5) + 7 ring stops x 2 edges (14) = 67 cycles
ONDIE = 134              # per crossing (both ends)
CROSSINGS = {"allreduce_20480": 2}   # RS + AG; every other exchange is one crossing
MTP_EXTRA = {"hop_in": "stage_hop", "wave.hop": "stage_hop"}


def token_compose_terms(coll, dags, commit_note):
    """token_compose override block (results/arch/token_path_1018/README.md): one term per DAG coll/hop slot the vehicle
    measured; E split into the measured-current-RTL part and the modelled off-chip part (453 cyc a crossing); O by the
    composition's S81 rule (critical -> 0, off the critical path -> O = E)."""
    terms = []
    for wl, path in dags.items():
        dag = json.loads(Path(path).read_text())
        gk = {g["id"]: g["kind"] for g in dag["groups"]}
        for nd in dag["nodes"]:
            if nd.get("cls") not in ("coll", "hop"):
                continue
            x = DAG_MAP.get(nd["op"]) or (MTP_EXTRA.get(nd["op"]) if wl == "mtp" else None)
            mult = 1
            if nd["op"] == "unplaced_hops":
                x, mult = "stage_hop", 62
            if not x or x not in coll or coll[x]["E_meas"] is None:
                continue
            k = gk.get(nd.get("group"))
            L = k if k in ("head", "embed", "hops", "draft", "wave", "accept") else (
                f"L{nd['layer']}" if isinstance(nd.get("layer"), int) and nd["layer"] >= 0 else (k or "other"))
            E = mult * coll[x]["E_meas"]
            mod = mult * OFFCHIP * CROSSINGS.get(x, 1)
            ond = mult * ONDIE * CROSSINGS.get(x, 1)
            crit = bool(nd.get("critical"))
            terms.append(dict(design="ds_rom", workload=wl, slot=f"{L}.xdie.{nd['id']}",
                              E=[dict(grade="measured-current-RTL", E=float(E - mod),
                                      note=f"{x}: current S81 die RTL (G8R2 p4m: rstop + lep + lane legs) + lane tiles (HF-3) + PHY digital (KP4) co-sim, tb_xdie_s81_2 {commit_note}"),
                                 dict(grade="modelled-PHY", E=float(mod),
                                      note="PMA + Tomahawk-Ultra + 2 x 3 m twinax: 377.6 ns budget a crossing"),
                                 dict(grade="priced", E=float(ond),
                                      note="on-die leg farthest slice <-> end slice, both ends (p4l plan, 67 cyc an end)")],
                              O=0.0 if crit else float(E + ond),
                              O_source="token-path DAG solve: critical -> O 0; off the critical path (slack %.1f) -> O = E"
                                       % float(nd.get("slack") or 0.0),
                              pointer=f"collectives.{x}.E_meas" + (f" x {mult}" if mult > 1 else "")))
    return terms


def parse(run):
    rows = []
    for ln in Path(run).read_text(errors="replace").splitlines():
        if ln.startswith("LAND "):
            rows.append(tuple(int(x) for x in ln.split()[1:]))
    stats = next((ln for ln in Path(run).read_text(errors="replace").splitlines() if ln.startswith("XDIE_STATS")), "")
    verdict = next((ln for ln in Path(run).read_text(errors="replace").splitlines()
                    if ln.startswith("PASS xdie_s81") or ln.startswith("FAIL xdie_s81")), "NO VERDICT")
    return rows, stats, verdict


def inst_metrics(rows):
    st = collections.defaultdict(list)
    for inst, s, d, k, iss, land, dl in rows:
        st[(s, d)].append((k, iss, land, dl))
    fi = min(v[0][1] for v in st.values()); ll = max(v[-1][2] for v in st.values())
    lf = max(v[0][2] - v[0][1] for v in st.values())
    el = max(v[-1][2] - v[-1][1] for v in st.values())
    dr = max(((v[-1][2] - v[0][2]) / (len(v) - 1)) if len(v) > 1 else 0.0 for v in st.values())
    lat_by = {f"{s}->{d}": v[0][2] - v[0][1] for (s, d), v in st.items()}
    slack = [dl - land for v in st.values() for (_, _, land, dl) in v if dl]
    return dict(streams=len(st), beats=sum(len(v) for v in st.values()), first_issue=fi, last_land=ll,
                L_first=lf, E_meas=ll - fi, E_last=el, drain_per_beat=round(dr, 3),
                L_first_min=min(lat_by.values()), min_deadline_slack=min(slack) if slack else None)


def mu_summary(g, run, single):
    """MU run: per user, E_meas per collective and of its h message; invariance against user 0 and the single-user run."""
    rows, stats, verdict = parse(run)
    ln = Path(run).read_text(errors="replace").splitlines()
    by = collections.defaultdict(list)
    for r in rows:
        by[r[0]].append(r)
    users = collections.OrderedDict()
    for ins in g["instances"]:
        u = ins.get("user")
        if u is None:
            continue
        if ins["kind"] == "AR":
            rs = inst_metrics(by[ins["inst"]]) if by[ins["inst"]] else None
            ag = inst_metrics(by[ins["inst_ag"]]) if by[ins["inst_ag"]] else None
            E = (rs["E_meas"] + ag["E_meas"]) if rs and ag else None
            first = rs["first_issue"] if rs else None
        else:
            m = inst_metrics(by[ins["inst"]]) if by[ins["inst"]] else None
            E = m["E_meas"] if m else None
            first = m["first_issue"] if m else None
        uu = users.setdefault(str(u), dict(copy_h=None, start=None, E={}))
        uu["E"][ins["name"]] = E
        if uu["start"] is None:
            uu["start"] = first
        if ins["kind"] == "MUH":
            uu["copy_h"] = ins["copy"]; uu["pos"] = ins["pos"]
            uu["h"] = inst_metrics(by[ins["inst"]]) if by[ins["inst"]] else None
    u0 = users.get("0", {}).get("E", {})
    inv = {u: all(v.get("E", {}).get(n) == u0.get(n) for n in u0) for u, v in users.items()}
    vs_single = {n: dict(user0=u0.get(n), single=(single.get(n) or {}).get("E_meas")) for n in u0 if n in single}
    return dict(golden_mu=g.get("mu"), verdict=verdict, stats=stats,
                link=next((x for x in ln if x.startswith("XDIE_LINK")), ""),
                tags=next((x for x in ln if x.startswith("XDIE_MU")), ""),
                users=users, shift_invariant=inv, all_users_equal_user0=all(inv.values()),
                user0_vs_single_user=vs_single,
                user0_equals_single_user=all(v["user0"] == v["single"] for v in vs_single.values()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--golden", required=True)
    ap.add_argument("--run", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--dag", default=None)
    ap.add_argument("--fold", type=float, default=0.0)
    ap.add_argument("--dag-mtp", default=None)
    ap.add_argument("--commit", default="", help="RTL / vehicle commit for the notes")
    ap.add_argument("--compose", action="store_true", help="emit the token_compose override block")
    ap.add_argument("--mu", action="append", default=[], help="NAME=GOLDEN_DIR:RUN_LOG of an MU run (repeatable)")
    ap.add_argument("--extra-run", action="append", default=[], help="NAME=RUN_LOG: verdict/stats of another run of this record")
    a = ap.parse_args()
    g = json.loads(Path(a.golden).read_text())
    rows, stats, verdict = parse(a.run)
    by = collections.defaultdict(list)
    for r in rows:
        by[r[0]].append(r)
    res = collections.OrderedDict()
    for ins in g["instances"]:
        m = dict(name=ins["name"], kind=ins["kind"], payload_B=ins["payload_B"], rep=ins["rep"],
                 beats_per_peer=ins.get("beats_per_peer", ins.get("beats")))
        if ins["kind"] == "AR":
            rs = inst_metrics(by[ins["inst"]]) if by[ins["inst"]] else None
            ag = inst_metrics(by[ins["inst_ag"]]) if by[ins["inst_ag"]] else None
            m.update(rs=rs, ag=ag, fold_die=a.fold,
                     E_meas=(rs["E_meas"] + a.fold + ag["E_meas"]) if rs and ag else None,
                     ag_issue_after_rs_land=(ag["first_issue"] - rs["last_land"]) if rs and ag else None)
        else:
            mm = inst_metrics(by[ins["inst"]]) if by[ins["inst"]] else None
            m.update(mm or {}, E_meas=mm["E_meas"] if mm else None)
        res[f'{ins["name"]}#{ins["rep"]}'] = m
    # per collective: both reps must agree
    coll = collections.OrderedDict()
    for k, m in res.items():
        n = m["name"]
        c = coll.setdefault(n, dict(kind=m["kind"], payload_B=m["payload_B"], beats_per_peer=m["beats_per_peer"], E=[]))
        c["E"].append(m["E_meas"])
        for f in ("L_first", "E_last", "drain_per_beat"):
            if f in m:
                c.setdefault(f, []).append(m[f])
        if m["kind"] == "AR" and m.get("rs"):
            c.setdefault("E_RS", []).append(m["rs"]["E_meas"]); c.setdefault("E_AG", []).append(m["ag"]["E_meas"])
            c.setdefault("L_first", []).append(m["rs"]["L_first"])
    for c in coll.values():
        Es = [e for e in c["E"] if e is not None]
        c["E_meas"] = max(Es) if Es else None
        c["deterministic"] = len(set(Es)) == 1 and len(Es) == len(c["E"])
    out = dict(schema="opentallas.xdie_s81.record.v1", config=a.name, verdict=verdict, stats=stats,
               golden=dict(beats=g["beats"], gate=g["gate"], lat=g["lat"], per=g["per"]),
               collectives=coll, instances=res)
    if a.dag:
        dag = json.loads(Path(a.dag).read_text())
        comp = collections.OrderedDict(); tot_new = tot_old = 0.0
        for nd in dag["nodes"]:
            x = DAG_MAP.get(nd["op"])
            if not x or x not in coll or coll[x]["E_meas"] is None:
                continue
            E = coll[x]["E_meas"] + ONDIE * CROSSINGS.get(x, 1)
            O = 0.0 if nd.get("critical") else nd["cycles"] + (nd.get("slack") or 0.0)
            old_exp = nd["cycles"] if nd.get("critical") else 0.0
            new_exp = max(0.0, E - O)
            r = comp.setdefault(nd["op"], dict(coll=x, n=0, n_critical=0, E_meas=E, dag_cycles_each=nd["cycles"],
                                               exposed_new=0.0, exposed_dag=0.0))
            r["n"] += 1; r["n_critical"] += 1 if nd.get("critical") else 0
            r["exposed_new"] += new_exp; r["exposed_dag"] += old_exp
            tot_new += new_exp; tot_old += old_exp
        # the 62 unplaced stage hops (one aggregate DAG node) are stage hops too
        un = next((nd for nd in dag["nodes"] if nd["op"] == "unplaced_hops"), None)
        if un and "stage_hop" in coll and coll["stage_hop"]["E_meas"] is not None:
            n_un = 62
            per_old = 1006.0
            comp["unplaced_hops (62 stage hops)"] = dict(coll="stage_hop", n=n_un, n_critical=n_un,
                E_meas=coll["stage_hop"]["E_meas"], dag_cycles_each=per_old,
                exposed_new=n_un * (coll["stage_hop"]["E_meas"] + ONDIE), exposed_dag=n_un * per_old,
                note="DAG node 'unplaced_hops' = 27 S81 frame hops + 35 HALF-mapping hops at 0.8425 us; priced here as "
                     "62 hops at the DAG's placed-hop 1,006 cycles for the delta")
            tot_new += n_un * (coll["stage_hop"]["E_meas"] + ONDIE); tot_old += n_un * per_old
        T = dag["totals"]["cycles"]
        out["composition"] = dict(
            dag=a.dag, dag_total_cycles=T, dag_tok_s=dag["totals"]["tok_s"],
            rule="T_xdie = sum_x n_x * max(0, E(x) - O(x)), E = E_meas (vehicle, incl. 453 modelled a crossing) + 134 "
                 "priced on-die cycles a crossing; O = 0 on the DAG critical path, cycles + slack off it",
            terms=comp, T_xdie_new=round(tot_new, 1), T_xdie_dag=round(tot_old, 1), delta_cycles=round(tot_new - tot_old, 1),
            tok_s_dag_basis=round(F_CLK / T, 2), tok_s_with_measured_xdie=round(F_CLK / (T + tot_new - tot_old), 2),
            pct_change=round(100.0 * (T / (T + tot_new - tot_old) - 1.0), 3))
    if a.mu:
        out["multi_user"] = {}
        for spec in a.mu:
            nm, rest = spec.split("=", 1)
            gd, rl = rest.split(":", 1)
            out["multi_user"][nm] = mu_summary(json.loads((Path(gd) / "golden.json").read_text()), rl, coll)
    if a.extra_run:
        out["runs"] = {}
        for spec in a.extra_run:
            nm, rl = spec.split("=", 1)
            _, st, vd = parse(rl)
            ln = Path(rl).read_text(errors="replace").splitlines()
            out["runs"][nm] = dict(verdict=vd, stats=st, link=next((x for x in ln if x.startswith("XDIE_LINK")), ""),
                                   mu=next((x for x in ln if x.startswith("XDIE_MU")), ""),
                                   cfg=next((x for x in ln if x.startswith("XDIE2_CFG")), ""))
    if a.compose and a.dag:
        dags = {"ar": a.dag}
        if a.dag_mtp:
            dags["mtp"] = a.dag_mtp
        out["token_compose"] = dict(terms=token_compose_terms(coll, dags, a.commit))
    Path(a.out).write_text(json.dumps(out, indent=1))
    print(verdict); print(stats)
    for n, c in coll.items():
        print(f"{n:20s} {c['kind']:3s} {c['payload_B']:6d} B  beats/peer {c['beats_per_peer']:4}  E_meas {c['E_meas']}  "
              f"det {c['deterministic']}  L_first {c.get('L_first')}  drain {c.get('drain_per_beat')}")
    if "composition" in out:
        cp = out["composition"]
        print(f"T_xdie new {cp['T_xdie_new']} vs DAG {cp['T_xdie_dag']} delta {cp['delta_cycles']} -> tok/s "
              f"{cp['tok_s_dag_basis']} -> {cp['tok_s_with_measured_xdie']} ({cp['pct_change']} %)")


if __name__ == "__main__":
    main()
