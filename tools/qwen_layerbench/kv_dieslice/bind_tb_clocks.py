#!/usr/bin/env python3
"""Connect every bound regional clock to the bench's single core domain.

Regional names describe clock-delivery leaves, not separate clock domains.  The
functional bench drives them with ck_core; physical clock variation is die STA's
responsibility.  Derive names from the actual bound top, never a fixed list.
"""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path


def public_top(text: str) -> str:
    """The module text of qwen_kvsys_bound_top itself.  A START-provider join (start_provider_bind.py) puts the
    private top (qwen_kvsys_bound_top__without_start_provider, which still declares the pst_* inputs) in the same
    file; the bench instantiates only the public top, so only its ports are bench pins."""
    m = re.search(r'\bmodule\s+qwen_kvsys_bound_top\s*[#(]', text)
    if not m:
        return text
    end = text.find('endmodule', m.start())
    return text[m.start():] if end < 0 else text[m.start():end]


def bind_clocks(top: str, bench: str) -> tuple[str, list[str]]:
    top = public_top(top)
    names = sorted(set(re.findall(r'\binput\s+(?:wire\s+)?(clk_region_[A-Za-z0-9_$]+)\s*;', top)))
    declared = set(re.findall(r'\b(clk_region_[A-Za-z0-9_$]+)\b', top.split(');', 1)[0]))
    if declared != set(names):
        raise ValueError(f'unsupported regional clock declarations: {sorted(declared - set(names))}')
    # TOK-KV-7 10-29: a START provider joined into the public top (start_provider_bind.py) exposes one clock input per
    # emitted stage (t_st_<path>__clk, the die clock-tree tap that clocks it).  Like the regional leaves these are
    # delivery points of the one core clock: the functional bench drives them with ck_core (insertion delay / skew is
    # die STA's job).  Left unconnected they would sit at 0 under PINMISSING and the START wave would never leave the root.
    names += sorted(set(re.findall(r'\binput\s+(?:wire\s+)?(t_st_[A-Za-z0-9_$]+__clk)\s*;', top)))
    match = re.search(r'\bqwen_kvsys_bound_top\s+dut\s*\((.*?)\);', bench, re.S)
    if not match:
        raise ValueError('expected one qwen_kvsys_bound_top dut instance')
    body = match.group(1)
    # Bind5's virtual START stages are real required inputs. Under Verilator's
    # PINMISSING suppression an absent provider silently held all 29 low,
    # leaving the native boot stuck at 528 frames with zero credits. The die's
    # generated START provider must connect these pins or internalize them;
    # the functional bench cannot substitute POR or its mission START.
    start_inputs = sorted(set(re.findall(
        r'\binput\s+(?:wire\s+)?(?:\[[^]]+\]\s*)?(pst_[A-Za-z0-9_$]+)\s*;', top)))
    missing = []
    for name in start_inputs:
        actual = re.findall(r'\.' + re.escape(name) + r'\s*\(([^)]*)\)', body)
        if len(actual) != 1 or not actual[0].strip():
            missing.append(name)
    if missing:
        raise ValueError('missing native START provider inputs: ' + ', '.join(missing) +
                         '; install the plan-generated START stages before building the native bench')
    for name in names:
        actual = re.findall(r'\.' + re.escape(name) + r'\s*\(([^)]*)\)', body)
        if actual and actual != ['ck_core']:
            raise ValueError(f'{name}: expected ck_core, got {actual}')
        if not actual:
            body += f',\n        .{name}(ck_core)'
    patched = bench[:match.start(1)] + body + bench[match.end(1):]
    for name in names:
        if len(re.findall(r'\.' + re.escape(name) + r'\s*\(ck_core\)', body)) != 1:
            raise ValueError(f'{name}: missing or duplicate connection')
    return patched, names


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('top', type=Path)
    parser.add_argument('bench', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    result, names = bind_clocks(args.top.read_text(), args.bench.read_text())
    args.output.write_text(result)
    args.output.with_suffix('.clocks.json').write_text(json.dumps({'clock': 'ck_core', 'region_inputs': names}, indent=2) + '\n')
    print(f'bench clocks: core + {len(names)} regional / START-stage clock inputs')


if __name__ == '__main__':
    main()
