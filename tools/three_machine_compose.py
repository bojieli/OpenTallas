#!/usr/bin/env python3
"""Recompose the three machines from committed lever records, with an adoption guard (one command).

  DS ROM   DeepSeek-V4.1 1M (P1,048,575): tools/dsrom_1m_allmeasured.compose() over the lever records
           results/rtl/dsrom_recovery_20261004/levers/*.json (ADOPT + exact applied; PENDING_SSFF recomposed
           separately as CONDITIONAL, never in the headline).  MTP at the adopted owner-blend tau (4.159),
           published 3.8879 as the sensitivity (tools/third_party_tau.py).
  Qwen ROM Qwen3-8B 8K (P8191): the measured STREAM4 full36+HEAD token (terminal.json, 193,955 cycles) plus the
           adopted in-context core closure's added cycles (claude_context_20261005/verdict.json, +112/token).
           MTP mode = AR (DSpark verdict AR_MODE: below AR on STREAM4).
  HBM      DS HBM accelerator 1M: the matched reference gate (dshbm_matched_reference_20261005) + the exact HBM
           levers (joint PQ+XMAP, paired W2 PACK; tools/dshbm_hbm_opt_compose.py output joint_r2) + the die
           wire stages priced at floor / median / bound (hbm_accel_die_floorplan_20261005/wire_stages.json).

GUARD (refuses to publish, exit 2):
  * an ADOPT lever record that is not exact, or an unknown verdict;
  * a lever applied in the published DS ROM composition that is not ADOPT+exact now (or whose record changed /
    disappeared), or an ADOPT+exact lever the published composition does not apply (missing);
  * the same two checks on the fresh recomposition;
  * Qwen: core closure not SS/FF >= 0, or its token_cycles_before != the measured terminal token;
  * HBM: a non-exact lever (e.g. the analytic item-3 x map) included, a lever input whose sha256 drifted, or a
    basis that is not the matched gate.

    python3 tools/three_machine_compose.py            # recompose, guard, write record + table, scoreboard --check
    python3 tools/three_machine_compose.py --check    # guard + recompose, compare with the committed record only
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

RECOVERY = ROOT / "results/rtl/dsrom_recovery_20261004"
QWEN_TERMINAL = ROOT / "results/rtl/qwen_plain_ar_stream4_P8191_20261005/terminal.json"
QWEN_CORE = ROOT / "results/rtl/qwen_core_decode_closure_20261004/claude_context_20261005/verdict.json"
QWEN_DSPARK = ROOT / "results/rtl/qwen_rom_kv_fullbw_20261004/dspark_verdict.json"
HBM_MATCHED = ROOT / "results/rtl/dshbm_matched_reference_20261005/composition.json"
HBM_OPT = ROOT / "results/rtl/dshbm_hbm_opt_20261005/joint_r2/composition.json"
WIRE = ROOT / "results/rtl/hbm_accel_die_floorplan_20261005/wire_stages.json"
OUT = ROOT / "results/arch/three_machine_compose"
WIRE_BASES = (("floor", "stages_430_manhattan"), ("median", "stages_430_median_bundle"), ("bound", "stages_430"))
LEVER_SCHEMA = "opentallas.dsrom-recovery.lever.v1"
KNOWN_VERDICTS = {"ADOPT", "REJECT", "PENDING_SSFF"}


class Refused(Exception):
    pass


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rel(p):
    p = Path(p).resolve()
    return str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p)


def load(p):
    return json.loads(Path(p).read_text())


# ------------------------------------------------------------------------------------------------- DS ROM levers
def read_levers(lever_dir: Path):
    """All lever records (schema v1) with their adoption class; refuses inconsistent records."""
    out, errs = {}, []
    for f in sorted(lever_dir.glob("*.json")):
        r = load(f)
        if r.get("schema") != LEVER_SCHEMA:
            continue
        v, ex = r.get("verdict"), r.get("exact")
        if v not in KNOWN_VERDICTS:
            errs.append(f"{r['lever']}: unknown verdict {v!r}")
        if v == "ADOPT" and ex is not True:
            errs.append(f"{r['lever']}: verdict ADOPT but exact={ex!r} (an ADOPT lever must be exact)")
        cls = ("adopted" if v == "ADOPT" and ex is True else
               "conditional" if v == "PENDING_SSFF" and ex is True else "excluded")
        out[r["lever"]] = dict(lever=r["lever"], verdict=v, exact=ex, cls=cls, record=rel(f), path=f,
                               sha256=sha(f), note=r.get("verdict_reason") or r.get("note") or "")
    if errs:
        raise Refused("lever records: " + "; ".join(errs))
    return out


def guard_applied(levers: dict, applied: list, what: str):
    """`applied` = info.levers.applied of a DS ROM composition.  Refuse unless it is exactly the ADOPT+exact set
    with the current record bytes."""
    errs = []
    adopted = {k for k, v in levers.items() if v["cls"] == "adopted"}
    seen = set()
    for row in applied:
        k = row["lever"]
        seen.add(k)
        if k not in levers:
            errs.append(f"{what} applies lever {k!r} whose record is gone (ADOPT lever missing)")
        elif levers[k]["cls"] != "adopted":
            errs.append(f"{what} includes lever {k!r} with verdict {levers[k]['verdict']} exact={levers[k]['exact']} "
                        "(only ADOPT + exact may be included)")
        elif row.get("sha256") != levers[k]["sha256"]:
            errs.append(f"{what} applied lever {k!r} from a different record version (stale composition)")
    for k in sorted(adopted - seen):
        errs.append(f"{what} is missing ADOPT lever {k!r}")
    if errs:
        raise Refused("; ".join(errs))


def _args(recovery: Path):
    import dsrom_1m_allmeasured as D
    return argparse.Namespace(rec=D.REC, out=Path("/dev/null"), baseline="recovery", recovery=recovery,
                              window="s81", hop_tier="light_fec")


def _row(rec):
    m = rec["MTP"]
    return dict(AR_us=rec["AR_us"], AR_tok_s=rec["AR_tok_s"], MTP_step_us=m["step_us"], MTP_tok_s=m["MTP_tok_s"],
                MTP_tok_s_tau_published=m["tau_sensitivity"]["published"]["MTP_tok_s"], II_us=m["II_us"],
                measured_share=rec["measured_share"])


def _delta(new, base):
    return {k: round(new[k] - base[k], 3) for k in ("AR_us", "AR_tok_s", "MTP_step_us", "MTP_tok_s")}


def ds_rom(recovery: Path, levers: dict, deltas=True):
    import dsrom_1m_allmeasured as D
    base = D.compose(_args(recovery), write_output=False)
    guard_applied(levers, base["info"]["levers"]["applied"], "fresh DS ROM recomposition")
    b = _row(base)
    per = {}
    if deltas:
        for k, v in levers.items():
            if v["cls"] == "adopted":       # delta = headline - headline without this lever
                r = _row(D.compose(_args(recovery), excluded_levers=(k,), write_output=False))
                per[k] = dict(cls="adopted", verdict=v["verdict"], record=v["record"], delta=_delta(b, r))
        with tempfile.TemporaryDirectory() as td:
            for k, v in levers.items():
                if v["cls"] != "conditional":
                    continue
                r = _row(_with_flipped(recovery, Path(td), [k]))
                per[k] = dict(cls="conditional", verdict=v["verdict"], record=v["record"], delta=_delta(r, b),
                              if_adopted=r)
            # alternatives: conditional levers replacing the same nodes (e.g. field_spine vs field_spine_pq) are
            # not stacked; the joint keeps the one with the larger individual AR gain and lists the other
            cond = [k for k, v in levers.items() if v["cls"] == "conditional"]
            nodes = {k: set(load(levers[k]["path"]).get("nodes", {})) for k in cond}
            dropped = {}
            for x in cond:
                for y in cond:
                    if x < y and nodes[x] & nodes[y]:
                        lo, hi = sorted((x, y), key=lambda k: per[k]["delta"]["AR_us"], reverse=True)
                        dropped[lo] = f"overlaps {hi} on {len(nodes[x] & nodes[y])} nodes; {hi} kept in the joint"
            cond = [k for k in cond if k not in dropped]
            joint = _row(_with_flipped(recovery, Path(td), cond)) if cond else None
        for k, v in levers.items():
            if v["cls"] == "excluded":
                per[k] = dict(cls="excluded", verdict=v["verdict"], exact=v["exact"], record=v["record"],
                              note=v["note"][:240])
    else:
        joint, cond, dropped = None, [], {}
    m = base["MTP"]
    return base, dict(
        tool="tools/dsrom_1m_allmeasured.py compose() (recovery baseline)",
        **b, tau=m["tau"], tau_source=m["tau_source"], tau_sensitivity=m["tau_sensitivity"],
        MTP_physical_qualified=m.get("physical_qualified"), MTP_qualified_headline_rate=m.get("qualified_headline_rate"),
        still_modelled_total_us=base["still_modelled_total_us"],
        levers=per, conditional_all=dict(levers=cond, alternatives_not_stacked=dropped, composed=joint,
                                         note="all PENDING_SSFF levers (alternatives resolved) flipped to ADOPT together; not a headline"))


def _with_flipped(recovery: Path, td: Path, names):
    """Compose as if the named PENDING_SSFF levers were ADOPT (same apply_levers semantics), in a scratch copy."""
    import dsrom_1m_allmeasured as D
    tmp = td / ("r_" + "_".join(names))
    if tmp.exists():
        shutil.rmtree(tmp)
    shutil.copytree(recovery / "levers", tmp / "levers")
    for n in names:
        for f in (tmp / "levers").glob("*.json"):
            r = load(f)
            if r.get("lever") == n:
                r["verdict"] = "ADOPT"
                f.write_text(json.dumps(r))
    old_rel, D.rel = D.rel, rel          # the scratch copy lives outside the repository
    try:
        return D.compose(_args(tmp), write_output=False)
    finally:
        D.rel = old_rel


# ------------------------------------------------------------------------------------------------------ Qwen ROM
def qwen_rom():
    t, core, dsp = load(QWEN_TERMINAL), load(QWEN_CORE), load(QWEN_DSPARK)
    if not (t["status"] == "PASS" and t["process_exit"] == 0 and t["total_cycles"] == t["total_edges"]):
        raise Refused("Qwen terminal.json is not a PASS full token")
    ad = core["adopted"]
    if not (ad["setup_ss_ref_ps"] >= 0 and ad["hold_ff_ref_ps"] >= 0 and ad["drc_errors"] == 0):
        raise Refused(f"Qwen core-context lever {ad['variant']} does not close SS60/FF25")
    if ad["token_cycles_before"] != t["total_cycles"]:
        raise Refused(f"Qwen core-context added cycles composed on {ad['token_cycles_before']}, "
                      f"terminal token is {t['total_cycles']} (stale)")
    clk = ad["tok_per_s_before"] * ad["token_cycles_before"]
    if abs(clk - 1.2e9) > 1e6:
        raise Refused(f"Qwen clock basis {clk:.4g} Hz is not 1.2 GHz")
    clk = 1.2e9
    cyc = t["total_cycles"] + ad["added_cycles_per_token"]
    ar = clk / cyc
    sp = dsp["variants"]["baseline_np4"]
    mtp_mode = dsp["verdict"] == "AR_MODE"
    return dict(
        position=t["position"], clock_hz=clk, token_cycles_measured=t["total_cycles"],
        levers={"core_context": dict(cls="adopted", verdict="ADOPT (closed SS60/FF25, exact 5/5)", record=rel(QWEN_CORE),
                                     variant=ad["variant"], ss_ps=ad["setup_ss_ref_ps"], ff_ps=ad["hold_ff_ref_ps"],
                                     delta=dict(cycles=ad["added_cycles_per_token"],
                                                AR_tok_s=round(ar - clk / t["total_cycles"], 3)))},
        token_cycles=cyc, AR_us=round(cyc / clk * 1e6, 3), AR_tok_s=round(ar, 1),
        MTP_mode="AR (DSpark OFF)" if mtp_mode else "DSpark", MTP_tok_s=round(ar, 1) if mtp_mode else sp["tok_s_upper"],
        dspark_reference=dict(tok_s=sp["tok_s_upper"], speedup_vs_ar=sp["speedup_vs_ar_upper"], tau=sp["tau"],
                              verdict=dsp["verdict"], record=rel(QWEN_DSPARK)),
        physical_qualified_full_system=False,
        inputs={rel(p): sha(p) for p in (QWEN_TERMINAL, QWEN_CORE, QWEN_DSPARK)})


# ---------------------------------------------------------------------------------------------------------- HBM
def hbm_ds():
    import third_party_tau as TP
    mref, opt, wire = load(HBM_MATCHED), load(HBM_OPT), load(WIRE)
    gate = mref["gate"]
    b = opt["basis"]
    if b["record"] != rel(HBM_MATCHED) or abs(b["gate_AR_us"] - gate["AR_us"]) > 1e-6 \
            or abs(b["gate_MTP_step_us"] - gate["MTP_step_us"]) > 1e-6:
        raise Refused("HBM lever composition is not on the matched gate basis")
    tau = gate["tau"]
    j, w2 = opt["joint_PQ_XMAP"], opt["paired_W2_increment"]
    drift = [p for blk in (j["inputs"], w2["inputs"], w2["combined_measurement"]["inputs"]) for p, s in blk.items()
             if not (ROOT / p).exists() or sha(ROOT / p) != s]
    if drift:
        raise Refused(f"HBM lever inputs drifted: {drift}")
    term = load(ROOT / next(p for p in j["inputs"] if p.endswith("terminal.json")))
    levers = {
        "joint_PQ_XMAP": dict(exact=term["status"] == "pass" and j["negative_expected_failure"] is True,
                              AR_us=-j["target_clock_projection"]["AR"]["total_replacement_saved_us"],
                              MTP_step_us=-j["target_clock_projection"]["MTP"]["total_replacement_saved_us"],
                              scope=j["measured_scope"], ss_ff=j["SS_FF_admitted"],
                              note="pipelined issue (item 1) + format-masked x map measured together; replaces the "
                                   "PQ groups once (item 1 alone is not added again)"),
        "paired_W2_PACK": dict(exact=bool(w2["actual_combined_PQ_XMAP_PACK_measured"]
                                          and w2["combined_measurement"]["exact_rows"] == 86
                                          and w2["combined_measurement"]["exact_activation_beats"]),
                               AR_us=-w2["incremental_AR_projection_us"], MTP_step_us=0.0,
                               scope=w2["combined_measurement"]["scope"], ss_ff=w2["physical_ss_ff_qualified"],
                               note="P1 combined measurement; P6 (MTP) increment unmeasured -> 0"),
    }
    excluded = {"item3_activation_delivery_standalone": "analytic beat-law sensitivity (not an exact measurement; "
                                                        "joint_PQ_XMAP carries the measured x map)",
                "item2_partial_wave / item4_workgroup_layout": "estimates (design notes), not credited",
                "item5_head": "REJECT"}
    bad = [k for k, v in levers.items() if v["exact"] is not True]
    if bad:
        raise Refused(f"HBM non-exact lever included: {bad}")
    ar0, st0 = gate["AR_us"], gate["MTP_step_us"]
    ar1 = ar0 + sum(v["AR_us"] for v in levers.values())
    st1 = st0 + sum(v["MTP_step_us"] for v in levers.values())
    pub = TP.sensitivity_ds_v41()["published"]["tau"]
    rows = {}
    for name, key in WIRE_BASES:
        add = wire["bases"][key]["ds_matched_added_us"]
        ar, st = ar1 + add, st1 + add
        rows[name] = dict(wire_basis=key, wire_added_us=add, AR_us=round(ar, 3), AR_tok_s=round(1e6 / ar, 1),
                          MTP_step_us=round(st, 3), MTP_tok_s=round(tau * 1e6 / st, 1),
                          MTP_tok_s_tau_published=round(pub * 1e6 / st, 1))
    # cross-check: the wire record's own gate-row pricing at each basis reproduces gate + wire
    for name, key in WIRE_BASES:
        assert abs(wire["bases"][key]["ds_gate_AR_priced_us"] - (ar0 + wire["bases"][key]["ds_matched_added_us"])) < 2e-3
    return dict(
        basis=dict(record=rel(HBM_MATCHED), gate_AR_us=ar0, gate_MTP_step_us=st0, tau=tau, gate_AR_tok_s=round(1e6 / ar0, 1),
                   gate_MTP_tok_s=gate["MTP_tok_s"]),
        levers={k: dict(cls="exact_credited", record=rel(HBM_OPT), exact=v["exact"], ss_ff_admitted=v["ss_ff"],
                        delta=dict(AR_us=round(v["AR_us"], 3), MTP_step_us=round(v["MTP_step_us"], 3)), scope=v["scope"],
                        note=v["note"]) for k, v in levers.items()},
        not_credited=excluded,
        levers_AR_us=round(ar1, 3), levers_MTP_step_us=round(st1, 3),
        rows=rows, headline_row="median",
        unvalidated=["wire stages priced on the matched-reference walk's crossing counts; the PQ levers merge some "
                     "barriers / x loads, so the barrier and x-broadcast wire terms are an upper charge on the lever row",
                     "HBM levers are exact on minimum components; SS60/FF25 not admitted (comparator credit)",
                     "inherited vendor terms (Tomahawk-Ultra PHY + switch + cable) as in the matched reference"],
        inputs={rel(p): sha(p) for p in (HBM_MATCHED, HBM_OPT, WIRE)})


# ------------------------------------------------------------------------------------------------------- output
def table(rec):
    d, q, h = rec["ds_rom"], rec["qwen_rom"], rec["hbm_ds"]
    L = ["THREE-MACHINE COMPOSITION (per user, target context)", "",
         f"{'machine':34s} {'AR tok/s':>10s} {'MTP tok/s':>10s} {'MTP@3.8879':>11s}  note"]
    L.append(f"{'DS ROM 1M (adopted levers)':34s} {d['AR_tok_s']:>10,.1f} {d['MTP_tok_s']:>10,.1f} "
             f"{d['MTP_tok_s_tau_published']:>11,.1f}  tau {d['tau']:g}; MTP physical_qualified={d['MTP_physical_qualified']}")
    cj = d["conditional_all"]["composed"]
    if cj:
        L.append(f"{'  + all PENDING_SSFF (CONDITIONAL)':34s} {cj['AR_tok_s']:>10,.1f} {cj['MTP_tok_s']:>10,.1f} "
                 f"{cj['MTP_tok_s_tau_published']:>11,.1f}  not a headline")
    L.append(f"{'Qwen ROM 8K (P8191)':34s} {q['AR_tok_s']:>10,.1f} {q['MTP_tok_s']:>10,.1f} {'-':>11s}  "
             f"{q['token_cycles']:,} cycles; MTP mode {q['MTP_mode']} (DSpark {q['dspark_reference']['speedup_vs_ar']}x)")
    for name, r in h["rows"].items():
        L.append(f"{('HBM accel DS 1M, wire ' + name):34s} {r['AR_tok_s']:>10,.1f} {r['MTP_tok_s']:>10,.1f} "
                 f"{r['MTP_tok_s_tau_published']:>11,.1f}  +{r['wire_added_us']} us wire")
    L += ["", f"DS ROM / HBM (wire median): AR {rec['ratios']['ds_rom_over_hbm_ar']:.4f}x  "
              f"MTP {rec['ratios']['ds_rom_over_hbm_mtp']:.4f}x", "",
          "PER-LEVER DELTAS (adopted: headline minus headline-without; conditional: if-adopted minus headline)",
          f"{'machine':9s} {'lever':22s} {'class':12s} {'dAR us':>9s} {'dAR tok/s':>10s} {'dMTP step':>10s} {'dMTP tok/s':>11s}"]
    for k, v in sorted(d["levers"].items(), key=lambda kv: (kv[1]["cls"], kv[0])):
        if v["cls"] == "excluded":
            L.append(f"{'DS ROM':9s} {k:22s} {'excluded':12s} {v['verdict']}")
            continue
        x = v["delta"]
        L.append(f"{'DS ROM':9s} {k:22s} {v['cls']:12s} {x['AR_us']:>9.3f} {x['AR_tok_s']:>10.1f} "
                 f"{x['MTP_step_us']:>10.3f} {x['MTP_tok_s']:>11.1f}")
    for k, v in q["levers"].items():
        L.append(f"{'Qwen ROM':9s} {k:22s} {v['cls']:12s} {'+' + str(v['delta']['cycles']) + ' cyc':>9s} "
                 f"{v['delta']['AR_tok_s']:>10.1f}")
    for k, v in h["levers"].items():
        L.append(f"{'HBM':9s} {k:22s} {'exact':12s} {v['delta']['AR_us']:>9.3f} {'':>10s} {v['delta']['MTP_step_us']:>10.3f}")
    return "\n".join(L) + "\n"


def compose_all(recovery: Path, committed: Path, deltas=True):
    levers = read_levers(recovery / "levers")
    guard_applied(levers, load(committed)["info"]["levers"]["applied"], f"published DS ROM composition ({rel(committed)})")
    _, ds = ds_rom(recovery, levers, deltas=deltas)
    q, h = qwen_rom(), hbm_ds()
    hm = h["rows"][h["headline_row"]]
    rec = dict(
        schema="opentallas.three-machine-compose.v1",
        rule="ADOPT + exact levers only in headlines; PENDING_SSFF reported as conditional; refuses otherwise",
        ds_rom=ds, qwen_rom=q, hbm_ds=h,
        ratios=dict(ds_rom_over_hbm_ar=round(ds["AR_tok_s"] / hm["AR_tok_s"], 4),
                    ds_rom_over_hbm_mtp=round(ds["MTP_tok_s"] / hm["MTP_tok_s"], 4),
                    hbm_row=h["headline_row"],
                    by_wire_basis={n: dict(ar=round(ds["AR_tok_s"] / r["AR_tok_s"], 4),
                                           mtp=round(ds["MTP_tok_s"] / r["MTP_tok_s"], 4))
                                   for n, r in h["rows"].items()}),
        lever_summary=dict(
            ds_rom_adopted=sorted(k for k, v in ds["levers"].items() if v["cls"] == "adopted"),
            ds_rom_conditional=sorted(k for k, v in ds["levers"].items() if v["cls"] == "conditional"),
            ds_rom_excluded=sorted(k for k, v in ds["levers"].items() if v["cls"] == "excluded"),
            qwen_rom_adopted=sorted(q["levers"]), hbm_exact_credited=sorted(h["levers"])),
        inputs=dict(levers={v["record"]: v["sha256"] for v in levers.values()},
                    ds_rom_composition={rel(committed): sha(committed)}, **q["inputs"], **h["inputs"]),
        tool_sha256={rel(Path(__file__)): sha(Path(__file__))})
    return rec


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--recovery", type=Path, default=RECOVERY, help="directory holding levers/*.json")
    ap.add_argument("--composition", type=Path, default=None,
                    help="published DS ROM composition (default <recovery>/composition.json)")
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--check", action="store_true", help="do not write; fail if the committed record differs")
    ap.add_argument("--guard-only", action="store_true", help="lever guard against the published composition only")
    ap.add_argument("--no-scoreboard", action="store_true")
    a = ap.parse_args(argv)
    committed = a.composition or a.recovery / "composition.json"
    try:
        if a.guard_only:
            levers = read_levers(a.recovery / "levers")
            guard_applied(levers, load(committed)["info"]["levers"]["applied"], f"published DS ROM composition ({rel(committed)})")
            print("GUARD PASS:", sorted(k for k, v in levers.items() if v["cls"] == "adopted"))
            return 0
        rec = compose_all(a.recovery, committed)
    except Refused as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 2
    tab = table(rec)
    print(tab)
    out_json, out_tab = a.out / "compose.json", a.out / "table.txt"
    text = json.dumps(rec, indent=1, default=str) + "\n"
    if a.check:
        old = out_json.read_text() if out_json.exists() else ""
        strip = lambda s: {k: v for k, v in json.loads(s).items() if k != "tool_sha256"} if s else None
        if strip(old) != strip(text):
            print(f"STALE: {rel(out_json)} differs from the recomposition", file=sys.stderr)
            return 1
        print("CHECK PASS")
        return 0
    a.out.mkdir(parents=True, exist_ok=True)
    out_json.write_text(text)
    out_tab.write_text(tab)
    print(f"wrote {rel(out_json)}, {rel(out_tab)}")
    if not a.no_scoreboard:
        for args in ([], ["--check"]):
            r = subprocess.run([sys.executable, str(ROOT / "tools/measured_scoreboard.py"), *args], cwd=ROOT)
            if r.returncode:
                print(f"measured_scoreboard.py {' '.join(args)} failed ({r.returncode})", file=sys.stderr)
                return r.returncode
    return 0


if __name__ == "__main__":
    sys.exit(main())
