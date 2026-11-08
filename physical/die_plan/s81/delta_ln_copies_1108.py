#!/usr/bin/env python3
"""S81 plan event LN-BROADCAST (S81-LNB-1 11-08): partition_types[T].ln_copies = true for the named leaf types.

bind.py kit-rtl then gives each of the 16 hc_post lanes its own kept copy of the vp coefficient words and its own
reset relay bit (tools/die_plan/kit_ln_copies.py; proof results/s81_lnb_1108/proof.json; 0 cycles changed).
Line-exact: one line `"ln_copies": true,` after the type's `"hard": false,` line; the plan is otherwise unchanged
(asserted json-equal to the dict edit).
    python3 -I delta_ln_copies_1108.py PLAN_IN PLAN_OUT REPORT.json TYPE [TYPE ...]      (cwd = repo root)
"""
import json
import sys
from pathlib import Path

sys.path[:0] = ["tools/die_plan"]
import schema as S  # noqa: E402


def main():
    src, out, rep, *types = sys.argv[1:]
    assert types, "name the types"
    txt = Path(src).read_text()
    P = json.loads(txt)
    lines = txt.split("\n")
    done = []
    for tn in types:
        t = P["partition_types"][tn]
        assert not t["hard"] and "ln_copies" not in t, tn
        head = [i for i, l in enumerate(lines) if l == f'  "{tn}": {{']
        assert len(head) == 1, (tn, head)
        i = head[0]
        while lines[i] != '   "hard": false,':
            i += 1
            assert not lines[i].startswith("  }"), tn
        lines.insert(i + 1, '   "ln_copies": true,')
        t["ln_copies"] = True
        done.append(tn)
    new = "\n".join(lines)
    assert json.loads(new) == P, "line edit is not the dict edit"
    errs = []
    for tn in done:
        S._check(P["partition_types"][tn]["ln_copies"],
                 S.SCHEMA["properties"]["partition_types"]["additionalProperties"]["properties"]["ln_copies"], tn, errs)
    assert not errs, errs
    Path(out).write_text(new)
    Path(rep).write_text(json.dumps(dict(event="ln_copies_1108", types=done, lines_added=len(done),
                                         cycles_changed=0), indent=1) + "\n")
    print(json.dumps(dict(types=done)))


if __name__ == "__main__":
    main()
