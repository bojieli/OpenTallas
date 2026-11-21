"""bind_tool_stamp.py -- BIND-GEN-TOOLSKEW (FLOW-FIX-0400, COORD item 5).

A private bind run with one tree's tools, then generated with a newer rt, fails at gen hours later with "physical collector_tree differs from captured bound
reset identity" (S81 leaf t44, KV hgi_v6).  bind.py stamps the tool sha it ran with and the content hashes of the reset / relay generators into
<bind_out>/bind_tool.json; kit prep runs `check` against the gen rt before any heavy work and refuses a mismatch in those generators at once.

  python3 -I bind_tool_stamp.py stamp --bind-out DIR [--tools ROOT]
  python3 -I bind_tool_stamp.py check --bind-out DIR [--tools ROOT]     exit 0 ok / no stamp (a bind written before the stamp), exit 3 BIND-GEN-TOOLSKEW
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

STAMP = "bind_tool.json"
CLASS_LINE = "BIND-GEN-TOOLSKEW"
# the generators that decide the bound reset identity and the relay chains gen_phys re-derives (tools/die_plan/)
GENERATORS = ("reset_tree.py", "bound_reset_contract.py", "cbc_rules.py", "reset_consumers.py", "reset_port_relays.py", "reset_anchor.py", "reset_provider.py",
              "reset_replicate.py", "reset_carriers.py", "reset_leg_plan.py", "kit_reset_contract.py", "kit_relay_depth.py", "relay_depth.py", "relay_branch.py",
              "relay_bay.py", "reach_relay_plan.py", "native_relay_plan.py", "native_relay_apply.py", "local_reset_writeback.py", "bind_leaf_reset.py")


def tools_root(arg=None):
    return Path(arg).resolve() if arg else Path(__file__).resolve().parents[2]


def tools_sha(root):
    """the rt snapshot sha (root = .../rt/<sha>), else OT_TOOLS_SHA, else git HEAD of root, else ''"""
    root = Path(root)
    if root.parent.name == "rt" and len(root.name) >= 12:
        return root.name
    if os.environ.get("OT_TOOLS_SHA"):
        return os.environ["OT_TOOLS_SHA"]
    try:
        return subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True, timeout=20).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def generator_hashes(root):
    out = {}
    for n in GENERATORS:
        f = Path(root) / "tools" / "die_plan" / n
        if f.is_file():
            out[n] = hashlib.sha256(f.read_bytes()).hexdigest()
    return out


def stamp(bind_out, root=None):
    root = tools_root(root)
    rec = {"tools_sha": tools_sha(root), "generators": generator_hashes(root)}
    Path(bind_out).mkdir(parents=True, exist_ok=True)
    (Path(bind_out) / STAMP).write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n")
    return rec


def check(bind_out, root=None):
    """-> '' (ok, or no stamp / unreadable stamp: a bind written before the stamp is not refused) or the BIND-GEN-TOOLSKEW refusal text"""
    f = Path(bind_out) / STAMP
    try:
        rec = json.loads(f.read_text())
    except (OSError, ValueError):
        return ""
    root = tools_root(root)
    bsha, gsha = str(rec.get("tools_sha") or ""), tools_sha(root)
    if bsha and gsha and bsha == gsha:
        return ""
    old, now = rec.get("generators") or {}, generator_hashes(root)
    diff = sorted(n for n in set(old) | set(now) if old.get(n) != now.get(n))
    if not diff:
        return ""
    return (f"{CLASS_LINE}: bind of record {bind_out} ran with tools {bsha[:12] or '?'}, this gen runs rt {gsha[:12] or '?'}; reset / relay generators differ: {', '.join(diff[:8])}"
            f"{' ...' if len(diff) > 8 else ''}.  Fix: rebind on the gen rt ({gsha[:12] or 'this rt'}); gen would fail hours later with 'differs from captured bound reset identity'")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("stamp", "check"))
    ap.add_argument("--bind-out", required=True)
    ap.add_argument("--tools")
    a = ap.parse_args(argv)
    if a.cmd == "stamp":
        rec = stamp(a.bind_out, a.tools)
        print(f"bind tool stamp: {rec['tools_sha'][:12] or '?'} ({len(rec['generators'])} generators)")
        return 0
    why = check(a.bind_out, a.tools)
    if why:
        print(why)
        return 3
    print("BIND-GEN-TOOLSKEW ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
