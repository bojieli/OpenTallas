#!/usr/bin/env python3
"""TOK-KV-7 10-29: bench scope of the bound die under a joined START provider.

tools/die_plan/start_provider_bind.py turns qwen_kvsys_bound_top into a thin public top (the generated START provider
ot_die_start_stages + `qwen_kvsys_bound_top__without_start_provider u_bound`), so every bound partition / net the bench
reads by hierarchical reference (dut.sys_c..., dut.x_<net>, generated partrec / kvpc diag includes) now lives under
dut.u_bound.  Usage: join_scope.py TOP FILE... -- rewrites `dut.<name>` -> `dut.u_bound.<name>` in place when TOP is
such a join (idempotent); a plain bound top leaves the files untouched.
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

JOIN_RE = re.compile(r'^\s*qwen_kvsys_bound_top__without_start_provider\s+(\w+)\s*\(', re.M)


def joined_instance(top: str) -> str | None:
    m = re.search(r'\bmodule\s+qwen_kvsys_bound_top\s*[#(]', top)
    if not m:
        return None
    end = top.find('endmodule', m.start())
    hits = JOIN_RE.findall(top[m.start():end if end >= 0 else None])
    if len(hits) > 1:
        raise ValueError(f'public top instantiates the private top {len(hits)} times')
    return hits[0] if hits else None


def rescope(text: str, inst: str) -> str:
    return re.sub(r'\bdut\.(?!' + re.escape(inst) + r'\.)(?=[A-Za-z_\\])', 'dut.' + inst + '.', text)


def main() -> int:
    top, files = Path(sys.argv[1]), [Path(f) for f in sys.argv[2:]]
    inst = joined_instance(top.read_text(errors='replace'))
    if inst is None:
        print('JOIN_SCOPE none (plain bound top)')
        return 0
    n = 0
    for f in files:
        old = f.read_text()
        new = rescope(old, inst)
        n += len(re.findall(r'\bdut\.' + re.escape(inst) + r'\.', new)) - len(re.findall(r'\bdut\.' + re.escape(inst) + r'\.', old))
        if new != old:
            f.write_text(new)
    print(f'JOIN_SCOPE dut.{inst} refs rescoped {n} files {len(files)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
