#!/usr/bin/env python3
"""Requeue class A/B blocks through the closure loop with the setup-triage flow fixes (+ flow-hold mm hold repair).

For each job name: copy its frozen spec, source = this branch's commit, prefix calibrate/route with
`export OT_CTS_FIX_HOOKS=...; export OT_MM_FF_SDC=<verdict.post_sdc>;` (an `export`, so the WHOLE command chain sees
it), route_hold_corners mm / HM 50 ps (flow-hold rule), merge_target null, name <job>-<tag>.
"""
import json, sys, os, re, copy, subprocess
JOBS = os.path.expanduser("~/.local/state/closure_loop/jobs")
DROP = "/tmp/claude-review-20261003/closure_jobs"
HOOKS = "physical/common_flow/cg_pushdown.tcl physical/common_flow/clk_net_protect.tcl"

def main():
    commit, tag = sys.argv[1], sys.argv[2]
    extra_env = {}
    names = []
    for a in sys.argv[3:]:
        if "=" in a and not a.startswith("-"):
            k, v = a.split("=", 1); extra_env[k] = v
        else:
            names.append(a)
    for n in names:
        st = json.load(open(f"{JOBS}/{n}.json"))
        sp = copy.deepcopy(st["spec"])
        new = f"{n}-{tag}"
        sp["name"] = new
        src = sp.get("source", {})
        sp["source"] = {k: v for k, v in src.items() if k not in ("branch", "commit")}
        sp["source"].update(branch="claude/setup-triage-20261007", commit=commit)
        post = " ".join(sp.get("verdict", {}).get("post_sdc", []))
        env = f"export OT_CTS_FIX_HOOKS='{HOOKS}'; " + (f"export OT_MM_FF_SDC='{post}'; " if post else "")
        env += "".join(f"export {k}='{v}'; " for k, v in extra_env.items())
        for stg in ("calibrate", "route"):
            s = sp.get("stages", {}).get(stg)
            if isinstance(s, dict) and s.get("cmd"):
                c = re.sub(r"^OT_MM_FF_SDC='[^']*' ", "", s["cmd"])
                s["cmd"] = env + c
        sp["route_hold_corners"] = "mm"
        sp["route_hold_margin_ns"] = 0.05
        sp["merge_target"] = None
        sp["owner"] = f"Claude:setup-triage (block owner {src.get('branch','?')} / {st['spec'].get('owner','?')})"
        sp["purpose"] = (f"SETUP-TRIAGE requeue of {n} (SS {st.get('metrics',{}).get('ss_ps')} / FF {st.get('metrics',{}).get('ff_ps')}): "
                         "class A/B flow fixes only (clock-gate push-down with latch cloning, CTS-net dont_touch before repair, "
                         "fixed SDC patterns) + flow-hold mm hold repair; source = origin/main + setup-triage fixes, no RTL change "
                         "by this stream. " + " ".join(f"{k}={v}" for k, v in extra_env.items()))
        out = f"{DROP}/{new}.json"
        json.dump(sp, open(out, "w"), indent=1)
        r = subprocess.run(["python3", "/home/ubuntu/wt-codex-closure-daemon-20261007i/tools/closure_loop/closure_loop.py", "validate", out],
                           capture_output=True, text=True)
        print(new, "validate rc", r.returncode, (r.stdout + r.stderr).strip()[-300:])
        if r.returncode != 0:
            os.rename(out, out + ".invalid")

if __name__ == "__main__":
    main()
