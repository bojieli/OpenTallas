"""physical/common_flow files for kit generators in a sparse checkout (DIE-KV-62/q2e6 11-02, default-on).

Class: lane worktrees are often sparse (`sparse-checkout set tools physical/die_plan ...`).  The kit generators copy
Tcl from physical/common_flow (ot_keep_regs.tcl, ot_pin_regs.tcl, hold_pad_hb4.tcl, macro_cts_cluster.tcl,
clock_family.tcl), so a checkout without that directory died mid-gen with FileNotFoundError (DIE-KV-61 q2/astk/e6
kit gens; codex-qc-glue hold_pad_hb4.tcl).  The bytes are in the checkout's own git object store: when the working
tree does not carry the file, read it from HEAD (the pinned source commit) instead.  Same content as a full checkout,
no gate changed; a file git does not hold either comes back as the on-disk path, so callers report it as before.
"""
import os
import subprocess
from pathlib import Path

REL = "physical/common_flow"


def _git(repo, *args, text=True):
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=text, timeout=120)
    if r.returncode:
        return None
    return r.stdout.strip() if text else r.stdout


def common_flow_file(name, repo):
    """physical/common_flow/<name> of checkout `repo`: on disk if present, else materialised from git HEAD under
    $OT_VIEW_CACHE (default ~/.cache/opentallas/views)/common_flow/<blob>/<name>."""
    if Path(name).name != name:
        raise ValueError(f"common_flow_file: basename expected, got {name!r}")
    repo = Path(repo)
    path = repo / REL / name
    if path.is_file():
        return path
    try:
        top = _git(repo, "rev-parse", "--show-toplevel")
        if not top or Path(top).resolve() != repo.resolve():
            return path                      # not the toplevel of a checkout (e.g. a git-archive tools export)
        blob = _git(repo, "rev-parse", "--verify", "--quiet", f"HEAD:{REL}/{name}")
        if not blob:
            return path
        cache = Path(os.environ.get("OT_VIEW_CACHE") or Path.home() / ".cache/opentallas/views") / "common_flow" / blob
        out = cache / name
        if not out.is_file():
            data = _git(repo, "cat-file", "blob", blob, text=False)
            if data is None:
                return path
            cache.mkdir(parents=True, exist_ok=True)
            tmp = cache / f".{name}.{os.getpid()}.tmp"
            tmp.write_bytes(data)
            os.replace(tmp, out)
        return out
    except (OSError, subprocess.SubprocessError):
        return path
