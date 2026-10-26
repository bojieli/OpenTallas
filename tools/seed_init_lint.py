#!/usr/bin/env python3
"""Flag testbench RNG seeds that Verilator does not honour.

Verilator 5.050 drops a declaration initialiser (``integer seed = SEED;``,
``reg [31:0] seed = 7;``, ``int seed = ...``) when the variable's only reads are
as the inout seed argument of ``$random(seed)`` / ``$dist_*(seed, ...)``: every
SEED then runs one identical stream (Icarus honours the initialiser).  Measured
2026-10-10 on ot-epyc1tb (hardcore-1010 seed sweep): SEED=1 and SEED=9 gave the
same $random values for decl-initialised seeds; a runtime ``seed = SEED;`` in an
initial block gave distinct streams.

Findings per seed variable of a module:
  DECL_INIT   initialised only at its declaration (no runtime assignment)
  NEVER_SET   never initialised nor assigned (constant X/0 seed)
The fix: assign the seed at runtime in an initial block (``seed = SEED;`` or via
``$value$plusargs``) and ``$display("SEED=%0d", seed)`` at start.

Usage: seed_init_lint.py [--all] [paths...]
  default: every tracked *.sv/*.v/*.svh/*.vh outside results/ (archived evidence copies);
  --all includes results/.
Exit status 1 when anything is flagged.
"""
import re
import subprocess
import sys
from pathlib import Path

SEED_USE = re.compile(r"\$(?:random|dist_[a-z_]+)\s*\(\s*([A-Za-z_]\w*)\s*[,)]")
TYPE_KW = r"(?:integer|int|reg|logic|bit|longint|shortint|var)"
MODULE = re.compile(r"\b(module|program|interface)\b(.*?)\bend(?:module|program|interface)\b", re.S)
AUTO_SCOPE = re.compile(r"\b(task|function)\s+automatic\b(.*?)\bend(?:task|function)\b", re.S)


def strip_comments(text):
    text = re.sub(r"/\*.*?\*/", lambda m: re.sub(r"[^\n]", " ", m.group(0)), text, flags=re.S)
    return re.sub(r"//[^\n]*", "", text)


def scan_module(body):
    names = sorted(set(SEED_USE.findall(body)))
    if not names:
        return []
    # Declarations inside automatic tasks/functions are initialised at call time: harmless.
    auto = [(m.start(), m.end()) for m in AUTO_SCOPE.finditer(body)]
    out = []
    for v in names:
        ve = re.escape(v)
        dims = r"\s*(?:\[[^\]]*\]\s*)*"
        # declarations naming v (possibly in a multi-declarator list), with or without an initialiser
        decl = re.compile(r"\b" + TYPE_KW + r"\b[^;]*?(?<![\w.$])" + ve + dims + r"(=(?!=)|[,;])")
        spans, decl_init, declared = [], False, False
        for m in decl.finditer(body):
            pre = body[m.start():m.start(m.lastindex)]
            if re.search(r"\b(begin|end|initial|always\w*|if|for|assign|\$\w+)\b|[()]", pre[:pre.rfind(v)]):
                continue  # not a declaration statement
            declared = True
            spans.append((m.start(), m.end()))
            if m.group(m.lastindex).startswith("=") and not any(a <= m.start() < b for a, b in auto):
                decl_init = True
        runtime = False
        asg = re.compile(r"(?<![\w.$])" + ve + dims + r"(?:<=|=)(?!=)")
        for m in asg.finditer(body):
            if not any(a <= m.start() < b for a, b in spans):
                runtime = True
                break
        if not runtime and re.search(r"\$value\$plusargs\s*\([^;]*,\s*" + ve + r"\s*\)", body):
            runtime = True
        if not runtime and re.search(r"\brandomize\s*\([^;]*\b" + ve + r"\b", body):
            runtime = True
        if runtime or not declared:
            continue  # assigned at runtime, or a port / declared elsewhere: not judged
        out.append((v, "DECL_INIT" if decl_init else "NEVER_SET"))
    return out


def scan_file(path):
    try:
        text = strip_comments(Path(path).read_text(errors="replace"))
    except OSError:
        return []
    res = []
    for m in MODULE.finditer(text):
        hdr = re.match(r"\s*(?:automatic\s+)?(\w+)", m.group(2))
        mod = hdr.group(1) if hdr else "?"
        for v, kind in scan_module(m.group(2)):
            res.append((path, mod, v, kind))
    return res


def main(argv):
    args = argv[1:]
    include_results = "--all" in args
    paths = [a for a in args if a != "--all"]
    if not paths:
        root = Path(__file__).resolve().parent.parent
        paths = subprocess.run(["git", "-C", str(root), "ls-files", "*.sv", "*.v", "*.svh", "*.vh"],
                               capture_output=True, text=True, check=True).stdout.split()
        paths = [str(root / p) for p in paths if include_results or not p.startswith("results/")]
    hits = []
    for p in paths:
        hits += scan_file(p)
    for path, mod, v, kind in hits:
        print(f"{kind}\t{path}\t{mod}\t{v}")
    print(f"seed_init_lint: {len(hits)} finding(s) in {len({h[0] for h in hits})} file(s)", file=sys.stderr)
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
