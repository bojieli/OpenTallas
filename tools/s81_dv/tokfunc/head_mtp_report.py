#!/usr/bin/env python3
"""TOK-FUNC-S81/HEADMTP: compose the LM-head (TOK.DS.LAYER.5) and MTP-draft (TOK.DS.LAYER.6) legs run by head_mtp_fleet.sh
into results/token_pass/tokfunc_s81_1021/head_mtp.json.  Grade: "RTL-functional (source assembly)".  Every cycle term is
labelled MEASURED (RTL bench on this run) or MODELLED (off-chip leg: release_rack_1021/hop_latency.json direct cabling, or the
link beat count of the S81-HEAD spec).  The head-die top does not exist (lane S81-HEAD), so the legs are composed serially at
their measured boundaries (golden boundary values shared bit for bit: head.norm.scale is both the producer's checked output
and the bundle's input).
    python3 tools/s81_dv/tokfunc/head_mtp_report.py --run DIR --prep DIR --out JSON [--meta k=v ...]
"""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
GRADE = "RTL-functional (source assembly)"


def rd(p):
    p = Path(p)
    return p.read_text(errors="replace") if p.exists() else ""


def sha(p):
    p = ROOT / p
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None


def ints(s):
    return [int(t) for t in s.split("/")]


def leg_xfin(run):
    out = {}
    for m in ("base", "mutleaf"):
        t = rd(run / f"xfin/{m}/run.log")
        line = next((l for l in t.splitlines() if l.startswith("DVXFIN16")), None)
        verdict = "PASS" if re.search(r"^PASS", t, re.M) else ("FAIL" if re.search(r"^FAIL", t, re.M) else "NO_RESULT")
        kv = dict(re.findall(r"(\w+)=([0-9a-fx]+)", line or ""))
        out[m] = dict(verdict=verdict, line=line, kv=kv)
    ok = out["base"]["verdict"] == "PASS" and out["mutleaf"]["verdict"] == "FAIL"
    kv = out["base"]["kv"]
    cyc = dict(stream_in_beats=80, last_partial_to_first_rstd=int(kv.get("last_partial_to_first_rstd", -1)),
               rstd_spread=int(kv.get("rstd_spread", -1)))
    return dict(ok=ok, kind="MEASURED", what="head hc_pre + RMSNorm exchange: ot_hbm_norm_grp G64 (80 beat partials) + 16 x "
                "ot_s81dv_xfin (collector, snake ring LS 9 / LE 29, replicated finish) -> rstd at all 16 slices; all 80 y vectors "
                "vs HEAD head.norm.scale", cycles=cyc, runs=out,
                rtl=["rtl/dsrom_sys/s81_dv/ot_s81dv_norm.sv", "physical/hbm_norm_split_20261008/sources.f"],
                bench="rtl/dsrom_sys/s81_dv/test/tb_s81dv_xfin16.sv")


def leg_beat(run):
    rows, bad = [], []
    for b in range(80):
        t = rd(run / f"beat/base_b{b:02d}/run.log")
        m = re.search(r"^SLBEAT .*", t, re.M)
        v = "PASS" if re.search(r"^PASS", t, re.M) else ("FAIL" if re.search(r"^FAIL", t, re.M) else "NO_RESULT")
        kv = dict(re.findall(r"(\w+)=([0-9/\-]+)", m.group(0))) if m else {}
        r = dict(beat=b, verdict=v)
        for k in ("go_to_partial", "rstd_to_y0", "rstd_to_xq", "rstd_to_xb"):
            if k in kv:
                r[k] = ints(kv[k])[0]       # block a = the head norm
        rows.append(r)
        if v != "PASS":
            bad.append(b)
    mt = rd(run / "beat/mutnormimm_b37/run.log")
    mut = "FAIL" if re.search(r"^FAIL", mt, re.M) else ("PASS" if re.search(r"^PASS", mt, re.M) else "NO_RESULT")
    good = [r for r in rows if r["verdict"] == "PASS"]
    mx = {k: max((r[k] for r in good if k in r), default=None) for k in ("go_to_partial", "rstd_to_xb")}
    return dict(ok=not bad and mut == "FAIL", kind="MEASURED",
                what="per-beat slice leaves vp (NORMR on the G-unit row) + vn + vq: beat partial, normed y and the 80 BF16 "
                "XB beats, every beat bit-exact vs HEAD head.norm.scale (block a); block f / hc_post run the same norm with "
                "identity comb (not graded)", beats_pass=len(good), beats_fail=bad, mutant_normimm_b37=mut,
                cycles=dict(go_to_partial_max=mx["go_to_partial"], rstd_to_xb_max=mx["rstd_to_xb"]), per_beat=rows,
                rtl=["rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vp.sv", "rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vn.sv",
                     "rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vq.sv", "rtl/dsrom_sys/s81_dv/slice/ot_s81sl_aq12x.sv"],
                bench="rtl/dsrom_sys/s81_dv/slice/test/tb_s81sl_beat.sv (-GVQ_XMEM=2, kit setting)")


