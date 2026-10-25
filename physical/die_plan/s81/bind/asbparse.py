"""parse the one-line-per-instance die_asb.v (dv_die) into instances: module, params text, name, ordered conns."""
import re, sys, json

INST_RE = re.compile(r"^(\s*)([A-Za-z_][\w$]*)\s*(#\((.*?)\))?\s+([A-Za-z_][\w$\\\[\].]*)\s*\((.*)\);\s*$")


def split_top(s, sep=","):
    out, depth, cur = [], 0, []
    for ch in s:
        if ch in "({[":
            depth += 1
        elif ch in ")}]":
            depth -= 1
        if ch == sep and depth == 0:
            out.append("".join(cur)); cur = []
        else:
            cur.append(ch)
    if cur and "".join(cur).strip():
        out.append("".join(cur))
    return out


def parse_conns(body):
    conns = []
    for c in split_top(body):
        c = c.strip()
        m = re.match(r"^\.([\w$]+)\s*\((.*)\)$", c, re.S)
        if not m:
            raise ValueError("bad conn %r" % c[:80])
        conns.append([m.group(1), m.group(2).strip()])
    return conns


KW = {"module", "endmodule", "input", "output", "wire", "reg", "assign", "inout", "always", "localparam", "parameter"}


def parse(path):
    lines = open(path).read().split("\n")
    insts = {}
    for i, ln in enumerate(lines):
        if not ln.strip().endswith(");") or ln.lstrip().split(" ", 1)[0] in KW:
            continue
        # params may contain parentheses: find "#(" balanced
        s = ln.strip()
        m = re.match(r"^([A-Za-z_][\w$]*)\s*", s)
        if not m:
            continue
        mod = m.group(1); rest = s[m.end():]
        params = None
        if rest.startswith("#("):
            d = 0
            for j, ch in enumerate(rest):
                if ch == "(":
                    d += 1
                elif ch == ")":
                    d -= 1
                    if d == 0:
                        break
            params = rest[2:j]; rest = rest[j + 1:].lstrip()
        m2 = re.match(r"^([A-Za-z_\\][^\s(]*)\s*\(", rest)
        if not m2:
            continue
        name = m2.group(1); body = rest[m2.end():]
        assert body.endswith(");"), (i, s[:100])
        body = body[:-2]
        try:
            conns = parse_conns(body)
        except ValueError:
            continue
        insts[name] = dict(line=i, module=mod, params=params, conns=conns)
    return lines, insts


def emit(mod, params, name, conns):
    p = (" #(%s)" % params) if params is not None else ""
    return "  %s%s %s (%s);" % (mod, p, name, ", ".join(".%s(%s)" % (a, b) for a, b in conns))


if __name__ == "__main__":
    lines, insts = parse(sys.argv[1])
    print(len(insts))
    pat = re.compile(sys.argv[2]) if len(sys.argv) > 2 else None
    for n, d in insts.items():
        for p, e in d["conns"]:
            if pat and pat.search(e):
                print(n, d["module"], p, e[:120])
