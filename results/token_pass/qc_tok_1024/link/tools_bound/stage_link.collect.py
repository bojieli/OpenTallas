#!/usr/bin/env python3
"""TOK-FUNC-QW link stages (10-21): parse the runs of stage_tp8.sh / stage_ovl4u.sh / stage_ctx4u.sh into
RUNROOT/<stage>/result.json.  usage: stage_link.collect.py {tp8|ovl4u|ctx4u} RUNROOT --grade G [--lanes JSON]"""
import argparse, json, re, statistics
from pathlib import Path

CLK_HZ = 1.2e9          # 833 ps
LAYERS = 36             # Qwen3-8B: 2 all-reduces per layer


def asm_commit(root):
    p = root / "src" / "ASM_COMMIT"
    return p.read_text().strip() if p.exists() else "unknown"


def tp8(root, S, a):
    R = S / "runs"; runs = {}; mutants = {}; logs = []
    for line in (S / "cases.txt").read_text().splitlines():
        if not line.strip():
            continue
        name = line.split("|", 1)[0]; ef = "--expect-fail" in line
        logs.append(f"runs/{name}.log")
        rec = R / name / "record.json"
        if not rec.exists():
            log = (R / f"{name}.log").read_text(errors="replace") if (R / f"{name}.log").exists() else ""
            runs[name] = dict(expect_fail=ef, ok=False, error="no record.json (build/elaboration failure)",
                              tail=log.strip().splitlines()[-6:])
        else:
            r = json.loads(rec.read_text()); cs = {}
            for c in r["cases"]:
                p = c.get("program") or []
                for m in p:
                    m["last_in"] = m["first_slot"] + (8 if m["mode"] else 1) * (m["words"] - 1)
                res = c.get("result") or {}
                cs[c["name"]] = dict(passed=c["passed"], words_out=res.get("words_out"), mismatches=res.get("mismatches"),
                                     span=c.get("compiled_span_cycles"),
                                     E_meas_first=(p[0]["first_out"] - p[0]["last_in"]) if p and p[0].get("first_out") is not None else None,
                                     first_in_to_first_out=(p[0]["first_out"] - p[0]["first_slot"]) if p and p[0].get("first_out") is not None else None)
            ok = (not any(c["passed"] for c in r["cases"])) if r["expect_fail"] else (bool(r["cases"]) and all(c["passed"] for c in r["cases"]))
            runs[name] = dict(expect_fail=r["expect_fail"], ok=ok, lats=r.get("lats"), latu=r.get("latu"), mutant=r.get("mutant"),
                              verilator=r.get("verilator_version"), cases=cs)
        if ef:
            mutants[name] = "FAIL as required" if runs[name]["ok"] else ("NOT RUN: " + runs[name].get("error", "")) if "error" in runs[name] else "PASSED (UNEXPECTED)"
    cyc = {}
    try:
        c = runs["cal"]["cases"]; ar, am = c["qwen_ar_256w"], c["qwen_argmax_1w"]
        cyc.update(AR256_E=ar["E_meas_first"], AR256_span=ar["span"], AR256_first_in_to_first_out=ar["first_in_to_first_out"],
                   AR256x2_back_to_back_span=c["qwen_layer_2x256w"]["span"], argmax_1w_E=am["E_meas_first"], argmax_1w_span=am["span"],
                   layer_2xAR_plus_argmax_span=c["qwen_layer_2x256w_argmax"]["span"], LS=runs["cal"]["lats"], LU=runs["cal"]["latu"],
                   token_allreduce_E_36x2=LAYERS * 2 * ar["E_meas_first"],
                   token_E_incl_argmax=LAYERS * 2 * ar["E_meas_first"] + am["E_meas_first"],
                   token_span=LAYERS * 2 * ar["span"] + am["span"])
        mu = runs["mu"]["cases"]
        cyc.update(mu4_window_span=mu["mu_window"]["span"], mu4_window_E=mu["mu_window"]["E_meas_first"],
                   mu4_user0_alone_span=mu["mu_window_ref_user0"]["span"], mu4_user0_alone_E=mu["mu_window_ref_user0"]["E_meas_first"])
    except (KeyError, TypeError) as e:
        cyc["missing"] = f"positive case data missing: {e!r}"
    positives = [k for k, v in runs.items() if not v["expect_fail"]]
    verdict = "PASS" if all(runs[k]["ok"] for k in runs) else "FAIL"
    lanes = json.loads(Path(a.lanes).read_text()) if a.lanes else {}
    src = (S / "fx/lanes/SOURCE").read_text().strip() if (S / "fx/lanes/SOURCE").exists() else a.lanes
    return dict(verdict=verdict,
                transport_grade=("DIAG (g5r2b forwarded lanes; current assembly transport not measured)"
                                 if "g5r2b" in str(src) else a.grade),
                golden="numpy fp32 all-reduce / argmax reference (tools/qwen_coll_tp8_static_bench.vectors): every output word of all 8 dies, "
                       + ", ".join(f"{k}: " + "/".join(f"{n} {v['words_out']}w mm={v['mismatches']}" for n, v in runs[k].get('cases', {}).items()) for k in positives),
                cycles=cyc, mutants=mutants,
                stand_ins=["SerDes PHY = fixed-latency model PS=339, UCIe PU=20 (modelled off-chip legs)",
                           f"die forwarded-lane latencies from GEN {src} (LX {lanes.get('LX')}, LS {lanes.get('calendar', {}).get('LS')})",
                           "COLLIO SAFE/PLAND tile form (qfd_coll_face_*_pl) not selected: the tb instantiates the production parent with "
                           "defaults SAFE=0/PLAND=0 as the die top does; the PL face form is covered by QW-COLLIO bench11 per-face golds"],
                logs=logs, runs=runs)


