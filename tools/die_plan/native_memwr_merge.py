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


def merge_memwr(sv_text, chunk=CHUNK):
    """Return (text, [(memory, statements before, statements after)]). Single statements are left as written."""
    ms = list(_STMT.finditer(sv_text))
    if len(ms) < MIN_STATEMENTS:
        return sv_text, []
    out, pos, stats, i = [], 0, {}, 0
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
        key = m.group("mem")
        b, a = stats.get(key, (0, 0))
        out.append(sv_text[pos:m.start()])
        if len(run) == 1 or m.group("hi") != m.group("lo"):
            out.append(sv_text[m.start():run[-1].end()])
            stats[key] = (b + len(run), a + len(run))
        else:
            n, lo, e = len(run), m.group("lo"), m.group("ei")
            dv = f"{{{n}{{{m.group('k')}}}}}" if m.group("k") else f"{m.group('d')}[{m.group('di')} +: {n}]"
            sl = f"{m.group('mem')} [{m.group('addr')}][{lo} +: {n}]"
            en = f"{m.group('en')}[{e} +: {n}]"
            out.append(f"{m.group('ind')}{sl} <= ({sl} & ~{en}) | ({dv} & {en});\n")
            stats[key] = (b + n, a + 1)
        pos = run[-1].end()
        i += len(run)
    out.append(sv_text[pos:])
    return "".join(out), [(k, b, a) for k, (b, a) in stats.items()]