def leg_egress(run):
    a, b, lat = rd(run / "egress/bench_none.log"), rd(run / "egress/bench_xooff.log"), rd(run / "egress/run_lat.log")
    m = re.search(r"RSTOP_LAT pass=1 n=(\d+) min=(-?\d+) max=(-?\d+) per_slice_max=([\d,\-]+)", lat)
    ok = "BENCH_PASS" in a and "NEGATIVE_CONTROL_FAILED_AS_EXPECTED" in b and bool(re.search(r"^PASS rstop_xo", lat, re.M))
    return dict(ok=ok and bool(m) and int(m.group(1)) == 80, kind="MEASURED",
                what="head XB egress on the 16-stop die ring with the current end-slice master ot_s81sl_rstopt_xo (in "
                "ot_s81sl_xgt_xo): 80 flagged beats leave s_0N ro_w exactly once, bit-exact (bench beat bodies are synthetic "
                "ring words; the head values are carried bit-exactly by construction, 0 added edges)",
                bench_none=[l for l in a.splitlines() if l.startswith(("PASS", "FAIL", "RSTOP_XO", "BENCH"))],
                mutant_xooff=[l for l in b.splitlines() if l.startswith(("FAIL", "NEGATIVE"))],
                cycles=dict(ring_inject_to_s0N_egress_min=int(m.group(2)) if m else None,
                            ring_inject_to_s0N_egress_max=int(m.group(3)) if m else None,
                            per_slice_max=[int(t) for t in m.group(4).split(",")] if m else None, egress_added_edges=0),
                rtl=["rtl/dsrom_sys/s81_dv/slice/ot_s81sl_rstopt_xo.sv", "rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xgt_xo.sv"],
                bench="tools/s81_slice/rstopt_xo_bench.sh + tools/s81_dv/tokfunc/rstop_lat_tb.py (latency copy)")


def leg_bundle(run):
    rec = {}
    p = run / "bundle/receipt.json"
    if p.exists():
        rec = json.loads(p.read_text())
    t = rd(run / "bundle/run_mode1_mut0.log")
    toks = re.findall(r"RETURN case=\d+ .* row=(\d+) bits=([0-9a-f]+) age=(\d+)", t)
    ok = rec.get("gate") == "PASS" and bool(toks) and all(r == "21946" for r, _, _ in toks)
    return dict(ok=ok, kind="MEASURED", what="LM-head bundle: ot_dsrom_head_bundle (5 elems, IOREG 1 SAFE 1) over ten "
                "ot_rom_4096x274_m8 holding the real rank-0 head.weight rows 21888..22015 (the 128-row group of the winner), "
                "ot_rom_argmax_rows, ot_s81_bundle_token_return; input = head.norm.scale; every returned logit vs HEAD "
                "head.lm_head, token 21946 / 4173a558; mutants (stream corrupt, owner, 1 edge late) FAIL",
                returns=[dict(row=int(r), bits=b, age=int(g)) for r, b, g in toks],
                cycles=dict(go_to_return=rec.get("actual_go_to_return_edges")), cases=rec.get("cases"),
                weights_slice_sha256=rec.get("weights_slice_sha256"), source_hashes=rec.get("source_hashes"),
                bench="tools/s81_ftok/live_head_return.py (codex/s81-token-integrate-1019@98a2f06da)")


