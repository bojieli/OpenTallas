#!/usr/bin/env python3
"""otrun-hub-retarget.py SRC DST NEWHUB OLDHUB [--drop-old]   (INFRA2 2026-10-24; see lanes/OTRUN-HUB-RECOVERY.md)

Rewrites an ot-run or ot-sizes-sync copy for a new hub.  In those tools "localhost" = THE HUB ITSELF (reached by
`ssh localhost`), so moving the hub from OLDHUB (e.g. epyc1) to NEWHUB (e.g. epyc3) swaps the two names in the host
tables HOSTS, HOST_ROLE, NO_AVX512, HOST_MAX_DIE (code part only, comments untouched):
  NEWHUB -> "localhost"  (its role / Zen-3 NO_AVX512 flag move with it)     "localhost" -> OLDHUB  (old hub = plain worker)
HOST_RESERVE stays on "localhost" (the hub keeps its 8-thread/16-GB reserve for ot-run clients).
--drop-old removes OLDHUB from HOSTS (use when the old hub is dead).  Prints a diff of the changed lines."""
import difflib, re, sys

a = [x for x in sys.argv[1:] if not x.startswith("--")]
src, dst, new, old = a
drop = "--drop-old" in sys.argv
lines = open(src).read().split("\n")
out = []
for ln in lines:
    m = re.match(r"^(HOSTS|HOST_ROLE|NO_AVX512|HOST_MAX_DIE)\s*=", ln)
    if m:
        code, sep, com = ln.partition("   #") if "   #" in ln else (ln, "", "")
        code = code.replace(f'"{new}"', '"\0NEW"').replace('"localhost"', f'"{old}"').replace('"\0NEW"', '"localhost"')
        if drop and m.group(1) == "HOSTS":
            code = re.sub(rf'"{re.escape(old)}",\s*|,\s*"{re.escape(old)}"', "", code)
        ln = code + sep + com
    out.append(ln)
open(dst, "w").write("\n".join(out))
sys.stdout.writelines(difflib.unified_diff([l + "\n" for l in lines], [l + "\n" for l in out], src, dst, n=0))
compile("\n".join(out), dst, "exec")
