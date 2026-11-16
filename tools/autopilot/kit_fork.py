#!/usr/bin/env python3
"""kit_fork.py: copy a kit as a clean fork, and refuse a copied sign-off (COORD r178b, KIT-OPS-5).

  kit_fork.py fork SRC DST     copy the kit INPUTS only: no logs/, reports/, results/, run/, gate/signoff/verdict files,
                               odb/def outputs, FAIL_/DONE markers, resume state, .git.  Writes DST/KIT_FORK.json
                               {source, forked_at, inputs_digest} so the copy is recognisable as a fork.
  kit_fork.py digest KIT       print the kit-inputs digest (sha256 over the sorted relative paths + file sha256 of every
                               input file, same exclusion rule as fork)
  kit_fork.py check KIT        exit 0 when KIT has no signoff.json, or its signoff.json carries kit_inputs_digest equal to the
                               current digest; exit 1 when a signoff.json is present without / with a different digest in a
                               forked kit (a copied result must never read as a new sign-off); a kit that is not a fork and
                               has no digest field passes (legacy kits).
  kit_fork.py stamp KIT        write kit_inputs_digest into KIT/signoff.json (the sign-off step calls this when it writes the file).
"""
import hashlib, json, os, shutil, sys, time

SKIP_DIRS = {"logs", "reports", "results", "run", "gate", "signoff", "verdict", "objects", ".git", "__pycache__", "future_lec"}
SKIP_FILES = ("signoff.json", "gate.json", "verdict.json", "KIT_FORK.json", "resume.json", "result.json", "spec.json")
SKIP_PREFIX = ("FAIL_", "DONE", "PASS_", "GATE_")
SKIP_SUFFIX = (".odb", ".log", ".lock")


def is_input(rel):
    parts = rel.split(os.sep)
    if any(p in SKIP_DIRS for p in parts[:-1]):
        return False
    n = parts[-1]
    return not (n in SKIP_FILES or n.startswith(SKIP_PREFIX) or n.endswith(SKIP_SUFFIX))


def walk_inputs(kit):
    out = []
    for root, dirs, files in os.walk(kit):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for f in sorted(files):
            rel = os.path.relpath(os.path.join(root, f), kit)
            if is_input(rel) and os.path.isfile(os.path.join(kit, rel)):
                out.append(rel)
    return out


def file_sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def digest(kit):
    h = hashlib.sha256()
    for rel in walk_inputs(kit):
        h.update(rel.encode() + b"\0" + file_sha(os.path.join(kit, rel)).encode() + b"\n")
    return h.hexdigest()


def fork(src, dst):
    if os.path.exists(dst):
        raise SystemExit(f"kit_fork: {dst} exists")
    for rel in walk_inputs(src):
        t = os.path.join(dst, rel)
        os.makedirs(os.path.dirname(t), exist_ok=True)
        shutil.copy2(os.path.join(src, rel), t)
    json.dump({"source": os.path.realpath(src), "forked_at": time.time(), "inputs_digest": digest(dst)},
              open(os.path.join(dst, "KIT_FORK.json"), "w"), indent=1)
    return dst


def stamp(kit):
    p = os.path.join(kit, "signoff.json")
    s = json.load(open(p))
    s["kit_inputs_digest"] = digest(kit)
    tmp = p + ".new"
    json.dump(s, open(tmp, "w"), indent=1)
    os.replace(tmp, p)


def check(kit):
    """(ok, why)"""
    p = os.path.join(kit, "signoff.json")
    if not os.path.exists(p):
        return True, "no signoff.json"
    try:
        have = json.load(open(p)).get("kit_inputs_digest")
    except (OSError, ValueError):
        return False, "signoff.json unreadable"
    forked = os.path.exists(os.path.join(kit, "KIT_FORK.json"))
    if have is None:
        return (not forked), ("forked kit carries a signoff.json without kit_inputs_digest: copied result" if forked else "legacy kit")
    cur = digest(kit)
    return (have == cur), ("signoff matches the kit inputs" if have == cur else f"signoff digest {have[:12]} != kit inputs {cur[:12]}: result is not of these inputs")


def main(argv):
    if len(argv) >= 3 and argv[1] == "fork" and len(argv) == 4:
        print(fork(argv[2], argv[3])); return 0
    if len(argv) == 3 and argv[1] == "digest":
        print(digest(argv[2])); return 0
    if len(argv) == 3 and argv[1] == "stamp":
        stamp(argv[2]); return 0
    if len(argv) == 3 and argv[1] == "check":
        ok, why = check(argv[2]); print(("OK " if ok else "REFUSE ") + why); return 0 if ok else 1
    print(__doc__); return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