def leg_tp4(run):
    p = run / "tp4/record.json"
    if not p.exists():
        return dict(ok=False, kind="MEASURED", error="no tp4 record", log_tail=rd(run / "tp4.log")[-1500:])
    r = json.loads(p.read_text())
    res = r.get("results", {})
    h = res.get("head", {}).get("ops", {}).get("1", {})
    drafts = {k: dict(token=v.get("exp_id"), pass_=v.get("pass"), lanes=v.get("fused_lanes"),
                      last_beat_to_final=v.get("ops", {}).get("2", {}).get("last_beat_to_final"))
              for k, v in res.items() if k.startswith("draft")}
    muts = {k: res.get(k, {}).get("pass") for k in ("mut_lg", "fh0_draft0")}
    return dict(ok=bool(r.get("pass_")), kind="MEASURED", what="4-rank fused head argmax (4 x ot_dsrom_s81_head_amax_fh, "
                "TP4 x 32,320 rows, 128 lanes, ot_rom_argmax_rows, rank chain + final broadcast) over the 129,280 HEAD "
                "logits (head) and the 5 MTP draft heads + Markov rows (fused add then argmax)",
                head=dict(token=h.get("id"), bits=h.get("bits"), beats=h.get("beats"),
                          first_beat_to_final=h.get("first_beat_to_final"), last_beat_to_final=h.get("last_beat_to_final")),
                drafts=drafts, mutants_pass_field=muts, measured_cycles=r.get("measured_cycles"),
                bench="tools/s81_dv/head_tp4_interim.py", source_sha256=r.get("source_sha256"))


def leg_dhead(run):
    p = run / "dhead/mtpd_draft_head.json"
    if not p.exists():
        return dict(ok=False, kind="MEASURED", error="no draft-head record", log_tail=rd(run / "dhead.log")[-1500:])
    r = json.loads(p.read_text())
    return dict(ok=bool(r.get("pass")), kind="MEASURED", what="MTP draft heads on the same LM-head bundle build: the 5 golden "
                "draft.head{i}.norm.scale inputs, every returned logit of rows 21888..22015 vs draft.head{i} + first-max token; "
                "mutant (head_d forced 0) FAIL", cycles=dict(go_to_return=r.get("ages_pass_cases")),
                cases=[dict(draft=c["draft"], mut=c["mut"], ok=c["ok"], ages=c["ages"], summary=c["summary"]) for c in r["cases"]],
                bench="tools/s81_dv/layer_prog/qf_producer/toksim_mtpd_draft_head.py")


