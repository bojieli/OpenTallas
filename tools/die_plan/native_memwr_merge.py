"""Merge the per-bit write statements that Yosys write_verilog prints for a $mem_v2 into chunk-wide statements.

write_verilog prints one `if (EN[i]) mem[A][i:i] <= D[i];` per write-port data bit.  Read back, each is its own
$memwr / process action (S81 svc: u_att_pvq 2120, u_att_land 1232, u_att_pmem 512, u_att_hold 512, u_att_fq 416, 4,792
in all), and yosys canonicalize sits hours in PROC_PRUNE / PROC_DFF.  A run of consecutive bits of ONE port (same memory,
same address expression, same enable and data vectors) is replaced by one read-modify-write of the run:

    mem[A][lo +: n] <= (mem[A][lo +: n] & ~EN[e +: n]) | (D[e +: n] & EN[e +: n]);

Exact for 2-state values: every bit takes D where its enable is 1 and keeps its old value elsewhere, which is the
per-bit statement.  Runs are disjoint bit ranges of one port, so no priority relation changes, and runs are only merged
when adjacent in the text, so the statement order between ports is untouched.  This is NOT one wide port: a 2120-bit
port is cut into chunks of at most CHUNK bits, so a memory ends with ceil(bits / CHUNK) write statements per port.
"""
import re

CHUNK = 256
MIN_STATEMENTS = 64   # memories with fewer per-bit statements are left as write_verilog printed them (same bar as native_mem2reg)
_STMT = re.compile(
    r"(?P<ind>[ \t]*)if \((?P<en>[A-Za-z_]\w*)\[(?P<ei>\d+)\]\)\n[ \t]*(?P<mem>\S+) \[(?P<addr>[^\n]*?)\]"
    r"\[(?P<hi>\d+):(?P<lo>\d+)\] <= (?:(?P<d>[A-Za-z_]\w*)\[(?P<di>\d+)\]|(?P<k>1'[hb][01]));[ \t]*\n")


def _zpad(core, pre, post):
    parts = ([f"{post}'b0"] if post else []) + [core] + ([f"{pre}'b0"] if pre else [])
    return core if len(parts) == 1 else "{" + ", ".join(parts) + "}"


def merge_memwr(sv_text, chunk=CHUNK):
    """Return (text, [(memory, statements before, statements after)]). Single statements are left as written.

    Exactness across ports: the statements of one always block are nonblocking, the LAST one that is enabled wins per bit.  A merged
    read-modify-write of a later chunk reads the OLD word, so it would undo an earlier statement's write to the same word when this
    chunk's enable bit is 0 (LEC on land: ports at different addresses, bit ranges overlapping).  Every merged chunk therefore starts from
    the word as the earlier overlapping statements of the same memory leave it:  base = (base & ~M) | (d & M),  M = (addresses equal) & en,
    per earlier overlapping statement, in text order."""
    ms = list(_STMT.finditer(sv_text))
    if len(ms) < MIN_STATEMENTS:
        return sv_text, []
    runs, i = [], 0
    while i < len(ms):
        m = ms[i]
        run = [m]
        while i + len(run) < len(ms) and len(run) < chunk:
            p, n = run[-1], ms[i + len(run)]
            same = all(p.group(k) == n.group(k) for k in ("ind", "en", "mem", "addr", "d", "k"))
            ok = (same and n.start() == p.end() and p.group("hi") == p.group("lo") and n.group("hi") == n.group("lo")
                  and int(n.group("ei")) == int(p.group("ei")) + 1 and int(n.group("lo")) == int(p.group("lo")) + 1)
            ok = ok and (n.group("k") is not None or int(n.group("di")) == int(p.group("di")) + 1)
            if not ok:
                break
            run.append(n)
        single = len(run) == 1 or m.group("hi") != m.group("lo")
        if single:
            run = run[:1] if m.group("hi") != m.group("lo") else run
        lo = int(m.group("lo")); hi = int(m.group("hi"))
        runs.append(dict(mem=m.group("mem"), addr=m.group("addr"), ind=m.group("ind"), en=m.group("en"), e0=int(m.group("ei")),
                         d=m.group("d"), di=int(m.group("di")) if m.group("di") else None, k=m.group("k"),
                         lo=lo, n=(hi - lo + 1) if m.group("hi") != m.group("lo") else len(run), merge=len(run) > 1 and not (m.group("hi") != m.group("lo")),
                         start=m.start(), end=run[-1].end(), count=len(run)))
        i += len(run)
    out, pos, stats = [], 0, {}
    for ix, r in enumerate(runs):
        b, a = stats.get(r["mem"], (0, 0))
        out.append(sv_text[pos:r["start"]])
        if not r["merge"]:
            out.append(sv_text[r["start"]:r["end"]])
            stats[r["mem"]] = (b + r["count"], a + r["count"])
        else:
            n, lo = r["n"], r["lo"]
            sl = f"{r['mem']} [{r['addr']}][{lo} +: {n}]"
            base = sl
            for e in runs[:ix]:
                if e["mem"] != r["mem"]:
                    continue
                o0, o1 = max(lo, e["lo"]), min(lo + n, e["lo"] + e["n"])
                if o0 >= o1:
                    continue
                w, pre, post = o1 - o0, o0 - lo, lo + n - o1
                eoff = o0 - e["lo"]
                enw = _zpad(f"{e['en']}[{e['e0'] + eoff} +: {w}]", pre, post)
                dw = _zpad(f"{{{w}{{{e['k']}}}}}" if e["k"] else f"{e['d']}[{e['di'] + eoff} +: {w}]", pre, post)
                mk = enw if e["addr"] == r["addr"] else f"({{{n}{{({e['addr']}) == ({r['addr']})}}}} & {enw})"
                base = f"(({base} & ~{mk}) | ({dw} & {mk}))"
            dv = f"{{{n}{{{r['k']}}}}}" if r["k"] else f"{r['d']}[{r['di']} +: {n}]"
            en = f"{r['en']}[{r['e0']} +: {n}]"
            out.append(f"{r['ind']}{sl} <= ({base} & ~{en}) | ({dv} & {en});\n")
            stats[r["mem"]] = (b + n, a + 1)
        pos = r["end"]
    out.append(sv_text[pos:])
    return "".join(out), [(k, b, a) for k, (b, a) in stats.items()]
