#!/usr/bin/env python3
"""Write the lever item-3 record (SU operator-fusion `_kr` core: lint successor + matched exactness re-run).

    python3 tools/dsrom_lever_record_su_kr.py --lint-dir DIR --run-dir DIR --run-root WT \
        [--out results/rtl/dsrom_system_rtl_20261003/levers/su_kr_lint.json]

--lint-dir: camp_lint_{orig,kr,lv}.log/.cmd.json (the decode campaign's own lint step, tools/dsrom_lever_su_kr.py
lint) and kr_lint_head.log / kr_lv_strict.log with kr_cmd.json / kr_lv_cmd.json (the W11 strict command of
results/rtl/w11_main_compatible_20261001/main_kr_lint_command.json).  --run-dir: {u00,f00,u2517,f2517}.json
(+ .log) from `tools/dsrom_lever_su_kr.py run --pregen` on the run host.  --run-root: the run host's source tree, or
a JSON {path: sha256} of it taken there (the host is not mounted here).  --images-dir: the local image step's logs
(images_k{0,40}.log) and the pregen meta (img_k{0,40}/_image_args.json).
"""
import argparse
import hashlib
import json
import re
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / "results/rtl/w11_main_compatible_20261001/matched_pairs.json"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def kinds(log: Path):
    t = log.read_text() if log.exists() else ""
    c = Counter(re.sub(r":\d+:\d+:", ":", l).split(": ")[0] + ": " + re.sub(r":\d+:\d+:", ":", l).split(": ", 1)[-1][:90]
                for l in t.splitlines() if l.startswith("%Warning"))
    rc = re.search(r"RC (\d+)", t)
    return dict(warnings=sum(c.values()), by_message=dict(c),
                returncode=int(rc.group(1)) if rc else (0 if not c and "%Error" not in t else 1))