def leg_wave(run):
    p = run / "wave/summary.json"
    if not p.exists():
        return dict(ok=False, kind="MEASURED", error="no wave summary", log_tail=rd(run / "wave.log")[-1500:])
    s = json.loads(p.read_text())
    ch = {}
    for c in s["cases"]:
        if c["case"] == "wave":
            for l in c.get("lines", []):
                m = re.match(r"WAVE_CHARGE id=(\S+) price=([\d.]+) measured=(-?[\d.]+) n=(\d+)", l)
                if m:
                    ch[m.group(1)] = dict(price=float(m.group(2)), measured=float(m.group(3)), n=int(m.group(4)))
    return dict(ok=all(c["ok"] for c in s["cases"]), kind="MEASURED", what="MTP sequencing loop tb_mtp_wave: dsfd_mtp_seq_rtt "
                "(head-die sequencer, core ot_dsrom_mtp_seq) + dsfd_cap_mtp_ep / dsfd_vm_mtp_ep + MTP lanes + seed launch / hrow "
                "+ P2 draft-die path + ot_dsrom_markov_row K256 + ot_mtp_commit, 1 user gamma 5; bench stubs (not RTL): stage "
                "core / S0 core busy, head lm-head T_LM, draft block compute T_BLK, seed_ctl T_SC; greedy truth is the bench's "
                "synthetic token function (sequencing exactness, not model numerics)",
                cases=[dict(case=c["case"], expect=c["expect"], got=c["got"], ok=c["ok"]) for c in s["cases"]],
                charges=ch, bench="tools/mtp_wave_bench.py (rtl/dsrom_sys/mtp/tb/tb_mtp_wave.sv)",
                source_sha256=s.get("source_sha256"))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--prep", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--meta", nargs="*", default=[])
    a = ap.parse_args()
    run = a.run
    hop = json.loads((ROOT / "results/arch/release_rack_1021/hop_latency.json").read_text())["systems"]["S81"]
    L = dict(xfin=leg_xfin(run), beat=leg_beat(run), egress=leg_egress(run), bundle=leg_bundle(run), tp4=leg_tp4(run),
             dhead=leg_dhead(run), wave=leg_wave(run))
    gold = json.loads((a.prep / "gold.json").read_text()) if (a.prep / "gold.json").exists() else {}

    def g(d, *ks):
        for k in ks:
            d = (d or {}).get(k) if isinstance(d, dict) else None
        return d
    terms = [
        ("head.hc_pre+norm: 80 beat partials in", "MEASURED", g(L, "xfin", "cycles", "stream_in_beats")),
        ("head.norm: last partial -> rstd (16-slice xfin ring)", "MEASURED", g(L, "xfin", "cycles", "last_partial_to_first_rstd")),
        ("head.norm.scale: rstd -> XB beat (vp/vn/vq, max of 80)", "MEASURED", g(L, "beat", "cycles", "rstd_to_xb_max")),
        ("XB egress: ring -> s_0N ro_w (max of 80)", "MEASURED", g(L, "egress", "cycles", "ring_inject_to_s0N_egress_max")),
        ("XB serialisation on the stage NEXT circuit: 160 x 512 b link beats (S81-HEAD SPEC 3)", "MODELLED", 160),
        ("head_hop: stage die -> head die, direct cabling (hop_latency.json D_cycles_max)", "MODELLED", hop["head_hop"]["D_cycles_max"]),
        ("head.lm_head: bundle go -> argmax return (128-row group, real ROM)", "MEASURED", g(L, "bundle", "cycles", "go_to_return")),
        ("head.argmax chain over 253 bundle results + TP4 rank merge + broadcast", "MEASURED", g(L, "tp4", "head", "first_beat_to_final")),
        ("head.argmax_merge: TP4 mesh crossing (hop_latency.json tp_mesh D)", "MODELLED", hop["tp_mesh"]["D_cycles_max"]),
        ("token.return: head die -> S000 (hop_latency.json token_return D)", "MODELLED", hop["token_return"]["D_cycles_max"]),
    ]
    known = [t for t in terms if isinstance(t[2], (int, float))]
    head_ok = all(L[k]["ok"] for k in ("xfin", "beat", "egress", "bundle", "tp4")) and g(L, "tp4", "head", "token") == 21946
    head_total = sum(t[2] for t in known) if len(known) == len(terms) else None
    dh = g(L, "dhead", "cycles", "go_to_return") or [None]
    mk = g(L, "tp4", "measured_cycles", "draft_fused_added", "last_beat_to_final")
    draft_terms = [
        ("draft body mtp.0..2 (3 transformer layers on the 72-frame stage die)", "NOT_RUN_HERE", None),
        ("draft head: bundle go -> return (real ROM, per draft row)", "MEASURED", dh[0]),
        ("draft argmax chain 253 results + TP4 merge (fused with Markov row)", "MEASURED",
         g(L, "tp4", "drafts", "draft0", "last_beat_to_final") and 253 + g(L, "tp4", "drafts", "draft0", "last_beat_to_final")),
        ("Markov fuse added cycles", "MEASURED", mk),
        ("dsfd_mtp_seq draft chain (wave charge mtp_seq.draft_chain)", "MEASURED", g(L, "wave", "charges", "mtp_seq.draft_chain", "measured")),
        ("dsfd_mtp_seq seed release (wave charge mtp_seq.seed_release)", "MEASURED", g(L, "wave", "charges", "mtp_seq.seed_release", "measured")),
    ]
    mtp_ok = all(L[k]["ok"] for k in ("dhead", "tp4", "wave"))
    rep = dict(
        schema="opentallas.tokfunc_s81.head_mtp.v1", lane="TOK-FUNC-S81/HEADMTP", grade=GRADE,
        tree_lines=["TOK.DS.LAYER.5 LM head", "TOK.DS.LAYER.6 MTP draft layer"],
        token=dict(context=1048576, position=1048575, next_token_golden=21946, fixture_head="HEAD (results/rtl/s81_layer_tput_1018/"
                   "fixtures/HEAD.sha256.json)", fixture_mtp="MTP (results/rtl/s81_layer_tput_1018/fixtures/MTP.sha256.json; the "
                   "regenerated 10-18 fixture of claude/lb2-s81-mtp-1018, generator fix in main: embed rows by Checkpoint.rows)"),
        verdict=dict(lm_head="PASS" if head_ok else "FAIL", mtp_draft_head_and_seq="PASS" if mtp_ok else "FAIL",
                     mtp_draft_body="NOT_RUN_HERE (stage-die per-layer runs, parent lane)"),
        lm_head=dict(terms=[dict(term=a_, kind=b_, cycles=c_) for a_, b_, c_ in terms], serial_sum_cycles=head_total,
                     note="serial composition of measured legs at their boundaries (no overlap credited); the head die top "
                     "(S81-HEAD) does not exist, so x distribution to 253 tiles and the return spine are represented by the "
                     "bundle's measured go->return and the measured 253-result chain"),
        mtp=dict(terms=[dict(term=a_, kind=b_, cycles=c_) for a_, b_, c_ in draft_terms]),
        legs=L, gold=gold,
        modelled=["XB link serialisation 160 beats (S81-HEAD SPEC)", "head_hop / tp_mesh / token_return off-die legs "
                  "(results/arch/release_rack_1021/hop_latency.json, direct cabling D)", "lep / SerDes PHY",
                  "wave bench stubs: stage / S0 core busy, head lm-head T_LM, draft block T_BLK, seed_ctl T_SC"],
        open_gaps=["S81 head die top (lane S81-HEAD) not built: legs composed, not one netlist",
                   "MTP draft body mtp.0..2 not run in this sub-lane (same 72-frame stage-die type; per-layer runner of the "
                   "parent lane on the MTP fixture)",
                   "head producer on the die: 16-slice NX/XB composition timing (GAP_NORM16) and the s_0N one-beat-per-cycle rule "
                   "are plan values; this run measures the xfin exchange (HBM norm group as the partial source) and the slice "
                   "leaves per beat separately",
                   "bundle runs the 128-row group that holds the winner; the other 252 groups are the same RTL on other ROM "
                   "rows (their logits enter the argmax chain from the fixture)",
                   "wave bench greedy truth is synthetic; draft-head numerics are covered by dhead + tp4"],
        sources={p: sha(p) for p in [
            "tools/s81_dv/tokfunc/run_head_mtp.sh", "tools/s81_dv/tokfunc/head_mtp_fleet.sh", "tools/s81_dv/tokfunc/head_mtp_gold.py",
            "tools/s81_dv/tokfunc/head_mtp_report.py", "tools/s81_dv/tokfunc/rstop_lat_tb.py",
            "rtl/dsrom_sys/s81_dv/test/tb_s81dv_xfin16.sv", "rtl/dsrom_sys/s81_dv/ot_s81dv_norm.sv",
            "rtl/dsrom_sys/s81_dv/slice/test/tb_s81sl_beat.sv", "rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vp.sv",
            "rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vn.sv", "rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vq.sv",
            "rtl/dsrom_sys/s81_dv/slice/ot_s81sl_rstopt_xo.sv", "rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xgt_xo.sv",
            "rtl/dsrom_sys/s81_dv/slice/test/tb_s81sl_rstop_xo.sv", "tools/s81_slice/rstopt_xo_bench.sh",
            "rtl/v41rom/ot_dsrom_head_bundle.sv", "rtl/v41rom/ot_dsrom_head_elem.sv",
            "rtl/dsrom_sys/s81_native_head/ot_rom_argmax_rows.sv",
            "rtl/dsrom_sys/s81_native_head_connect/ot_s81_bundle_token_return.sv",
            "rtl/dsrom_sys/integration/ot_dsrom_s81_head_amax_fh.sv", "rtl/dsrom_sys/mtp/dsfd_mtp_seq_rtt.sv",
            "rtl/dsrom_sys/mtp/ot_dsrom_mtp_seq.sv", "tools/mtp_wave_bench.py", "tools/s81_dv/head_tp4_interim.py",
            "tools/s81_ftok/live_head_return.py", "results/arch/release_rack_1021/hop_latency.json"]},
        simulator=rd(run / "verilator_version.log").strip(), meta=dict(kv.split("=", 1) for kv in a.meta))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rep, indent=1) + "\n")
    print("HEAD_MTP lm_head", rep["verdict"]["lm_head"], "serial", head_total, "| mtp", rep["verdict"]["mtp_draft_head_and_seq"])
    for t in terms + draft_terms:
        print(f"  {t[1]:12s} {str(t[2]):>8s}  {t[0]}")
    return 0 if head_ok and mtp_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
