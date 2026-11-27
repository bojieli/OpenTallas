"""rt_tool_commit: a launch must pin an rt snapshot at or after the row's tool commit (P-RUNTIME-MANIFEST, FLEET-OPS-R5 11-27).

QC-R3-STA died on SCHEMA-UNKNOWN-KEY lane_mono because its gate pinned an rt older than the commit that added the key.  check() asks the bare
mirror `git merge-base --is-ancestor <tool_commit> <rt_sha>`: equal or descendant passes; not an ancestor refuses (NOT-RUN SETUP line naming both
shas + the newest qualifying rt = rt/current when it descends); an unresolvable commit (not in the mirror, no mirror) fails open with a WARN.
The tool commit comes from --tool-commit, else spec key tool_commit, else kit_wave.json dies.<die>.tool_commit; none = no check.  Stdlib only."""
import os
import re
import subprocess
from pathlib import Path

MIRROR = os.environ.get("OT_GIT_MIRROR_BARE") or "/srv/opentallas-scratch2/git/OpenTallas.git"
RT_ROOT = os.environ.get("OT_RT_ROOT") or "/srv/opentallas-scratch2/claude/rt"
HEX = re.compile(r"[0-9a-fA-F]{7,40}")


def tool_commit_of(sp=None, cfg=None, die="", explicit=""):
    for v in (explicit, (sp or {}).get("tool_commit"), (((cfg or {}).get("dies") or {}).get(die) or {}).get("tool_commit")):
        v = str(v or "").strip()
        if v:
            return v
    return ""


def _git(mirror, *args):
    return subprocess.run(["git", "-C", str(mirror), *args], capture_output=True, text=True, timeout=60)


def _resolve(mirror, sha):
    if not HEX.fullmatch(str(sha)):
        return ""
    r = _git(mirror, "rev-parse", "--verify", "-q", f"{sha}^{{commit}}")
    return r.stdout.strip() if r.returncode == 0 else ""


def _descends(mirror, anc, desc):
    return _git(mirror, "merge-base", "--is-ancestor", anc, desc).returncode == 0


def check(tool_commit, rt_sha, mirror=None, rt_root=None, what="launch"):
    """-> (verdict OK|REFUSE|WARN|SKIP, text).  Only REFUSE refuses."""
    mirror, rt_root = mirror or MIRROR, rt_root or RT_ROOT
    tc, rt = str(tool_commit or "").strip(), str(rt_sha or "").strip()
    if not tc:
        return "SKIP", ""
    if not rt:
        return "WARN", f"RT-TOOL-COMMIT WARN: {what} has no rt pin; cannot check tool commit {tc[:12]}"
    try:
        tfull, rfull = _resolve(mirror, tc), _resolve(mirror, rt)
    except (OSError, subprocess.SubprocessError) as e:
        return "WARN", f"RT-TOOL-COMMIT WARN: {what}: mirror {mirror} unreadable ({type(e).__name__}); tool commit {tc[:12]} vs rt {rt[:12]} unchecked"
    if not tfull or not rfull:
        return "WARN", (f"RT-TOOL-COMMIT WARN: {what}: {'tool commit ' + tc[:12] if not tfull else 'rt ' + rt[:12]} not in {mirror}; "
                        f"tool commit {tc[:12]} vs rt {rt[:12]} unchecked (fail open)")
    if tfull == rfull or _descends(mirror, tfull, rfull):
        return "OK", ""
    better = ""
    try:
        cur = os.path.basename(os.readlink(Path(rt_root) / "current"))
        cfull = _resolve(mirror, cur[:12])
        if cfull and (cfull == tfull or _descends(mirror, tfull, cfull)):
            better = cur[:12]
    except OSError:
        pass
    fix = f"newest qualifying rt: --rt {better} (rt/current)" if better else "no qualifying rt/current yet (rt/current does not contain the tool commit; wait for ot-tools-follow)"
    return "REFUSE", (f"NOT-RUN SETUP: {what} pins rt {rfull[:12]} which does not contain tool commit {tfull[:12]} "
                      f"(git merge-base --is-ancestor {tfull[:12]} {rfull[:12]} fails: the rt predates the tools the row needs). {fix}")
