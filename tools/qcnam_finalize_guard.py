#!/usr/bin/env python3
"""Fail-closed QC-NAM orchestration; arithmetic and verdicts stay at d2631dd9.

Default is a read-only readiness check. --finalize snapshots completed evidence,
invokes the ORIGINAL pinned finalizer, and publishes with exclusive creation.
Never resumes jobs, removes checkpoints, changes thresholds, or enables nfold.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

PIN = "d2631dd9051c30d7ab1aeab6fdaab4f9200d3f5a"
WT = Path("/tmp/claude-1000/wt/qcnam-run")
RUNS = Path("/tmp/claude-1000/qcnam/runs")
JOBS = Path("/tmp/claude-1000/queue/qcnam_jobs")
SNAP = Path("/home/ubuntu/.cache/huggingface/hub/models--deepseek-ai--DeepSeek-V4.1-Flash/snapshots/dba1be0a40aa45a94ad051997016db3960a90277")
FREE = ["a", "a2", "b", "b_nam"]
CORE = FREE + ["b_tf", "b_nam_tf", "a2_tf"]
SPECS = {
    "core": dict(windows=16, ctx=2048, mmlu=200, stress=True, batch=4, modes=",".join(CORE), tf_chunks=2),
    "mmlu1000": dict(windows=0, ctx=2048, mmlu=1000, stress=False, batch=4, modes=",".join(FREE), tf_chunks=0),
    "long": dict(windows=4, ctx=8192, mmlu=0, stress=False, batch=1, modes=",".join(FREE), tf_chunks=0),
}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for data in iter(lambda: f.read(1024 * 1024), b""):
            h.update(data)
    return h.hexdigest()


def git(*args):
    return subprocess.check_output(["git", "-C", str(WT), *args], text=True).strip()


def literal(path, name):
    for node in ast.parse(Path(path).read_text()).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise ValueError(f"missing pre-registration {name}")


def active_jobs():
    found = []
    for p in Path("/proc").glob("[0-9]*"):
        try:
            argv = p.joinpath("cmdline").read_bytes().decode().split("\0")[:-1]
            if any(a in (str(JOBS / "laneA.sh"), str(JOBS / "laneB.sh")) for a in argv) or (
                any(Path(a).name in ("deepseek_v41_nam_quality.py", "deepseek_v41_greedy_reference.py") for a in argv)
                and p.joinpath("cwd").resolve() == WT
            ):
                found.append(dict(pid=int(p.name), argv=argv, cwd=str(p.joinpath("cwd").resolve()),
                                  start_ticks=p.joinpath("stat").read_text().rsplit(")", 1)[1].split()[19]))
        except (OSError, UnicodeError):
            continue
    return sorted(found, key=lambda r: r["pid"])


def source_identity():
    require(git("rev-parse", "HEAD") == PIN, "run worktree moved from registered pin")
    require(not git("status", "--porcelain"), "run worktree is dirty")
    paths = git("ls-files", "tools/*.py").splitlines()
    return {p: digest(WT / p) for p in paths}


def snapshot_identity():
    # HF weight symlinks resolve to content-addressed cache blobs. Keep their
    # identity plus size/mtime; never re-read hundreds of GB during live lanes.
    files = {}
    for p in sorted(SNAP.rglob("*")):
        if p.is_file() and "__pycache__" not in p.parts:
            st = p.stat()
            files[str(p.relative_to(SNAP))] = dict(target=str(p.resolve()), size=st.st_size, mtime_ns=st.st_mtime_ns)
            if p.suffix in (".json", ".py"):
                files[str(p.relative_to(SNAP))]["sha256"] = digest(p)
    require(files and "config.json" in files, "snapshot unavailable")
    return files


def completed(directory):
    status = (directory / "status").read_text().splitlines()
    require(status and status[-1].startswith("end rc=0 "), f"{directory.name}: no successful lane exit")
    require(any(l.startswith("done ") for l in (directory / "log.txt").read_text().splitlines()),
            f"{directory.name}: no tool completion marker")


def validate_gen(gen):
    require(len(gen) == 8, "greedy reference needs eight prompts")
    require([g["name"] for g in gen] == [f"gen{i}" for i in range(8)], "greedy prompt identities")
    for g in gen:
        require(not g.get("partial") and g["prompt_len"] == 128 and len(g["ids"]) == 256,
                "greedy reference is partial or truncated")
        require(all(type(i) is int and 0 <= i < 129280 for i in g["ids"]), "invalid greedy token")


def validate_run(name, rec, raw, gen):
    require(rec["schema"] == "opentallas.deepseek-v41-flash-norm-after-matvec.v1.run", f"{name}: schema")
    a = rec["args"]
    for k, v in SPECS[name].items():
        require(a[k] == v, f"{name}: unexpected {k}")
    require(a["max_layers"] == 0 and a["mmlu_seed"] == 0 and a["resume"] is True, f"{name}: reduced/changed job")
    require(a["snapshot"] == str(SNAP), f"{name}: snapshot provenance")
    for key, suffix in (("out", "run.json"), ("raw_out", "raw.json"), ("partial", "partial.json"), ("work", "work")):
        require(a[key] == str(RUNS / name / suffix), f"{name}: {key} provenance")
    require(a["gen_file"] == (str(RUNS / "gen/gen.json") if name == "long" else None), f"{name}: greedy provenance")
    require(a["stress_ctx"] == 2048, f"{name}: stress context")
    require([l["layer"] for l in rec["layers"]] == list(range(40)), f"{name}: incomplete depth")
    metrics = CORE[1:] if name == "core" else FREE[1:]
    instruments = ["b", "b_nam"] + (["b_tf", "b_nam_tf"] if name == "core" else [])
    for l in rec["layers"]:
        for key in ("router", "hidden_rel_rms", "router_by_pos"):
            require(set(l[key]) == set(metrics), f"{name}: missing {key} at layer {l['layer']}")
        # These are the pinned vehicle's index_source_layers; reused index
        # state at other layers produces no new selection measurement.
        for key in ("index", "index_by_pos"):
            require(set(l[key]) == (set(metrics) if l["layer"] in (2, 8, 14, 20, 24, 28, 32, 36) else set()), f"{name}: missing {key}")
        for metric, bucket, count, flips, rate in (
            ("router", "router_by_pos", "tokens", "tokens_with_flip", "flip_rate"),
            ("index", "index_by_pos", "queries", "queries_with_diff", "query_flip_rate"),
        ):
            for m, d in l[metric].items():
                b = l[bucket][m]
                require(d[count] > 0 and 0 <= d[flips] <= d[count], f"{name}: invalid selection samples")
                require(abs(d[rate] - d[flips] / d[count]) < 1e-12, f"{name}: selection rate mismatch")
                require(len(b[count]) == len(b["flips"]) == 9 and sum(b[count]) == d[count]
                        and sum(b["flips"]) == d[flips], f"{name}: incomplete position buckets")
                require(all(0 <= f <= n for f, n in zip(b["flips"], b[count])), f"{name}: invalid position counts")
        for m in instruments:
            ins = l["instr"][m]
            require(all(ins[k] for k in ("quant", "mv", "norm")), f"{name}: missing instrumentation {m}")
            if m.startswith("b_nam"):
                require(ins["probe"], f"{name}: missing folded-consumer probes")
                for p in ins["probe"].values():
                    require(all(p[k]["rows"] > 0 and "mean" in p[k] for k in ("e_b", "e_n")), f"{name}: incomplete probe")
            require(all("nan" in d and "inf" in d for d in ins["norm"].values()), f"{name}: missing norm checks")
            for k in ("quant", "mv"):
                for d in ins[k].values():
                    require(all(f in d for f in ("nan_in", "inf_in", "nan_out", "inf_out")), f"{name}: missing finite checks")
            require(all("saturated" in d for d in ins["quant"].values()), f"{name}: missing saturation")
        for category in ("quant", "mv", "norm"):
            require(set(l["instr"]["b"][category]) == set(l["instr"]["b_nam"][category]), f"{name}: unmatched sites")
    require(set(raw) == set(FREE), f"{name}: missing free-running raw modes")
    for m in ("b", "b_nam"):
        require(rec["head_instr"][m]["norm"] and rec["head_instr"][m]["mv"], f"{name}: missing head checks")
    expected = {"wt": SPECS[name]["windows"], "mmlu": SPECS[name]["mmlu"],
                "stress": 4 if name == "core" else 0, "gen": 8 if name == "long" else 0}
    for m, rows in raw.items():
        require({k: sum(r["kind"] == k for r in rows) for k in expected} == expected, f"{name}: incomplete sequences {m}")
        require(len(rows) == sum(expected.values()), f"{name}: extra sequences")
        mm = [r["mmlu_index"] for r in rows if r["kind"] == "mmlu"]
        require(len(set(mm)) == len(mm), f"{name}: duplicate MMLU")
        gs = []
        for i, r in enumerate(rows):
            require(all(k in r for k in ("nan_logits", "inf_logits")), f"{name}: missing logit checks")
            ref = raw["a"][i]
            for k in ("kind", "name", "mmlu_index", "answer", "prompt_len", "ids_next"):
                require(r.get(k) == ref.get(k), f"{name}: misaligned paired rows")
            if r["kind"] == "mmlu":
                require(type(r["pick"]) is int and 0 <= r["pick"] < 4, f"{name}: invalid MMLU pick")
            else:
                length = (8191 if name == "long" else 2047) if r["kind"] != "gen" else 255
                require(all(len(r[k]) == length for k in ("nll", "arg", "margin")), f"{name}: truncated token scores")
                if m != "a":
                    require(len(r["kl_a"]) == length, f"{name}: truncated KL")
                if r["kind"] == "gen":
                    gs.append(r)
        if name == "long":
            require([r["name"] for r in gs] == [g["name"] for g in gen], "greedy scoring names")
            require(all(r["prompt_len"] == 128 and r["ids_next"] == g["ids"][128:] for r, g in zip(gs, gen)), "greedy scoring tokens")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--observation", type=Path, required=True, help="committed live-job/source observation")
    ap.add_argument("--finalize", action="store_true")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    observation = json.loads(args.observation.read_text())
    require(source_identity() == observation["source_sha256"], "observed source identity changed")
    live = active_jobs()
    if live:
        print(json.dumps(dict(ready=False, live=live, reason="required lanes still live; no restart or finalization"), indent=2))
        return 2
    require(snapshot_identity() == observation["snapshot_identity"], "observed snapshot identity changed")
    require({p.name: digest(p) for p in JOBS.glob("*.sh")} == observation["job_sha256"], "lane scripts changed")
    if args.finalize:
        require(args.out is not None and not args.out.exists(), "output must be new; verdicts are immutable")
        args.out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="qcnam-evidence-", dir=args.out.parent if args.finalize else None) as td:
        evidence = Path(td)
        hashes = {}
        for name in (*SPECS, "gen"):
            d = RUNS / name
            completed(d)
            dest = evidence / name
            dest.mkdir()
            for file in (["gen.json"] if name == "gen" else ["run.json", "raw.json"]) + ["status", "log.txt"]:
                src, dst = d / file, dest / file
                before = digest(src)
                shutil.copyfile(src, dst)
                require(before == digest(dst) == digest(src), f"evidence changed while freezing {src}")
                hashes[f"{name}/{file}"] = before
        gen = json.loads((evidence / "gen/gen.json").read_text())
        validate_gen(gen)
        records = {}
        for name in SPECS:
            rec = json.loads((evidence / name / "run.json").read_text())
            raw = json.loads((evidence / name / "raw.json").read_text())
            validate_run(name, rec, raw, gen)
            records[name] = raw
        core_mm = {r["mmlu_index"] for r in records["core"]["a"] if r["kind"] == "mmlu"}
        full_mm = {r["mmlu_index"] for r in records["mmlu1000"]["a"]}
        require(core_mm <= full_mm and len(full_mm) == 1000, "MMLU pooled sample provenance")
        require(not active_jobs(), "lane became active during validation")
        if not args.finalize:
            print(json.dumps(dict(ready=True, source_commit=PIN, evidence_sha256=hashes), indent=2))
            return 0
        meta = evidence / "meta.json"
        meta.write_text(json.dumps(dict(source_commit=PIN, observation=observation, evidence_sha256=hashes,
                                       driver_sha256=digest(__file__))))
        result = evidence / "verdict.json"
        subprocess.run(["python3", str(WT / "tools/deepseek_v41_nam_quality.py"), "--finalize",
                        *[f"{n}={evidence / n}" for n in SPECS], "--meta", str(meta), "--out", str(result)],
                       cwd=WT, check=True, env={**os.environ, "CUDA_VISIBLE_DEVICES": ""})
        verdict = json.loads(result.read_text())
        require(verdict["stability_rule"] == literal(WT / "tools/deepseek_v41_nam_quality.py", "STABILITY_RULE"), "rule changed")
        require(verdict["threshold"] == literal(WT / "tools/deepseek_v41_deployment_quality.py", "THRESHOLD"), "threshold changed")
        require(source_identity() == observation["source_sha256"] and not active_jobs(), "provenance changed during finalization")
        # Hard-link is atomic and refuses to replace any earlier PASS or FAIL.
        os.link(result, args.out)
        print(json.dumps(dict(output=str(args.out), verdict=verdict["verdict"], hardware_adopted=False), indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, KeyError, OSError, TypeError, json.JSONDecodeError) as exc:
        print(json.dumps(dict(ready=False, error=str(exc))))
        raise SystemExit(2)