def _wall(log: Path):
    if not log.exists():
        return None
    ts = re.findall(r"^(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ)$", log.read_text(), re.M)
    return dict(start=ts[0], end=ts[-1]) if len(ts) >= 2 else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lint-dir", type=Path, required=True)
    ap.add_argument("--run-dir", type=Path, required=True)
    ap.add_argument("--run-root", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=ROOT / "results/rtl/dsrom_system_rtl_20261003/levers/su_kr.json")
    ap.add_argument("--images-dir", type=Path)
    ap.add_argument("--run-host", default="ot-epyc1tb")
    a = ap.parse_args()
    L = a.lint_dir
    lint = {
        "campaign_lint_original_core": kinds(L / "camp_lint_orig.log"),
        "campaign_lint_kr_fork": kinds(L / "camp_lint_kr.log"),
        "campaign_lint_kr_successor": kinds(L / "camp_lint_lv.log"),
        "strict_w11_kr_command_kr_fork": kinds(L / "kr_lint_head.log"),
        "strict_w11_kr_command_kr_successor": kinds(L / "kr_lv_strict.log"),
    }
    cmds = {k: json.loads((L / f).read_text()) for k, f in (("campaign_lint_kr_successor", "camp_lint_lv.cmd.json"),
                                                             ("campaign_lint_original_core", "camp_lint_orig.cmd.json"),
                                                             ("strict_kr_successor", "kr_lv_cmd.json"))}
    ref = {p["fused"]: p for p in json.loads(REF.read_text())["pairs"]}
    runs = {}
    for name in ("u00", "f00", "u2517", "f2517"):
        p = a.run_dir / f"{name}.json"
        if not p.exists():
            runs[name] = dict(status="missing")
            continue
        r = json.loads(p.read_text())
        s = r["single_step"] if isinstance(r["single_step"], dict) else eval(r["single_step"])  # noqa: S307
        runs[name] = dict(status=r["status"], cycles=s["cycles"], next_token=s["next_token"],
                          isa_next_token=s["isa_next_token"], fault=s["fault"],
                          logit_mismatches=s["logit_mismatches"], vector_memory_mismatches=s["vector_memory_mismatches"],
                          kv_cache_mismatches=s["kv_cache_mismatches"], su_busy=s["unit_busy_cycles"]["su"],
                          functional_pass=s["pass"], golden_next_token=s.get("golden_next_token"),
                          lint_returncode=r["verilator_lint"]["returncode"],
                          lint_messages=r["verilator_lint"]["messages"][:6],
                          wall_utc=_wall(a.run_dir / f"{name}.log"),
                          operator_fusion={k: v for k, v in r.get("operator_fusion", {}).items() if k != "sources_sha256"},
                          record_sha256=sha(p))
    comp = {}
    for un, fn in (("u00", "f00"), ("u2517", "f2517")):
        r0 = ref[fn]
        if runs[un].get("cycles") and runs[fn].get("cycles"):
            u, f = runs[un]["cycles"], runs[fn]["cycles"]
            comp[f"{un}/{fn}"] = dict(
                unfused=u, fused=f, saved=u - f, fraction=round((u - f) / u, 6),
                su_busy=dict(unfused=runs[un]["su_busy"], fused=runs[fn]["su_busy"]),
                same_token=runs[un]["next_token"] == runs[fn]["next_token"] == runs[fn]["golden_next_token"],
                recorded=dict(unfused=r0["unfused_cycles"], fused=r0["fused_cycles"], saved=r0["saved_cycles"]),
                cycles_reproduce_recorded=(u == r0["unfused_cycles"] and f == r0["fused_cycles"]))
    succ = {str(p.relative_to(ROOT)): sha(p) for p in (ROOT / "rtl/dsrom_sys/levers/ot_hdc_core_v41x_kr_lv.sv",
                                                       ROOT / "rtl/dsrom_sys/levers/ot_hdc_v41x_me_adapt_lv.sv",
                                                       ROOT / "tools/dsrom_lever_su_kr.py", Path(__file__))}
    replaced = {str(p.relative_to(ROOT)): sha(p) for p in (ROOT / "rtl/hdc/v41x/ot_hdc_core_v41x_kr.sv",
                                                           ROOT / "rtl/hdc/v41x/ot_hdc_v41x_me_adapt.sv",
                                                           ROOT / "rtl/hdc/v41x/ot_hdc_core_v41x.sv",
                                                           ROOT / "tools/w11_su_fuse_die.py",
                                                           ROOT / "tools/rtl_hdc_v41x_decode_campaign.py")}
    if a.run_root.is_file():
        rr = json.loads(a.run_root.read_text())
        wt_same = {k: rr.get(k) == v for k, v in {**succ, **replaced}.items() if not k.startswith("tools/dsrom_lever_record")}
    else:
        wt_same = {k: (a.run_root / k).exists() and sha(a.run_root / k) == v for k, v in {**succ, **replaced}.items()
                   if not k.startswith("tools/dsrom_lever_record")}
    imgs = {}
    if a.images_dir:
        for k in (0, 40):
            m = a.images_dir / f"img_k{k}/_image_args.json"
            lg = a.images_dir / f"images_k{k}.log"
            imgs[f"sukr{k}"] = dict(meta=json.loads(m.read_text()) if m.exists() else None, wall_utc=_wall(lg),
                                    expect_json_sha256=sha(a.images_dir / f"img_k{k}/expect.json")
                                    if (a.images_dir / f"img_k{k}/expect.json").exists() else None)
    ok_lint = lint["campaign_lint_kr_successor"]["returncode"] == 0 and \
        lint["strict_w11_kr_command_kr_successor"]["returncode"] == 0
    ok_runs = all(runs[n].get("status") == "pass" for n in runs)
    status = "pass" if ok_lint and ok_runs else ("lint_pass_runs_pending" if ok_lint else "fail")
    rec = dict(
        schema="opentallas.rtl.dsrom_lever_su_kr.v1", status=status,
        lever="free-levers audit L2: SU operator fusion (`_kr` lane-register core fork, tools/w11_su_fuse_die.py --sukr)",
        finding=("The audit's blocker 'PINMISSING i_preloaded' is stale: the fork at HEAD connects i_preloaded and the "
                 "shared_* pins (37ac8d2ef). What still fails the decode campaign's -Wall lint step (the step that "
                 "turns the functionally exact matched pairs into status 'fail') is 18 warnings, ALL inherited from "
                 "code the fork shares with the original core: 9 SELRANGE (FULL-profile-only fields QE_UNROUNDED / "
                 "COLL_* sliced past the reduced 1536-bit instruction inside a run-time FULL_SHAPE guard), 1 PINMISSING "
                 "(u_qe.qr_issue_ready), 8 GENUNNAMED (ot_hdc_v41x_me_adapt.sv:278-302, not a fork file). The "
                 "ORIGINAL core fails the same lint at HEAD with 27 warnings (these 18 + 9 PINMISSING it never "
                 "connects), so the unfused original is no cleaner than the fork."),
        fix=("rtl/dsrom_sys/levers/ot_hdc_core_v41x_kr_lv.sv: FULL-only slices from ir_w = 2048'(ir) (equal to ir "
             "when FULL_SHAPE, never selected otherwise); u_qe.qr_issue_ready tied 1'b1 (only read under "
             "WEIGHT_STALL != 0, which this instance leaves at its 0 default). "
             "rtl/dsrom_sys/levers/ot_hdc_v41x_me_adapt_lv.sv: the four if/else generate blocks labelled. "
             "Both keep their module names (source-list swap, as the fork itself). No behaviour change intended; "
             "the matched pairs re-run checks it."),
        cost="cheap: 3 lint-only edits in 2 successor files",
        lint=lint, matched_pair_rerun=runs, cycles=comp,
        execution=dict(images="local (python golden/ISA/program/images need `tokenizers`), "
                              "tools/dsrom_lever_su_kr.py images --pregen; shipped by rsync",
                       build_and_simulation=f"{a.run_host}, Verilator 5.050 (pinned), tools/dsrom_lever_su_kr.py run "
                                            "--pregen (campaign unchanged except the image step reads the shipped "
                                            "directory, asserted to match sukr/params/units/args)",
                       image_step=imgs),
        reference=dict(path=str(REF.relative_to(ROOT)), sha256=sha(REF), pairs=list(ref.values())),
        commands=dict(lint_campaign="python3 tools/dsrom_lever_su_kr.py lint [--orig | --pinned] --cmd-json C.json",
                      images="python3 tools/dsrom_lever_su_kr.py images --pregen IMG_K{0,40} --sukr {0,40} "
                             "--units he,me,su --single-only --output X.json",
                      u00="python3 tools/dsrom_lever_su_kr.py run --pregen IMG_K0 --sukr 0 --units he,me,su --single-only --output U00.json",
                      f00="python3 tools/dsrom_lever_su_kr.py run --pregen IMG_K40 --sukr 40 --units he,me,su --single-only --output F00.json",
                      u2517="... run --pregen IMG_K0 --sukr 0 --subcast 25 --suret 17 ... --output U2517.json",
                      f2517="... run --pregen IMG_K40 --sukr 40 --subcast 25 --suret 17 ... --output F2517.json",
                      expanded=cmds),
        run_root=str(a.run_root), run_root_sources_identical=wt_same,
        source_sha256=dict(successors=succ, replaced_or_wrapped=replaced),
        claim_boundary=("Reduced V4.1 token, one decode step at position 7 on the reduced core (HE, ME, SU "
                        "re-specified), Verilator 5.050. Both matched pairs re-run: 0/0 wire stages (u00/f00) and the "
                        "25/17 pair (u2517/f2517). No SS/FF closure of the lane registers, no full-shape or "
                        "W17-runtime-core port (the fork is of ot_hdc_core_v41x, not rtl/w17_runtime), no adoption."),
        recorded_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1) + "\n")
    print(status, json.dumps(dict(lint={k: v["returncode"] for k, v in lint.items()}, runs=runs, cycles=comp), indent=1))


if __name__ == "__main__":
    main()
