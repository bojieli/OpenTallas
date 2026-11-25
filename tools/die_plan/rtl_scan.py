#!/usr/bin/env python3
"""BIND-SPEED-1124 #2: one shared per-file RTL scan memo for the readers that re-scan the whole RTL tree.

A bind (and its PRE / elab) walked the same ~9k RTL files (0.85 GB on KV) many times: bind_elab.module_index alone runs from
the elab, PRE, the binder (4 call sites), split_source_guard, bind_wire_leaf and bind_plancells; view_define_check.rtl_index
and bind_strict_src parse the same text again.  scan(kind, path, fn) returns fn(text) of one file, where text is exactly
Path(path).read_text(errors="replace"):
  * in process: memoized on the file's stat (dev, inode, size, mtime_ns, ctime_ns), so a rewritten file is re-read;
  * on disk (OT_RTL_SCAN_CACHE=DIR, default DEFAULT_DIR when its parent exists; "0" = off): content addressed by
    sha256(text) + kind + the source of fn's module + extra, so any tree, fork or host-local copy with the same text shares it.
The value is pickled once and unpickled on every call: callers always get fresh objects (no cross-call mutation).
fn must be a pure function of (text, extra).  OSError propagates exactly like read_text (the callers skip unreadable files).
"""
import hashlib
import os
import pickle
import sys
import zlib
from pathlib import Path

VERSION = 1
DEFAULT_DIR = "/srv/opentallas-scratch2/claude/.cache/rtl-scan"
_MEM = {}           # (kind, path, extra) -> (stat key, pickled value)
_CODE = {}          # module name -> sha of its source file
STATS = dict(mem_hits=0, disk_hits=0, misses=0, disk_errors=0)


def _statkey(p):
    st = os.stat(p)
    return (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns)


def _code_sha(fn):
    mod = getattr(fn, "__module__", None) or "?"
    if mod not in _CODE:
        f = getattr(sys.modules.get(mod), "__file__", None)
        try:
            _CODE[mod] = hashlib.sha256(Path(f).read_bytes()).hexdigest() if f else "nofile"
        except OSError:
            _CODE[mod] = "unreadable"
    return _CODE[mod]


def cache_dir():
    d = os.environ.get("OT_RTL_SCAN_CACHE")
    if d is None:
        d = DEFAULT_DIR if os.path.isdir(os.path.dirname(os.path.dirname(DEFAULT_DIR))) else ""
    return None if d in ("", "0", "off") else d


def scan(kind, path, fn, extra=()):
    p = str(path)
    key = (kind, p, extra)
    sk = _statkey(p)                       # OSError (missing file) like read_text
    hit = _MEM.get(key)
    if hit is not None and hit[0] == sk:
        STATS["mem_hits"] += 1
        return pickle.loads(hit[1])
    text = Path(p).read_text(errors="replace")
    d = cache_dir()
    blob = None
    if d:
        h = hashlib.sha256(repr((VERSION, kind, _code_sha(fn), extra)).encode() + b"\0" + text.encode()).hexdigest()
        f = Path(d) / h[:2] / (h + ".pkz")
        try:
            blob = zlib.decompress(f.read_bytes())
            pickle.loads(blob)             # a torn / foreign file is a miss
            STATS["disk_hits"] += 1
        except Exception:                  # noqa: BLE001 - any unreadable cache entry is recomputed
            blob = None
    if blob is None:
        STATS["misses"] += 1
        blob = pickle.dumps(fn(text), protocol=4)
        if d:
            try:
                f.parent.mkdir(parents=True, exist_ok=True)
                tmp = f.parent / f".{h}.{os.getpid()}.tmp"
                tmp.write_bytes(zlib.compress(blob, 1))
                os.replace(tmp, f)
            except OSError:
                STATS["disk_errors"] += 1
    _MEM[key] = (sk, blob)
    return pickle.loads(blob)
