#!/usr/bin/env python3
"""Connected rank0/SM0 descriptor replay; other 96-rank rows are layout-only."""
import argparse
import hashlib
import json
from pathlib import Path
import resource
import shutil
import subprocess
import tarfile
import time

from w19_baseline_loader import load_image
from w19_payload_loader_gate import audit, git_bytes
from w19_rank_dispatch import dispatch, rank_layout

ROOT = Path(__file__).resolve().parents[1]
BASE = "1f74ac380"
ARCHIVE = "results/rtl/w19_payload_fixtures_3b15b18e.tar.gz"
PREBUILD = "results/uarch/w19_rank_baseline_prebuild.json"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rows(path):
    pairs = [line.split() for line in Path(path).read_text().splitlines() if not line.startswith("#")]
    if any(len(p) != 2 for p in pairs) or len({p[0] for p in pairs}) != len(pairs):
        raise ValueError("Malformed or duplicate result rows")
    return {int(r): int(bits, 16) for r, bits in pairs}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--record", type=Path, required=True)
    a = ap.parse_args()
    a.work, a.record = a.work.resolve(), a.record.resolve()
    if a.work.exists() or a.record.exists():
        ap.error("fresh work/record paths required; never overwrite verdicts")
    if a.work.is_relative_to(ROOT) or a.record.is_relative_to(ROOT):
        ap.error("outputs must be outside the pinned worktree")
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT).strip():
        ap.error("clean committed source required")
    a.work.mkdir(parents=True)
    a.record.parent.mkdir(parents=True, exist_ok=True)
    result = dict(schema="opentallas.w19.rank_baseline_dispatch.v1", status="fail",
                  source_commit=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                  enabled_default=False, fresh_checkpoint_golden=False,
                  scope="18 actual rank0/SM0 retained expert descriptors per run; 96x32 host layout only",
                  adoption="Host dispatch gate OFF; accepted256B baseline exercised; compact adapter REJECTED and excluded; SS/FF, routing and >=1% composed model gain unresolved",
                  prebuild_sha256=sha(ROOT / PREBUILD), commands=[], runs=[])

    def run(command, name):
        started = time.monotonic()
        with (a.work / (name + ".log")).open("w") as log:
            p = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=180)
        result["commands"].append(dict(argv=command, exit_code=p.returncode,
                                       elapsed_seconds=time.monotonic()-started,
                                       log_sha256=sha(a.work / (name + ".log"))))
        if p.returncode:
            raise RuntimeError(f"{name} exited {p.returncode}; retained log at {a.work}")

    try:
        model = json.loads((ROOT / PREBUILD).read_text())
        for path, expected in model["pins"].items():
            if sha(ROOT / path) != expected:
                raise ValueError("Changed prebuild prerequisite: " + path)
        available = int(next(line.split()[1] for line in Path("/proc/meminfo").read_text().splitlines() if line.startswith("MemAvailable:"))) * 1024
        disk = shutil.disk_usage(a.work).free
        if available < 512*1024**2 or disk < 256*1024**2:
            raise RuntimeError("Insufficient headroom for one bounded SM/64MiB behavioral HBM")
        result["admission"] = dict(available_memory_bytes=available, free_disk_bytes=disk,
                                   physical_simulated_SMS=1, HBM_model_bytes=67108864,
                                   full96_admitted=False)
        run(["python3", "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_w19_rank_dispatch.py"], "layout_tests")
        archive = a.work / "fixtures.tar.gz"
        archive.write_bytes(git_bytes(BASE, ARCHIVE))
        result["fixture_archive"] = dict(source_commit=BASE, path=ARCHIVE, sha256=sha(archive))
        fixtures = a.work / "fixtures"
        fixtures.mkdir()
        with tarfile.open(archive) as t:
            members = t.getmembers()
            if len(members) != 240:
                raise ValueError("Unexpected retained fixture archive")
            for member in members:
                p = Path(member.name)
                if not member.isfile() or len(p.parts) != 2 or not p.parts[0].startswith("s_") or p.name not in ("cfg.hex", "lines.hex", "x.hex", "out.txt"):
                    raise ValueError("Unsafe archive member")
                target = fixtures / p
                target.parent.mkdir(exist_ok=True)
                with target.open("xb") as out:
                    out.write(t.extractfile(member).read())
        historical = ROOT / "results/rtl/w19_payload_transport_historical_3b15b18e.json"
        old = json.loads(historical.read_text())
        matched = audit(old, fixtures)
        chosen = {(c["expert_id"], c["tag"].split()[-1]): (c, d) for c, d in matched
                  if not c["stall"] and not c["corrupt_exponent"] and not c["row_swap"]}
        ids = sorted({key[0] for key in chosen})
        layout = rank_layout(0, model["stack_sm_quadrants"])
        commands = dispatch(layout, ids, stage="input", enable=True)
        commands += dispatch(layout, ids, stage="output", producer_ready=True, enable=True)
        commands = [x for x in commands if x["sm"] == 0]
        if len(commands) != 18:
            raise ValueError("Missing selected-expert fixtures")
        result["descriptors"] = commands
        result["historical_reference"] = dict(source_commit=old["source_commit"], record_sha256=sha(historical),
                                               audited_cases=60, claim="retained outputs; no fresh golden promotion")
        sources, pins = [], {}
        for path, expected in old["sm_snapshot"]["source_sha256"].items():
            dest = a.work / Path(path).name
            dest.write_bytes(git_bytes(old["sm_snapshot"]["commit"], path))
            if sha(dest) != expected:
                raise ValueError("Changed W13 source snapshot")
            sources.append(str(dest)); pins[path] = expected
        local = ["rtl/gpu/ot_gpu_expert_fetch.sv",
                 "rtl/hdc/kv/ot_hdc_hbm_model.sv", "rtl/test/tb_w19_rank_dispatch.sv"]
        for path in local:
            if path != local[-1] and sha(ROOT / path) != old["source_sha256"][path]:
                raise ValueError("Changed production RTL " + path)
            sources.append(str(ROOT / path)); pins[path] = sha(ROOT / path)
        for path in ("tools/w19_rank_dispatch.py", "tools/w19_rank_dispatch_gate.py", "tools/w19_payload_loader.py", "tools/w19_baseline_loader.py",
                     "tools/w19_payload_loader_gate.py", "tests/test_w19_rank_dispatch.py"):
            pins[path] = sha(ROOT / path)
        result["source_sha256"] = pins
        binary = a.work / "gate.vvp"
        run(["iverilog", "-g2012", "-s", "tb_w19_rank_dispatch", "-Ptb_w19_rank_dispatch.NC=1", "-o", str(binary)] + sources, "compile")
        result["binary_sha256"] = sha(binary)
        for mode in ("normal", "stalled"):
            work = a.work / mode
            work.mkdir()
            plan, loads, references = [], [], []
            with (work / "stack0.hex").open("x") as combined:
                for index, descriptor in enumerate(commands):
                    c, source = chosen[descriptor["expert_id"], descriptor["operation"]]
                    if c["sm_rows"] != descriptor["rows"] or c["rtl"]["lines"] != descriptor["payloads"]:
                        raise ValueError("Rank geometry differs from actual fixture")
                    case = work / ("case" + str(index)); case.mkdir()
                    shutil.copyfile(source / "x.hex", case / "x.hex")
                    cfg = [int(x,16) for x in (source / "cfg.hex").read_text().splitlines()]
                    cfg[7] = int(mode == "stalled")
                    (case / "cfg.hex").write_text("".join(f"{v:08x}\n" for v in cfg))
                    load = load_image(source / "lines.hex", case / "sectors.hex",
                                      expected_sha256=c["rtl"]["fixture_sha256"]["lines.hex"],
                                      payloads=descriptor["payloads"], expert_id=descriptor["expert_id"],
                                      base_line=descriptor["cfg_base"], expert_stride_lines=descriptor["cfg_exp_lines"],
                                      sm_offset_lines=descriptor["cfg_off"])
                    if load["first_sector"] != descriptor["first_sector"]:
                        raise ValueError("Loader address differs from dispatch")
                    combined.write((case / "sectors.hex").read_text())
                    loads.append(load); references.append(source / "out.txt")
                    plan.extend([descriptor["cfg_base"], descriptor["cfg_exp_lines"], descriptor["cfg_off"],
                                 index+1, descriptor["first_sector"], descriptor["first_sector"]+descriptor["sector_count"]])
            (work / "dispatch.hex").write_text("".join(f"{v:08x}\n" for v in plan))
            run(["vvp", "-n", str(binary), "+DIR=" + str(work)], mode)
            verdicts = []
            for index, reference in enumerate(references):
                output = work / ("case"+str(index)) / "out.txt"
                verdicts.append(dict(index=index, pass_output=rows(output) == rows(reference),
                                     output_sha256=sha(output), reference_sha256=sha(reference),
                                     staged_cfg_sha256=sha(output.parent / "cfg.hex"),
                                     staged_x_sha256=sha(output.parent / "x.hex")))
            text = (a.work / (mode+".log")).read_text()
            valid = all(x["pass_output"] for x in verdicts) and "RANK_DISPATCH PASS descriptors=18 resets=1 physical_SM_instances=1" in text
            result["runs"].append(dict(mode=mode, pass_output=valid, cases=verdicts, loader_records=loads,
                                       stack_image_sha256=sha(work / "stack0.hex"), dispatch_sha256=sha(work / "dispatch.hex")))
            if not valid:
                raise RuntimeError(mode + " descriptor output differs from retained exact output")
        result["status"] = "pass"
    except (OSError, ValueError, RuntimeError, AssertionError, KeyError, subprocess.SubprocessError) as exc:
        result["error"] = str(exc)
    result["child_peak_RSS_KiB"] = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    result["limits"] = ["One physical SM; all other SM/rank geometry is host layout evidence only.",
                        "Producer activations are retained fixtures, not connected SwiGLU/gather/router arithmetic.",
                        "No route-weight arithmetic, MTP union dispatch, full checkpoint, token cycles or physical closure.",
                        "Model refresh remains parent-owned; source pins are retained worker prerequisites."]
    with a.record.open("x") as f:
        json.dump(result, f, indent=2); f.write("\n")
    print(result["status"].upper(), a.record, flush=True)
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
