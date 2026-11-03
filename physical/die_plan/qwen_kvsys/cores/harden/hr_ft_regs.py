"""DIE-KV-62/hr 11-02: register a recipe-declared HR wire feed-through (output port bit = input port bit, no logic).

face_guard fails a 'feedthrough' bit (port wired to port through the core): the kit IO budget cannot bound an in -> out
arc with no core register, and the timed-face class (face_guard timed_face.json) never exempts it.  The real fix is a
face register: each declared OUTPUT bus bit gets one capture flop (D = its source input bit, same core clock, async
active-low reset to a declared value) and the pin is driven by Q only -- the input then has one flop load, the output
one flop driver.  This ADDS ONE EDGE on that signal (declared: kit hr_ft_regs.json, the parent bind / sim prices it);
it is only for fault/status-class signals named in the recipe with a ruling.  Fail-closed: every bit of the bus must
be exactly one `assign OUT[i] = IN[j];` in the flat kit RTL (hr_face_ports emitted .v), the clock / reset must be core
input ports, and nothing else may drive the output.

recipe:  "ft_face_regs": {"regs": [{"out": BUS, "clock": CK, "reset_n": RST, "reset_value": 0}], "ruling": .., "reason": ..}
"""
import json
import re


def _port_width(text, kind, name):
    m = re.search(rf"^\s*{kind}\s+(?:\[(\d+):(\d+)\]\s+)?{re.escape(name)}\s*;", text, re.M)
    if not m:
        raise SystemExit(f"hr_ft_regs: no {kind} port {name}")
    return int(m.group(1)) - int(m.group(2)) + 1 if m.group(1) else 1, m.group(1) is not None


def transform(text, spec):
    """text (flat kit RTL), spec (recipe ft_face_regs) -> (new text, report)."""
    if not str(spec.get("ruling") or "").strip() or not str(spec.get("reason") or "").strip():
        raise SystemExit("hr_ft_regs: ruling and reason are required")
    rep = []
    for r in spec["regs"]:
        out, ck, rst = r["out"], r["clock"], r["reset_n"]
        rv = int(r.get("reset_value", 0))
        if not all(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", n) for n in (out, ck, rst)):
            raise SystemExit(f"hr_ft_regs: bad names {r}")
        w, vec = _port_width(text, "output", out)
        _port_width(text, "input", ck)
        _port_width(text, "input", rst)
        srcs = []
        for i in range(w):
            lhs = rf"{re.escape(out)}\[{i}\]" if vec else re.escape(out)
            pat = re.compile(rf"^\s*assign\s+{lhs}\s*=\s*([A-Za-z_][A-Za-z0-9_]*)(\[\d+\])?\s*;\s*\n", re.M)
            hits = pat.findall(text)
            if len(hits) != 1:
                raise SystemExit(f"hr_ft_regs: {out}[{i}]: {len(hits)} direct port assigns (want exactly 1)")
            src = hits[0][0] + hits[0][1]
            _port_width(text, "input", hits[0][0])
            text = pat.sub("", text, count=1)
            srcs.append(src)
        drv = re.findall(rf"^\s*assign\s+{re.escape(out)}\b", text, re.M)
        if drv or re.search(rf"\.\w+\(\s*{re.escape(out)}\b", text):
            raise SystemExit(f"hr_ft_regs: {out} has other drivers/loads after removing the feed-through")
        q = f"ot_ftreg_{out}"
        rng = f"[{w - 1}:0] " if vec else ""
        cat = "{" + ", ".join(reversed(srcs)) + "}" if vec else srcs[0]
        blk = (f"  // DIE-KV-62/hr hr_ft_regs: face register on the wire feed-through {out} (+1 edge, declared)\n"
               f"  (* keep *) reg {rng}{q};\n"
               f"  always @(posedge {ck}, negedge {rst})\n"
               f"    if (!{rst}) {q} <= {w}'d{rv};\n"
               f"    else {q} <= {cat};\n"
               f"  assign {out} = {q};\n")
        end = text.rfind("endmodule")
        if end < 0:
            raise SystemExit("hr_ft_regs: no endmodule")
        text = text[:end] + blk + text[end:]
        rep.append(dict(out=out, src=srcs, clock=ck, reset_n=rst, reset_value=rv, added_edges=1, flops=w))
    return text, rep


def write_report(kd, rep, spec):
    (kd / "hr_ft_regs.json").write_text(json.dumps(dict(
        schema="opentallas.kit_hr_ft_regs.v1", regs=rep, ruling=spec["ruling"], reason=spec["reason"],
        note="each listed output is the input delayed by ONE core clock edge (face register); the parent bind / "
             "sim must price +1 edge on these signals"), indent=1) + "\n")
