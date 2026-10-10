#!/usr/bin/env python3
"""eco-sweep (2026-10-09): launch the post-route VT-SWAP SETUP ECO (vtswap_eco.sh) on a NEEDS_RTL closure-loop job whose
only miss is a THIN TT setup miss (TT in [-45, 0), FF >= 0, DRC 0, no failed checks), as the job's ECO stage.

The stage is launched with the loop's own launch_stage (run.sh / pid / rc under {RUN}/cl, tag hold_eco.a<attempt>); the
job goes to status ECO, so the daemon's ECO completion takes over unchanged: result.json -> eco_passes (TT >= 0, FF >= 0,
DRC 0, no errors; an LVT share over the cap is an error) -> eco_install_cmd (6_final.* installed, originals *.pre_eco)
-> re-verdict at the routed reference -> CLOSED record.  A missed ECO -> NEEDS_RTL as for a hold ECO.

    vtswap_launch.py [--dry] [--target 10] [--cap 2.0] [--loop-dir DIR] NAME...
"""
import argparse
import shlex
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ap = argparse.ArgumentParser()
ap.add_argument("--dry", action="store_true")
ap.add_argument("--target", type=float, default=10.0)
ap.add_argument("--cap", type=float, default=2.0)
ap.add_argument("--loop-dir", default="/home/ubuntu/wt-codex-closure-daemon-20261007l/tools/closure_loop")
ap.add_argument("names", nargs="+")
a = ap.parse_args()
sys.path.insert(0, a.loop_dir)
import closure_loop as cl  # noqa: E402

for name in a.names:
    with cl.job_lock(name):
        j = cl.load_job(name)
        m = dict(j.get("metrics") or {})
        tt, ff, drc = m.get("ss_ps"), m.get("ff_ps"), m.get("drc")
        e = j.get("eco") or {}
        why = None
        if j["status"] != "NEEDS_RTL":
            why = f"status {j['status']}"
        elif tt is None or ff is None or not (-45.0 <= tt < cl.SS_MIN and ff >= cl.FF_MIN and drc == 0):
            why = f"not a thin setup miss (TT {tt} / FF {ff} / DRC {drc})"
        elif j.get("failed_checks"):
            why = f"failed checks {j['failed_checks']}"
        elif e.get("installed"):
            why = "an installed ECO replaced the route"
        if why:
            print(f"SKIP {name}: {why}")
            continue
        rb, ob = cl.eco_paths(j, m)
        if not rb:
            print(f"SKIP {name}: no route base")
            continue
        post = list(m.get("post_sdc") or (j["spec"].get("verdict") or {}).get("post_sdc", []))
        out = f"{j['run']}/cl/eco-vtswap" + (f"-r{len(j.get('eco_history') or []) + 1}" if j.get("eco_history") or e else "")
        env = (f"TARGET={a.target:g} CAP_PCT={a.cap:g} DRC0={int(drc)} ACC_SS={cl.SS_MIN:g} ACC_FF={cl.FF_MIN:g} SETUP_LIB=TT "
               f"SDC_NAME={shlex.quote(m.get('sdc_name') or '6_final.sdc')} THREADS=8 "
               f"MACROS={shlex.quote(' '.join((j['spec'].get('verdict') or {}).get('macros', [])))} "
               f"ORFS_W18={shlex.quote(m.get('orfs_dir') or '')}")
        if m.get("setup_post_sdc"):
            env += f" SETUP_POST_SDC={shlex.quote(' '.join(m['setup_post_sdc']))}"
        cmd = f"{env} bash {{CL}}/vtswap_eco.sh {rb} {ob} {out} {j['spec']['block']} " + " ".join(shlex.quote(p) for p in post)
        if a.dry:
            print(f"DRY {name} [{j['host']}]: {cmd}")
            continue
        cl.ship_helpers(j["host"], j["run"])
        r = subprocess.run(["scp", "-q", "-o", "BatchMode=yes", str(HERE / "vtswap_eco.sh"), str(HERE / "vtswap_eco.tcl"),
                            f"{j['host']}:{j['run']}/cl/"], capture_output=True, text=True, timeout=120)
        if r.returncode:
            print(f"FAIL {name}: scp {r.stderr[-200:]}")
            continue
        stl = cl.stage_list(j["spec"])
        vidx = next(i for i, x in enumerate(stl) if x["kind"] == "verdict")
        if e:
            j.setdefault("eco_history", []).append(e)
        rc = cl.ssh(j["host"], f"test -e {j['run']}/cl/hold_eco.a{j['attempt']}.rc && echo USED; true", timeout=60)
        if "USED" in rc.stdout:
            j["attempt"] += 1
        j.update(stage_idx=vidx, retries_used=0, errors=[], reason=None)
        j["eco"] = dict(tried=True, kind="vtswap", rb=rb, ob=ob, out=out, post_sdc=post,
                        sdc_name=m.get("sdc_name") or "6_final.sdc", setup_post_sdc=list(m.get("setup_post_sdc") or []),
                        pre=dict(ss_ps=tt, ff_ps=ff), started=cl.now_iso(), target_ps=a.target, lvt_cap_pct=a.cap)
        st = dict(key="hold_eco", kind="hold_eco", threads=8, ram=16)
        cl.launch_stage(j, st, cmd)
        j["status"], j["stage_key"] = "ECO", "hold_eco"
        cl.event(j, f"eco-sweep: thin TT setup miss (TT {tt:+.2f} / FF {ff:+.2f} / DRC 0): post-route VT-swap setup ECO "
                    f"(RVT->LVT on TT paths under {a.target:g} ps, cap {a.cap:g} % LVT, FF hold guard, no re-route) on {rb}/6_final.odb")
        cl.ledger(j, f"VT-SWAP ECO launched (eco-sweep): TT {tt:+.2f} / FF {ff:+.2f}, target {a.target:g}, LVT cap {a.cap:g} %")
        cl.save_job(j)
        print(f"LAUNCHED {name} [{j['host']}] tag hold_eco.a{j['attempt']} out {out}")
