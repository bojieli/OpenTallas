"""Optional AHUB same-edge fault capture factorization; no canonical activation."""
from __future__ import annotations
import argparse
import re
from pathlib import Path

OLD_CAPTURE = """            gqv[2]<=(m_issue && lm_seen!=16'hffff) ||
                ((|issue) && (done_seen!=4'hf || zseen[0][63:0]!=zmask || zseen[1][63:0]!=zmask ||
                    zseen[2][63:0]!=zmask || zseen[3][63:0]!=zmask));"""
NEW_CAPTURE = """            // Same-edge captures; the existing |gqv consumer observes the identical error.
            gqv[2]<=(m_issue && lm_seen!=16'hffff) || ((|issue) && done_seen!=4'hf);
            for(integer fg_a=0;fg_a<4;fg_a=fg_a+1)
                for(integer fg_s=0;fg_s<4;fg_s=fg_s+1)
                    gqv[5+4*fg_a+fg_s] <= (|issue) &&
                        (zseen[fg_a][16*fg_s+:16] != zmask[16*fg_s+:16]);"""


def factor_fault_capture(text: str, module_name: str) -> str:
    """Change only the explicitly selected current core, refusing ambiguous input."""
    matches = list(re.finditer(r"(?m)^module\s+" + re.escape(module_name) + r"\b[\s\S]*?^endmodule\b", text))
    if len(matches) != 1:
        raise ValueError(f"expected exactly one {module_name} module")
    match = matches[0]
    body = match.group()
    if body.count(OLD_CAPTURE) != 1 or body.count("reg [4:0] gqv;") != 1:
        raise ValueError("unexpected AHUB fault capture source; no transformation applied")
    if body.count("gqv<=0") != 1 or body.count("(|gqv || |gz || |tq)") != 1:
        raise ValueError("unexpected AHUB reset/observable fault consumer")
    body = body.replace("reg [4:0] gqv;", "reg [20:0] gqv;", 1)
    body = body.replace(OLD_CAPTURE, NEW_CAPTURE, 1)
    # This bank has a different state encoding: bit2 is now the scalar class,
    # with compare classes in16 new bits. Give it an honest distinct name so
    # equivalence does not assert the old internal bit2 as a correspondence.
    body = re.sub(r"\bgqv\b", "gqv_groups", body)
    return text[:match.start()] + body + text[match.end():]


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("source", type=Path)
    p.add_argument("--module", required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        p.error("output exists; preserve prior candidates")
    a.out.write_text(factor_fault_capture(a.source.read_text(), a.module))


if __name__ == "__main__":
    main()
