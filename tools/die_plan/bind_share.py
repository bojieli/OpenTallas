"""KIT-SLIM-1118 (COORD): every kit attempt re-runs bind and writes its own 2.36 GB bind_sinks.json (60 percent of the live kit disk); most are
byte-identical.  share_identical(path) is called right after the file is written: it keeps ONE inode per distinct content in a store next to the
scratch root (<scratch>/claude/.bind-share/<size>-<sha256>) and makes the attempt's copy a hardlink of it (atomic os.replace).  Readers only read the
file, so the shared inode is safe.  Store entries nobody links any more (st_nlink == 1) older than 1 h are unlinked on the next call.  Any failure
(other filesystem, no write access) leaves the plain copy.  Returns 'linked', 'stored' or 'kept'."""
import hashlib
import os
import re
import time

_ROOT = re.compile(r"^(/srv/opentallas-scratch[0-9]*/claude)(/|$)")
MIN_BYTES = 64 << 20


def sha256_file(path, chunk=8 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                return h.hexdigest()
            h.update(b)


def store_dir(path):
    m = _ROOT.match(os.path.realpath(path))
    return os.path.join(m.group(1), ".bind-share") if m else os.environ.get("OT_BIND_SHARE")


def share_identical(path, store=None, min_bytes=MIN_BYTES, now=None):
    try:
        st = os.stat(path)
        store = store or store_dir(path)
        if not store or st.st_size < min_bytes:
            return "kept"
        os.makedirs(store, exist_ok=True)
        now = time.time() if now is None else now
        for n in os.listdir(store):                       # orphaned store entries: only the store links them
            p = os.path.join(store, n)
            try:
                s = os.stat(p)
                if s.st_nlink == 1 and now - s.st_mtime > 3600 and not n.endswith(".tmp"):
                    os.unlink(p)
            except OSError:
                pass
        key = os.path.join(store, "%d-%s" % (st.st_size, sha256_file(path)))
        if not os.path.exists(key):
            os.link(path, key)
            return "stored"
        if os.stat(key).st_ino == st.st_ino:
            return "linked"
        tmp = path + ".share.tmp"
        os.link(key, tmp)
        os.replace(tmp, path)
        return "linked"
    except OSError:
        return "kept"
