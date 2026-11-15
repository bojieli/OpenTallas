"""Mark the arrays of bind-generated native memories that Yosys write_verilog expanded into many single-bit write
statements as (* mem2reg *), so the Yosys frontend turns them into registers BEFORE the memory passes.

Why: write_verilog prints each write port's per-bit enable as one `if (EN[i]) mem[A][i:i] <= D[i];` statement, so a
256 x 40 memory with 16 write ports re-reads as 4096 $memwr cells (S81 svc hi, ot_bind_native_dc625d1e). Yosys
opt_mem_priority / memory_share are superlinear in write ports and sat 2 h 15 min on the S81 svc hi kits. mem2reg
is exact (register array with the same per-statement write semantics and priority); memory_map would produce the same
flops later. A single wide masked write port is NOT equivalent when two ports of one clock write the same word with
disjoint masks (the second read-modify-write would restore the bits the first port wrote), so it is not used.
"""
import re

MIN_WRITES = 64
_DECL = re.compile(r"^(?P<ind>[ \t]*)reg (?P<rng>\[\d+:0\]) (?P<mem>\\\\?[A-Za-z_][A-Za-z0-9_]*)(?P<sp>\s+)(?P<dep>\[\d+:\d+\]);", re.M)


def mark_mem2reg(sv_text, min_writes=MIN_WRITES):
    """Return (text, [memory names marked]). Memories with fewer than min_writes write statements are untouched."""
    marked = []

    def fix(m):
        mem = m.group("mem")
        n = len(re.findall(r"<= ", "\n".join(l for l in sv_text.splitlines() if l.lstrip().startswith(mem))))
        if n < min_writes or "mem2reg" in sv_text[max(0, m.start() - 20):m.start()]:
            return m.group(0)
        marked.append(mem)
        return f"{m.group('ind')}(* mem2reg *) reg {m.group('rng')} {mem}{m.group('sp')}{m.group('dep')};"
    return _DECL.sub(fix, sv_text), marked
