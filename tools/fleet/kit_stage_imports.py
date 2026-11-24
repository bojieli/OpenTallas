#!/usr/bin/env python3
"""KIT-STAGE-IMPORT-1124 (COORD, FLOW-CANARY-R2): ot-push-main refuses a push that makes a tools/die_plan module staged into kits import a
tools/die_plan sibling that kit staging does not copy.  da4562fcf7 added `import kit_define_parity` to kit_preflight.main(); staging did not
copy kit_define_parity.py, so every kit died at preflight until b1462d16b4.

Staging list, read statically from the revision (no tool is imported): signoff.py SIGNOFF_BUNDLE + OPTIONAL_SIGNOFF_BUNDLE + every literal
extra=(...) passed to copy_signoff_bundle( in tools/die_plan/*.py (gen_phys stages the kit), closed over signoff.KIT_TOOL_DEPENDENCIES.
Every staged .py is parsed; each import (any depth) whose top name is a tools/die_plan/<name>.py that is not staged is a pair
(staged module, sibling), unless it sits in a try whose handler catches ImportError / ModuleNotFoundError / Exception (explicit fallback).

Main already carries such pairs inside functions kits never call, so the push rule is a DELTA: refuse only the pairs HEAD has and the base
does not.  Fix by adding the sibling to the staged module's KIT_TOOL_DEPENDENCIES entry (or the copy_signoff_bundle extra list), or guard it.

  kit_stage_imports.py [--base REV] [--head REV] [REPO]   exit 1 + one line per new pair (all pairs without --base); 0 = clean."""
import argparse
import ast
import subprocess as S
import sys

DP = "tools/die_plan"
GUARDS = {"ImportError", "ModuleNotFoundError", "Exception", "BaseException"}


class Rev:
    """read tools/die_plan files of one git revision (works in a sparse clone)"""
    def __init__(self, repo, rev):
        self.repo, self.rev = repo, rev
        r = S.run(["git", "-C", repo, "ls-tree", "--name-only", f"{rev}:{DP}"], capture_output=True, text=True, timeout=300)
        self.names = set(r.stdout.split()) if r.returncode == 0 else set()

    def text(self, name):
        if name not in self.names:
            return None
        r = S.run(["git", "-C", self.repo, "show", f"{self.rev}:{DP}/{name}"], capture_output=True, timeout=300)
        return r.stdout.decode(errors="replace") if r.returncode == 0 else None

    def callers(self):
        r = S.run(["git", "-C", self.repo, "grep", "-l", "-F", "copy_signoff_bundle(", self.rev, "--", f"{DP}/*.py"],
                  capture_output=True, text=True, timeout=300)
        return sorted({l.split(":", 1)[1].rsplit("/", 1)[-1] for l in r.stdout.splitlines() if ":" in l})


def _assign(tree, name):
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in n.targets):
            try:
                return ast.literal_eval(n.value)
            except ValueError:
                return None
    return None


def staging(src):
    """-> {staged basename: why staged}"""
    txt = src.text("signoff.py")
    if txt is None:
        return {}
    so = ast.parse(txt)
    why = {}
    for var in ("SIGNOFF_BUNDLE", "OPTIONAL_SIGNOFF_BUNDLE"):
        for name in (_assign(so, var) or ()):
            why.setdefault(name, var)
    deps = _assign(so, "KIT_TOOL_DEPENDENCIES") or {}
    for fn in src.callers():
        if fn.startswith("test_"):
            continue
        try:
            t = ast.parse(src.text(fn) or "")
        except SyntaxError:
            continue
        for n in ast.walk(t):
            if isinstance(n, ast.Call) and getattr(n.func, "id", getattr(n.func, "attr", None)) == "copy_signoff_bundle":
                for k in n.keywords:
                    if k.arg == "extra":
                        try:
                            for name in ast.literal_eval(k.value):
                                why.setdefault(name, f"{fn} copy_signoff_bundle extra")
                        except ValueError:
                            pass
    todo = list(why)
    while todo:
        name = todo.pop()
        for d in deps.get(name, ()):
            if d not in why:
                why[d] = f"KIT_TOOL_DEPENDENCIES[{name}]"
                todo.append(d)
    return why


def _guarded(stack):
    for n in stack:
        for h in n.handlers:
            if h.type is None:
                return True
            es = h.type.elts if isinstance(h.type, ast.Tuple) else [h.type]
            if GUARDS & {getattr(e, "id", getattr(e, "attr", "")) for e in es}:
                return True
    return False


def imports(tree):
    """-> [(lineno, top module name, guarded)] of the absolute imports anywhere in the module"""
    out = []

    def walk(node, stack):
        for ch in ast.iter_child_nodes(node):
            st = stack + [node] if isinstance(node, ast.Try) and ch in node.body else stack
            if isinstance(ch, ast.Import):
                out.extend((ch.lineno, a.name.split(".")[0], _guarded(st)) for a in ch.names)
            elif isinstance(ch, ast.ImportFrom) and not ch.level and ch.module:
                out.append((ch.lineno, ch.module.split(".")[0], _guarded(st)))
            walk(ch, st)
    walk(tree, [])
    return out


def pairs(repo, rev):
    """-> {(staged module, unstaged sibling): line text} at REV"""
    src = Rev(repo, rev)
    why = staging(src)
    siblings = {n[:-3] for n in src.names if n.endswith(".py")}
    out = {}
    for name in sorted(why):
        if not name.endswith(".py"):
            continue
        txt = src.text(name)
        if txt is None:
            continue
        try:
            t = ast.parse(txt)
        except SyntaxError as e:
            out[(name, "<syntax>")] = f"KIT-STAGE-IMPORT {DP}/{name}: does not parse at {rev[:11]} ({e})"
            continue
        for ln, mod, guarded in imports(t):
            if guarded or mod == name[:-3] or mod not in siblings or f"{mod}.py" in why:
                continue
            out.setdefault((name, mod), f"KIT-STAGE-IMPORT {DP}/{name}:{ln} imports {mod}, which kit staging does not copy ({name} is "
                                        f"staged via {why[name]}); add {mod}.py to signoff.KIT_TOOL_DEPENDENCIES['{name}'] (or the "
                                        f"copy_signoff_bundle extra list), or guard the import with an ImportError fallback")
    return out


def new_pairs(repo, base, head="HEAD"):
    """the pairs HEAD adds over BASE (the push rule)"""
    b = pairs(repo, base)
    return [x for k, x in sorted(pairs(repo, head).items()) if k not in b]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("repo", nargs="?", default=".")
    ap.add_argument("--base")
    ap.add_argument("--head", default="HEAD")
    a = ap.parse_args(argv)
    f = new_pairs(a.repo, a.base, a.head) if a.base else list(pairs(a.repo, a.head).values())
    for x in f:
        print(x)
    return 1 if f else 0


if __name__ == "__main__":
    sys.exit(main())
