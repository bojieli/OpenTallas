#!/usr/bin/env python3
"""ot_delete_guard: THE shared pre-delete check of every fleet cleaner (ot-autoclean delete(), wt-reaper, ot_disk_autoprune, ot_cleanup_*).
CLEAN-ALL-1115 postmortem (11-16): an urgent deleter descended into a tree it had kept as a whole and deleted every child that had no
reference of its own, hollowing live die source trees (and removed whole the src tree kit_wave.json names).  This module makes both
impossible.  refuse(target) -> None (may delete) or the reason string.  A target is refused when
  1. it is a symlink or its realpath differs (no aliases: the epyc4 loss),
  2. it IS, CONTAINS or lies INSIDE a protected path: kit_wave.json dies[*].src / item_inputs[*].src / plan dirs, any tree_switch_*.json
     marker tree, a bind of record (kit_rtl bind_out/asbuilt/script + dirs), prov_view_sources dirs,
  3. a live process has its cwd, an open file or its command line under it (or its cwd is a parent of it),
  4. it is a STRICT DESCENDANT of a source tree root (<lane>/kw45/<tree>/x, <lane>/src_*/x): trees are deleted WHOLE or not at all.
The protected list is built on the hub (build_protected) and pushed to every host as protected.txt (header '# built <epoch>'); a missing
or older-than-MAX_AGE_H list fails CLOSED for any tree root.  usage: ot_delete_guard.py build COORD_DIR OUT | check PATH [LIST]"""
import glob, json, os, re, sys, time

DEFAULT_LIST = os.path.expanduser("~/.local/state/ot-delete-guard/protected.txt")
MAX_AGE_H = float(os.environ.get("OT_GUARD_MAX_AGE_H", "6"))
TREE_ROOT = re.compile(r"^(?P<root>/srv/opentallas-scratch[0-9]*/claude/(?:kw45/[^/]+|[^/]+/src_[^/]+))(?:/(?P<rest>.+))?$")
SRV = re.compile(r"/srv/opentallas-scratch[0-9]*/claude/[A-Za-z0-9._+/@=-]+")


def canon(p):
    return re.sub(r"opentallas-scratch[0-9]+", "opentallas-scratch2", p).replace("opentallas-scratch/", "opentallas-scratch2/").rstrip("/")


def _add(s, p):
    if isinstance(p, str) and p.startswith("/srv/"):
        s.add(canon(p))
        s.add(canon(os.path.dirname(p)) if os.path.basename(p) in ("bind_report.json", "asbuilt.json", "asbuilt_sources.json") else canon(p))


def build_protected(coord, marker_dir=None):
    """coord may be one dir or a list (hub clone + hub-coord copy): the union is protected"""
    if isinstance(coord, (list, tuple)):
        s = set()
        for c in coord:
            try:
                s |= build_protected(c, marker_dir)
            except (OSError, ValueError, KeyError):
                pass
        return s
    s = set(); cfg = json.load(open(os.path.join(coord, "autopilot/kit_wave.json")))["dies"]
    for d in cfg.values():
        for it in [d] + [i for i in (d.get("item_inputs") or {}).values() if isinstance(i, dict)]:
            _add(s, it.get("src")); _add(s, os.path.dirname(str(it.get("plan") or "")))
            kr = it.get("kit_rtl") or {}
            for k in ("bind_out", "asbuilt", "script"):
                _add(s, kr.get(k))
        for lst in (d.get("prov_view_sources") or {}).values():
            for c in lst if isinstance(lst, list) else [lst]:
                if isinstance(c, dict):
                    _add(s, c.get("dir")); _add(s, c.get("base"))
    for f in glob.glob(os.path.join(marker_dir or os.path.join(coord, "lanes/handoff"), "tree_switch_*.json")):
        try:
            _add(s, json.load(open(f)).get("tree"))
        except (OSError, ValueError):
            pass
    s.discard("")
    return s


def write_list(s, out):
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True); tmp = out + ".tmp"
    with open(tmp, "w") as fh:
        fh.write("# built %d\n" % time.time()); fh.write("\n".join(sorted(s)) + "\n")
    os.replace(tmp, out)


def load_list(path=None, now=None):
    path = path or os.environ.get("OT_GUARD_LIST") or DEFAULT_LIST
    try:
        lines = open(path).read().splitlines()
        built = float(lines[0].split()[2]) if lines and lines[0].startswith("# built") else os.path.getmtime(path)
    except (OSError, ValueError, IndexError):
        return None, "protected list missing/unreadable"
    if (now or time.time()) - built > MAX_AGE_H * 3600:
        return None, "protected list older than %gh" % MAX_AGE_H
    return {canon(l) for l in lines if l.startswith("/srv/")}, None


_CACHE = {"t": 0, "v": ""}


def live_text(skip=(), ttl=20):
    if time.time() - _CACHE["t"] < ttl and not skip:
        return _CACHE["v"]
    v = _live_text(skip); _CACHE.update(t=time.time(), v=v)
    return v


def _live_text(skip=()):
    t, me = [], {os.getpid(), os.getppid(), *skip}
    for p in glob.glob("/proc/[0-9]*"):
        if int(p[6:]) in me:
            continue
        try:
            t.append(open(p + "/cmdline", "rb").read().decode("latin1"))
            t.append(os.readlink(p + "/cwd"))
        except OSError:
            continue
        try:
            for f in os.listdir(p + "/fd"):
                try:
                    t.append(os.readlink(p + "/fd/" + f))
                except OSError:
                    pass
        except OSError:
            pass
    return "\n".join(t).replace("opentallas-scratch3", "opentallas-scratch2")


def refuse(target, protected=None, ptext=None, why_list=None):
    """None = allowed.  protected/ptext may be passed in (tests, batch callers); otherwise loaded."""
    t = canon(os.path.abspath(target))
    if os.path.islink(target) or os.path.realpath(target) != os.path.abspath(target):
        if canon(os.path.realpath(target)) != t:
            return "symlink or realpath differs"
    m = TREE_ROOT.match(t)
    if m and m.group("rest"):
        return "partial delete inside source tree %s (whole trees only)" % os.path.basename(m.group("root"))
    if protected is None:
        protected, err = load_list()
        if protected is None:
            return err if m else None            # fail closed for tree roots; other targets keep the other guards
    for p in protected:
        if p == t or p.startswith(t + "/") or t.startswith(p + "/"):
            return "protected (kit_wave.json src/bind of record/marker/prov): " + p
    pt = live_text() if ptext is None else ptext
    if t in pt or t + "/" in pt:
        return "live process cwd/open file/cmdline under it"
    return None


if __name__ == "__main__":
    if sys.argv[1] == "build":
        s = build_protected(sys.argv[2].split(",")); write_list(s, sys.argv[3]); print(len(s), "protected paths ->", sys.argv[3])
    else:
        r = refuse(sys.argv[2], *(([load_list(sys.argv[3])[0]] if len(sys.argv) > 3 else [])))
        print("REFUSE: " + r if r else "ok"); sys.exit(1 if r else 0)
