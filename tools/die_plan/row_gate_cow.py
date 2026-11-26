"""Mount a sealed die source as the read-only lower of a terminal row gate."""
import os
from pathlib import Path
import runpy
import shutil
import stat
import subprocess
import sys


INNER = "OT_ROW_GATE_COW_TREE"
LEDGER = "OT_ROW_GATE_COW_LEDGER"
SHARED_PRE_CACHE = Path("/srv/opentallas-scratch2/claude/.cache/pre-base")
SHARED_PRE_SLOTS = Path("/tmp/ot-pre-slots")


def run(argv, src, out, ledger=None):
    """Invoke the same gate in a private mount namespace with writable OUT."""
    bwrap = shutil.which("bwrap")
    if not bwrap:
        raise ValueError("bwrap with kernel overlay support is required")
    if out == src or out.is_relative_to(src) or src.is_relative_to(out):
        raise ValueError("source and output trees overlap")
    if ledger:
        ledger = Path(ledger).resolve()
        if ledger == src or ledger.is_relative_to(src):
            raise ValueError("ledger must not write into the sealed source")
    out.mkdir(parents=True, exist_ok=True)
    for p in ("tree", "launch", "ROW-READY.json", ".cow-upper", ".cow-work", ".pre-base"):
        if os.path.lexists(out / p):
            raise ValueError(f"copy-on-write requires a new attempt directory ({out / p} exists)")
    upper, work = out / ".cow-upper", out / ".cow-work"
    view, cache = out / "tree", out / ".pre-base"
    for d in (upper, work, view, cache):
        d.mkdir()
    # Keep host-wide PRE admission even though this process gets a private
    # /tmp. The rest of the host remains read-only inside the namespace.
    if SHARED_PRE_SLOTS.is_symlink():
        raise ValueError(f"shared PRE slot directory is a symlink: {SHARED_PRE_SLOTS}")
    SHARED_PRE_SLOTS.mkdir(mode=0o1777, parents=True, exist_ok=True)
    mounts = ["--bind", str(SHARED_PRE_SLOTS), str(SHARED_PRE_SLOTS),
              "--bind", str(out), str(out)]
    if SHARED_PRE_CACHE.is_dir():
        # Read existing base findings and launch trees without permitting a
        # scoped row script to mutate the common cache.
        mounts += ["--overlay-src", str(SHARED_PRE_CACHE), "--tmp-overlay", str(cache)]
    try:
        rc = subprocess.run([
            bwrap, "--unshare-user", "--die-with-parent", "--ro-bind", "/", "/",
            "--dev-bind", "/dev", "/dev", "--tmpfs", "/tmp", *mounts,
            "--overlay-src", str(src), "--overlay", str(upper), str(work), str(view),
            "--setenv", INNER, str(view), "--setenv", "OT_PRE_BASE_CACHE", str(cache),
            "--setenv", "OT_PRE_SLOT_DIR", str(SHARED_PRE_SLOTS),
            "--setenv", LEDGER, str(out / ".cow-ledger"),
            sys.executable, "-I", *argv,
        ]).returncode
    finally:
        # The mount lives only in bwrap. Remove its empty placeholder so the
        # ordinary gate cannot mistake it for an already materialized fork.
        view.rmdir()
    if ledger:
        for record in (out / ".cow-ledger").glob("*.json"):
            ledger.mkdir(parents=True, exist_ok=True)
            tmp = ledger / f".{record.name}.{os.getpid()}"
            shutil.copyfile(record, tmp)
            tmp.replace(ledger / record.name)
    return rc


def light_choice(src, rt, types, keep, env=None):
    """P-POSTPUBLISH-DISK (FLEET-OPS-R4 11-26): the light fork.  A gate that only needs to READ a sealed source runs in the kernel overlay
    (sparse upper = only the files the gate writes) instead of a full private copy (about 60 GB per run).  -> (use_cow, reason).
    Any doubt falls back to the ordinary ot-tree-fork copy; light never turns a gate into NOT-READY by itself."""
    env = os.environ if env is None else env
    if types == "all":
        return False, "whole-die gate needs --cow with R8 pins (explicit)"
    if keep:
        return False, "--keep-tree/--keep-fork needs a materialized fork"
    if not shutil.which("bwrap"):
        return False, "no bwrap"
    yosys = env.get("OT_BIND_YOSYS")
    if not yosys or not shutil.which(yosys, path=env.get("PATH")):
        return False, "no OT_BIND_YOSYS executable pin (Docker cannot see the overlay)"
    try:
        fleet = runpy.run_path(str(Path(rt) / "tools/fleet/ot-tree-fork"))
        ident = fleet["src_identity"](str(src))
    except Exception as e:  # noqa: BLE001
        return False, f"source identity unreadable: {e}"
    if not ident.get("src_manifest_hash") or not ident.get("src_sealed") or (Path(src) / ".fork.json").exists():
        return False, "source is not an immutable sealed manifest tree"
    return True, "bwrap-overlay"


def mounted(out):
    view = out / "tree"
    if os.environ.get(INNER) != str(view):
        return False
    if not view.is_mount():
        raise ValueError("copy-on-write tree is not an isolated mount")
    return True


def prepare(src, tree, rt, base, asbuilt, lane, table_paths):
    """Enforce stock source/link rules and prepare the known writable paths."""
    fleet = runpy.run_path(str(Path(rt) / "tools/fleet/ot-tree-fork"))
    identity = fleet["src_identity"](str(src))
    digest = identity.get("src_manifest_hash")
    if not digest or not identity["src_sealed"] or (src / ".fork.json").exists():
        raise ValueError("copy-on-write requires an immutable sealed source tree")
    why = fleet["same_manifest"](str(src), digest)
    if why:
        raise ValueError(f"sealed source verification failed: {why}")
    inventory = fleet["plan"](str(src), str(tree))
    if inventory["refused"] or inventory["specials"]:
        problems = inventory["refused"] + inventory["specials"]
        raise ValueError(f"copy-on-write refused source entries: {problems[:4]}")

    def owned(path):
        path = Path(path)
        if not path.resolve().is_relative_to(tree):
            raise ValueError(f"copy-on-write path leaves scoped tree: {path}")
        return path

    def allow_write(path):
        path = owned(path)
        path.chmod(path.stat().st_mode | stat.S_IWUSR)

    # Sealed inputs frequently have read-only directories. Only parents of
    # writes used by the gate need metadata copy-up. Absolute internal links
    # are rewritten to the same relative destinations as the normal fork.
    allow_write(tree)
    for rel, expected in inventory["links"]:
        link = tree / rel
        if os.readlink(link) != expected:
            allow_write(link.parent)
            link.unlink()
            link.symlink_to(expected)
    for path in (tree / base, tree / asbuilt):
        owned(path)
    allow_write((tree / base).parent)
    main, extra = table_paths(tree, asbuilt)
    for path in ([main] + extra if main is not None else ()):
        allow_write(owned(path).parent)

    meta = dict(src=str(src), src_real=str(src), lane=lane, method="bwrap-overlay", **identity)
    fleet["write_fork_json"](str(tree / ".fork.json"), meta)
    return {"method": "bwrap-overlay", "src_manifest_hash": digest,
            "logical_source_bytes": inventory["bytes"]}