def ovl4u(root, S, a):
    R = S / "runs"; out = {}; mutants = {}; logs = []; ok_all = True
    for c in (1, 2):
        sm = R / f"codec{c}" / "SUMMARY.txt"; logs += [f"runs/codec{c}.out", f"runs/codec{c}/SUMMARY.txt"]
        if not sm.exists():
            ok_all = False; out[f"codec{c}"] = dict(error="no SUMMARY.txt", tail=(R / f"codec{c}.out").read_text(errors="replace").splitlines()[-10:] if (R / f"codec{c}.out").exists() else [])
            continue
        txt = sm.read_text(); cfg = {}
        for m in re.finditer(r"^(\S+) expect=(\S+) got=(\S+) -> (\S+)", txt, re.M):
            cfg[m.group(1)] = dict(expect=m.group(2), got=m.group(3), ok=m.group(4) == "OK")
            ok_all &= m.group(4) == "OK"
            if m.group(1) != "pass":
                mutants[f"codec{c}_{m.group(1)}"] = "FAIL as required" if m.group(4) == "OK" else f"got {m.group(3)} (UNEXPECTED)"
        if "pass" not in cfg or len(cfg) < 5:
            ok_all = False
        d = dict(configs=cfg)
        pl = R / f"codec{c}" / "pass" / "run.log"
        if pl.exists():
            t = pl.read_text(errors="replace")
            users = {int(m.group(1)): dict(exchanges=int(m.group(2)), exchanges_compiled=int(m.group(3)), tokens=int(m.group(4)),
                                           tokens_compiled=int(m.group(5)), tok_s=float(m.group(6)))
                     for m in re.finditer(r"D2DOVL_USER (\d+) exchanges (\d+) \(compiled (\d+)\) tokens (\d+) \(compiled (\d+)\) tok/s ([\d.]+)", t)}
            mm = re.search(r"D2DOVL_MEAS H (\d+) frames C->K (\d+) K->C (\d+) aggregate ([\d.]+) tok/s", t)
            if mm and users:
                H = int(mm.group(1)); ntok = sum(u["tokens"] for u in users.values())
                d.update(H_frame=H, frames_C2K=int(mm.group(2)), frames_K2C=int(mm.group(3)), aggregate_tok_s_bench=float(mm.group(4)),
                         tokens_per_frame={u: v["tokens"] for u, v in sorted(users.items())},
                         exchanges_per_frame={u: v["exchanges"] for u, v in sorted(users.items())},
                         cycles_per_token_per_user={u: round(H / v["tokens"], 1) for u, v in sorted(users.items())},
                         tok_s_per_user_833ps={u: round(CLK_HZ * v["tokens"] / H, 1) for u, v in sorted(users.items())},
                         aggregate_cycles_per_token=round(H / ntok, 1), aggregate_tok_s_833ps=round(CLK_HZ * ntok / H, 1))
        out[f"codec{c}"] = d
    cyc = {k: v for k, v in out.get("codec2", {}).items() if k != "configs"}
    cyc["codec"] = 2
    if "H_frame" in out.get("codec1", {}):
        cyc["codec1_H_frame"] = out["codec1"]["H_frame"]; cyc["codec1_aggregate_tok_s_833ps"] = out["codec1"]["aggregate_tok_s_833ps"]
    if (S / "release_masters.txt").exists():
        return dict(verdict="PASS" if ok_all else "FAIL", dut=(S / "release_masters.txt").read_text().strip(),
                    golden="every C->K and K->C frame of the 4-user F16 frame: written frame == bench golden of its port "
                           "(producer word / kind-15 STATUS encoding / kind-5 KVN encoding), delivered in order bit-exact at "
                           "the receiver end on the compiled port/kind/beat with rx_user == sender user; KV pins: every "
                           "STATUS result and KVN word == the compute pins; per-user exchanges/tokens counted at the compute "
                           "master pins = compiled counts (tb_d2d_ovl_mu_rel checks)",
                    cycles=cyc, mutants=mutants,
                    stand_ins=["UCIe PHY = ot_qkvd_ucie_x64_phy_model (modelled off-chip leg; LAT = P_PHY - 2, the masters' "
                               "FDI pin flops are real)", "3-flop package bump of the forwarded epoch / link reset (modelled)",
                               "producers/consumers at the master pins are tb models (native CMD/Q, program witness, KVN x3, "
                               "HOST record, attention RESULT/STATUS, embedding row; result_v pulses for the STATUS codec); "
                               "the release masters (sf7 / sfm3), OVL sequencers, STATUS/KVN codecs, recovery, CRC and slot "
                               "SRAM links are assembly RTL",
                               "macro view ot_sram_1r1w_64x137_m1_r2c2_p192 from 545cdd4bc (the closed sf7w kit's view; not "
                               "in the assembly's asap7_memory_macros_v2)"],
                    logs=logs + [f"runs/codec{c}/{name}/run.log" for c in (1, 2)
                                  for name in ("pass", "asbuilt_one_playhead", "mut_collide", "mut_slot", "mut_user")]
                              + [f"runs/codec{c}/{name}" for c in (1, 2)
                                 for name in ("source.sha256", "verilator.txt")]
                              + ["release_masters.txt"], runs=out)
    return dict(verdict="PASS" if ok_all else "FAIL",
                golden="every C->K and K->C D2D frame of the 4-user F16 frame bit-exact against the compiled producer words "
                       "(tb_d2d_ovl_mu checks), per-user exchanges/tokens = compiled counts",
                cycles=cyc, mutants=mutants,
                stand_ins=["UCIe PHY = ot_qkvd_ucie_x64_phy_model (modelled off-chip leg)",
                           "producers/consumers at both ends are tb models emitting the compiled words (as on 10-19); the link "
                           "ends, OVL sequencers, codecs, CRC, LLR and SRAM are assembly RTL"],
                logs=logs, runs=out)


