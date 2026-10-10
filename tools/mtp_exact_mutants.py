"""Negative mutants of the MTP exactness regression (mtp-exact 2026-10-08), made as PATCHED COPIES in a run
directory: the pinned sources stay byte-identical.

accept_extra  rtl/hdc/ot_hdc_accept.sv with one extra draft accepted whenever the matching prefix stops short of
              g (a < g -> a + 1): the step emits a rejected draft and commits one position too many.  Shared by
              the DS ROM core (ot_hdc_core_v41) and the HBM DSpark loop (ot_dshbm_accept_port -> ot_hdc_accept).
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACCEPT = ROOT / "rtl/hdc/ot_hdc_accept.sv"
_ANCHOR = """            if (run) a_c = i + 1;
            /* verilator lint_on WIDTH */
        end
"""
_EXTRA = """        // MUTANT accept_extra (mtp-exact negative control): accept one draft past the first mismatch
        /* verilator lint_off WIDTH */
        if (a_c < acc_g) a_c = a_c + 1;
        /* verilator lint_on WIDTH */
"""


def accept_extra(outdir: Path) -> Path:
    src = ACCEPT.read_text()
    assert src.count(_ANCHOR) == 1, "ot_hdc_accept.sv changed: re-anchor the accept_extra mutant"
    out = Path(outdir) / "mutant_accept_extra" / "ot_hdc_accept.sv"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(src.replace(_ANCHOR, _ANCHOR + _EXTRA))
    return out


def swap(sources, original: Path, replacement: Path):
    paths = [Path(p) for p in sources]
    hits = [i for i, p in enumerate(paths) if p.resolve() == original.resolve()]
    assert len(hits) == 1, (original, hits)
    paths[hits[0]] = replacement
    return paths
