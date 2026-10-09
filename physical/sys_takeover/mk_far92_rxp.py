#!/usr/bin/env python3
"""sys-takeover 2026-10-09: qfd_emb_far92 RXP route specs (variants a / b) from the AFW specs.
    mk_far92_rxp.py COMMIT   (writes into /home/ubuntu/claude-takeover-20261007/sys-takeover and submits)"""
import json, shutil, subprocess, sys
C = sys.argv[1]
D = "/home/ubuntu/claude-takeover-20261007/sys-takeover"
J = "/home/ubuntu/.local/state/closure_loop/jobs"
L = "/home/ubuntu/wt-codex-closure-daemon-20261007l/tools/closure_loop/closure_loop.py"
for v, hm in (("a", None), ("b", None)):
    src = json.load(open(f"{J}/qfd_emb_far92_afw_{v}-ba2140dcb-tc.json"))["spec"]
    s = json.loads(json.dumps(src).replace("route_master.sh qfd_emb_far92_afw ", "route_master.sh qfd_emb_far92_rxp ")
                   .replace("signoff/qfd_emb_far92_afw.sdc", "signoff/qfd_emb_far92_rxp.sdc"))
    n = f"qfd_emb_far92_rxp_{v}-{C}-tc"
    s["name"] = n
    s["source"] = {"branch": "claude/sys-takeover-far92-20261009", "commit": C}
    s["owner"] = "Claude:sys-takeover"
    s["purpose"] = (f"qfd_emb_far92 RXP ({C}): qfd_emb_far92_afw EARLY_FAIL TT -557 (66,469 endpoints) = u_rx ir -> 128:1 x "
                    "523-b receive-buffer mux -> FIFO write (-620 at 770) and one merged e_d/k_d flop driving the top (emb) and "
                    "bottom (kv) pins of the 1.4-mm strip (-586) -> one-hot pointer copies per 32-bit slice, registered 2-stage "
                    "read + 4-entry staging (+2 wclk a word, full rate), separate e_d/k_d enables. "
                    + src["purpose"].split("Variant")[-1].join(["Variant", ""]) if "Variant" in src["purpose"] else f"Variant {v}.")
    s["stages"]["bench"] = [
        {"name": "far_rxp_exact", "cmd": "bash physical/sys_takeover/far_rxp_bench.sh pos {RUN}/bpos", "expect": "pass",
         "pass_regex": "FAR_RXP_PASS", "threads": 1, "peak_ram_gb": 4},
        {"name": "far_rxp_neg", "cmd": "bash physical/sys_takeover/far_rxp_bench.sh neg {RUN}/bneg", "expect": "fail",
         "fail_regex": "FAR_RXP_NEG_DETECTED", "threads": 1, "peak_ram_gb": 4}]
    s["cycles_added"] = "+2 wclk per received word (latency); full rate"
    s.pop("no_bench_reason", None)
    p = f"{D}/{n}.json"
    json.dump(s, open(p, "w"), indent=1)
    r = subprocess.run(["python3", L, "validate", p], capture_output=True, text=True)
    print(n, (r.stdout + r.stderr).strip().splitlines()[-1], "| cfg refs:", json.dumps(s["stages"]).count("qfd_emb_far92_rxp"))
    shutil.copy(p, "/tmp/claude-review-20261003/closure_jobs/")