def ctx4u(root, S, a):
    R = S / "runs"; logs = []; mutants = {}; ok_all = True; detail = {}
    for s in ("0", "1", "2", "3", "4", "5", "full"):
        name = "full" if s == "full" else f"mut{s}"
        rl = R / f"c{s}" / name / "run.log"; logs.append(f"runs/c{s}/{name}/run.log")
        t = rl.read_text(errors="replace") if rl.exists() else ""
        if s == "0":
            ok = bool(re.search(r"^MUCTX_REAL_LINK_PASS", t, re.M))
        elif s == "full":
            ok = bool(re.search(r"^MUCTX_FULL_STREAM_DIAGNOSTIC_NATIVE_FAULT", t, re.M))
        else:
            ok = bool(re.search(r"^MUCTX_REAL_LINK_FAIL", t, re.M))
            mutants[name] = "FAIL as required" if ok else ("NOT RUN (no run.log)" if not t else "did not FAIL (UNEXPECTED)")
        ok_all &= ok
        if not t:
            out = R / f"c{s}.out"
            detail[name] = dict(ok=False, tail=out.read_text(errors="replace").splitlines()[-12:] if out.exists() else [])
        else:
            detail[name] = dict(ok=ok, last=[l for l in t.splitlines() if l.startswith("MUCTX_")][-3:])
    cyc = {}
    t = (R / "c0/mut0/run.log").read_text(errors="replace") if (R / "c0/mut0/run.log").exists() else ""
    runs = {}
    for m in re.finditer(r"^MUCTX_(SLOT|HOST_TX|WIRE|LOAD) cycle=(\d+)(?: run=(\d+))?(.*)$", t, re.M):
        k, c, r = m.group(1), int(m.group(2)), m.group(3)
        if r is None:   # LOAD lines carry no run=: attach to the last run seen
            r = max(runs) if runs else "0"
        runs.setdefault(r, {}).setdefault(k, []).append(c)
    per = {}
    for r, ev in sorted(runs.items(), key=lambda x: int(x[0])):
        if all(k in ev for k in ("SLOT", "HOST_TX", "WIRE", "LOAD")):
            per[r] = dict(slot_to_host_tx=ev["HOST_TX"][0] - ev["SLOT"][0], host_tx_to_wire=ev["WIRE"][0] - ev["HOST_TX"][0],
                          wire_to_load=ev["LOAD"][0] - ev["WIRE"][0], slot_to_load=ev["LOAD"][0] - ev["SLOT"][0], slot=ev["SLOT"][0])
    if per:
        f = per[min(per, key=int)]
        cyc = dict(slot_to_host_tx=f["slot_to_host_tx"], host_tx_to_wire=f["host_tx_to_wire"], wire_to_load=f["wire_to_load"],
                   slot_to_load=f["slot_to_load"], runs=len(per), per_run=per)
        slots = [per[r]["slot"] for r in sorted(per, key=int)]
        if len(slots) > 1:
            cyc["token_period_spacing"] = sorted({b - a_ for a_, b in zip(slots, slots[1:])})
    return dict(verdict="PASS" if ok_all else "FAIL",
                golden="config 0: every delivered context record = the SU host-port reference (MUCTX_SU_REF identical, MUCTX_LOAD ctx words), "
                       "no native/abort/transport fault; full: documented later-producer diagnostic fault",
                cycles=cyc, mutants=mutants,
                stand_ins=["UCIe PHY = ot_qkvd_ucie_x64_phy_model (modelled off-chip leg)",
                           "host-side record producer and token-period slots are tb stimulus (off-chip host leg)"],
                logs=logs, runs=detail)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("stage", choices=("tp8", "ovl4u", "ctx4u")); ap.add_argument("runroot", type=Path)
    ap.add_argument("--grade", default="RTL-functional (source assembly)"); ap.add_argument("--lanes")
    ap.add_argument("--stage-dir", help="run directory under RUNROOT (default: the stage name; ovl4u --release-masters: ovl4u_rel)")
    a = ap.parse_args(); root = a.runroot.resolve(); S = root / (a.stage_dir or a.stage)
    body = dict(tp8=tp8, ovl4u=ovl4u, ctx4u=ctx4u)[a.stage](root, S, a)
    res = dict(stage=a.stage, grade=a.grade, src_commit=asm_commit(root), **body)
    ov = S / "ovl_overlay.txt"
    if ov.exists():
        res["stand_ins"] = ["OVL link end overlay: " + ov.read_text().strip()] + res["stand_ins"]
    cp = S / "compiler_patch.txt"
    if cp.exists():
        res["compiler_patch"] = cp.read_text().strip()
    (S / "result.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps({k: res[k] for k in ("stage", "grade", "src_commit", "verdict", "cycles", "mutants")}, indent=1, default=str))


if __name__ == "__main__":
    main()
