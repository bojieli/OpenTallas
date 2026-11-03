"""DIE-KV-62/hr 11-02: drive recipe-declared spare (reserved, parent-tied) output bits as constant 0 in the kit RTL.

qkd_hr_cdc_pc u_tx__o_d[545:528] are reserved bits (KV-018, kit spare_out.json, face_guard spare_declared): the native
register u_tx__o_d <= od_q <= async-FIFO rd_data carries constant-0 writes through UNRESET FIFO storage, so the RTL
value is X until every entry was written once and 0 after.  Synthesis folds the X to 0 (TIELO); the kit LEC (no X
refinement on unreset storage) reports the 18 outputs 'differs' and the kit stops (LEC NOT EQUIVALENT).  The fix is
the X refinement in the kit RTL itself: the one statement that drives the bus loads its spare bits with 0
(`B <= (EXPR) & MASK;`), so the register bits are 0 from the first edge (LEC reset-window constant) and every other
bit is untouched.  Fail-closed: exactly one whole-bus driver (`B <= ...;` or `assign B = ...;`) and a declared
width that holds every spare bit.

recipe:  "spare_out_bits": ["B[i]", ...], "spare_out_tie": true
"""
import re


def transform(text, bits):
    """text (flat kit RTL), bits ['BUS[i]', ...] -> (new text, report)."""
    by = {}
    for b in bits:
        m = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*)\[(\d+)\]", b)
        if not m:
            raise SystemExit(f"hr_spare_tie: bad spare bit {b}")
        by.setdefault(m.group(1), set()).add(int(m.group(2)))
    rep = []
    for bus, idx in sorted(by.items()):
        d = re.search(rf"^\s*output\s+\[(\d+):0\]\s+{re.escape(bus)}\s*;", text, re.M)
        if not d:
            raise SystemExit(f"hr_spare_tie: no output [N:0] {bus}")
        w = int(d.group(1)) + 1
        if max(idx) >= w:
            raise SystemExit(f"hr_spare_tie: {bus} width {w} lacks bit {max(idx)}")
        pat = re.compile(rf"^(\s*(?:assign\s+)?){re.escape(bus)}(\s*(?:<=|=)\s*)([^;]*);", re.M)
        hits = pat.findall(text)
        if len(hits) != 1:
            raise SystemExit(f"hr_spare_tie: {bus}: {len(hits)} whole-bus drivers (want exactly 1)")
        mask = sum(1 << i for i in range(w) if i not in idx)
        text = pat.sub(lambda m: f"{m.group(1)}{bus}{m.group(2)}({m.group(3)} ) & {w}'h{mask:x};"
                       f"  // DIE-KV-62/hr hr_spare_tie: spare bits {min(idx)}..{max(idx)} = 0", text, count=1)
        rep.append(dict(bus=bus, width=w, spare=sorted(idx), driver=hits[0][0].strip() or "always"))
    return text, rep
