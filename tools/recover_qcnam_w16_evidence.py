#!/usr/bin/env python3
"""Archive recovery evidence without executing evaluations or changing model rates.

Outputs use exclusive creation. Live checkpoints and partial outputs are never read.
Git blobs are read directly so this works in a small sparse checkout.
"""
import ast
import hashlib
import json
from pathlib import Path
import subprocess
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
PIN = "d2631dd9051c30d7ab1aeab6fdaab4f9200d3f5a"
W19 = "71b3ffc5"
W11 = "fea725b1d"


def blob(ref, path):
    return subprocess.check_output(["git", "show", f"{ref}:{path}"], cwd=ROOT)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def literal(data, name):
    for n in ast.parse(data).body:
        if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in n.targets):
            return ast.literal_eval(n.value)
    raise ValueError(name)


def main():
    out = ROOT / "results/quality/qcnam_w16_recovery_20261001"
    out.mkdir(exist_ok=False)
    evidence = {}

    def archive(name, data, source):
        with (out / name).open("xb") as f:
            f.write(data)
        evidence[name] = dict(source=source, sha256=sha(data), bytes=len(data))
        return json.loads(data)

    smoke = {}
    for name in ("smoke", "smoke2"):
        d = Path("/tmp/claude-1000/qcnam") / name
        r = archive(f"{name}_run.json", (d / "run.json").read_bytes(), str(d / "run.json"))
        smoke[name] = dict(layers=len(r["layers"]), max_layers=r["args"]["max_layers"],
                           eligible_for_gate=False)
    s = Path("/tmp/claude-1000/qcnam/smoke2/final.json")
    final = archive("smoke2_final.json", s.read_bytes(), str(s))
    smoke["smoke2"]["original_verdict"] = dict(quality_acceptable=final["verdict"]["quality"]["acceptable"],
        stability_pass=final["verdict"]["stability"]["pass"], adopt=final["verdict"]["adopt"])

    # Completed core is retained in place: its success is not a finalized gate.
    core = Path("/tmp/claude-1000/qcnam/runs/core")
    status = (core / "status").read_text()
    assert status.splitlines()[-1].startswith("end rc=0 ")
    assert any(l.startswith("done ") for l in (core / "log.txt").read_text().splitlines())
    core_files = {n: sha((core / n).read_bytes()) for n in ("run.json", "raw.json", "status", "log.txt")}
    cr = json.loads((core / "run.json").read_text())
    assert [l["layer"] for l in cr["layers"]] == list(range(40))

    hbm = {}
    for kind in ("ar", "ar_fused", "mtp", "mtp_fused"):
        path = f"results/uarch/w19_hbm_token_{kind}_wsel256.json"
        r = archive(f"w19_{kind}.json", blob(W19, path), f"git:{W19}:{path}")
        assert abs(sum(r["result"]["parts_us"].values()) - r["result"]["total_us"]) < 0.03
        hbm[kind] = r["result"]
    hand = archive("w11_unfused_wired_handoff.json", blob(W11,
        "results/rtl/w11_controller_recovery_20261001/unfused_wired_handoff.json"), f"git:{W11}:unfused_wired_handoff")
    trace = archive("w11_u2517_issues.json", blob(W11,
        "results/rtl/w11_controller_recovery_20261001/u2517.issues.json"), f"git:{W11}:u2517.issues.json")
    rtl = archive("w11_u2517.json", blob(W11,
        "results/rtl/w11_controller_recovery_20261001/u2517.json"), f"git:{W11}:u2517.json")
    assert sha((out / "w11_u2517.json").read_bytes()) == hand["evidence_sha256"]["u2517.json"]
    assert sha((out / "w11_u2517_issues.json").read_bytes()) == hand["evidence_sha256"]["u2517.issues.json"]
    assert trace["runs"][0]["cycles"] == rtl["single_step"]["cycles"]

    # TP96 capacity uses global owner state, not the legacy busiest TP4 die.
    config_path = "configs/models/candidates/deepseek-v4.1-flash.json"
    cfg_data = blob("HEAD", config_path)
    cfg = json.loads(cfg_data)
    def find_config(x):
        if isinstance(x, dict):
            if "operator_config" in x:
                return x["operator_config"]
            for v in x.values():
                found = find_config(v)
                if found is not None:
                    return found
        return None
    c = find_config(cfg)
    rows = sum(1048576 // c["compress_ratios"][l] for l in c["kv_source_layer_ids"]
               if c["compress_ratios"][l])
    compressed, index = rows * 288, rows * 68
    window = cfg["num_layers"] * c["window_tokens"] * 528
    state = compressed + index + window
    physical = 96 * 4 * 22500000000
    usable = int(physical * 0.9)
    weights = int(cfg["checkpoint_bytes"])
    model_data = blob("HEAD", "tools/uarch_model.py")
    dep_data = blob(PIN, "tools/deepseek_v41_deployment_quality.py")
    rule_data = blob(PIN, "tools/deepseek_v41_nam_quality.py")
    same = ["tools/uarch_model.py", "results/arch/v41_stage_owner_product.json",
            "results/uarch/economics.json", "results/uarch/economics_levers.json",
            "results/uarch/v41_dedicated_units.json", "results/uarch/v41_vm_waterfall.json"]
    rec = dict(schema="opentallas.qcnam-w16-recovery.v1", observed_utc=datetime.now(timezone.utc).isoformat(),
        base_main="89eace61f6c5a33b9814e2ab5775dcbf9b5f3ca2", evidence=evidence,
        source_sha256={"tools/recover_qcnam_w16_evidence.py": sha(Path(__file__).read_bytes()),
                       "tools/uarch_model.py": sha(model_data), config_path: sha(cfg_data)},
        qc=dict(run_pin=PIN, finalized=False, gate_complete=False, hardware_adopted=False,
            readiness="Required MMLU1000 and greedy lanes live; long not complete; do not finalize or restart.",
            core=dict(completed=True, layers=40, files_sha256=core_files, verdict_available=False),
            smoke=smoke, disclosure="Stability thresholds were tightened AFTER two three-layer smoke runs, BEFORE any full-model result. This is not registration before all observations. smoke2_final is a reduced smoke artifact, not a completed QC verdict. Its original stability failure and adopt=false are preserved.",
            stability_rule=literal(rule_data, "STABILITY_RULE"), threshold=literal(dep_data, "THRESHOLD")),
        w16=dict(missing_history_but_identical_content={p: blob("HEAD", p) == blob("af06e43ac", p) for p in same},
            action="No W16 cherry-pick or duplicate regeneration required; main already has identical patches and source pins.",
            hbm_time_us={k: dict(total_us=v["total_us"], parts_us=v["parts_us"], flags=v["flags"]) for k,v in hbm.items()},
            hbm_capacity=dict(tp=96, stacks_per_die=4, physical_bytes=physical, reserve_bytes=physical-usable,
                usable_bytes=usable, weights_bytes=weights, state_budget_bytes=usable-weights,
                per_user_bytes=dict(compressed_kv=compressed,index=index,window=window,total=state),
                users=(usable-weights)//state, context=1048576,
                caveat="Pooled TP96 capacity assumes balanced sharding; legacy arch_budget_v41 capacity[1048576].hbm_users=811 is a busiest TP4 die basis and must not be applied to this TP96 group.")),
        calibration=dict(vehicle="Reduced unfused wired u2517; not full-shape product", overall_status=rtl["status"],
            exact_single_step=rtl["single_step"]["pass"], measured_cycles=rtl["single_step"]["cycles"],
            timing_model=rtl["single_step"]["timing_model"], comparison=hand["comparison"],
            su_busy_cycles=rtl["single_step"]["unit_busy_cycles"]["su"],
            su_issue_attributed_intervals_total=hand["su_issue_attributed_intervals_total"],
            calibration_factor=rtl["single_step"]["cycles"]/rtl["single_step"]["timing_model"]["cycles"],
            adopted=False, limitation="Trace calibrates this reduced vehicle only. Overall lint failure retained; issue attribution includes waits and is not SU busy time. No full-shape multiplier or headline change; SS/FF and exact adoption gates remain pending."))
    with (out / "recovery.json").open("x") as f:
        json.dump(rec, f, indent=2)
        f.write("\n")
    print(json.dumps(dict(output=str(out), capacity_users=rec["w16"]["hbm_capacity"]["users"], finalized=False)))


if __name__ == "__main__":
    main()
