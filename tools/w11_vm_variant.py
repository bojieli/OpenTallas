#!/usr/bin/env python3
"""W11 VM variants (VM-H, C_rotate): source-list selection, so main's pinned files stay byte-identical.

User decision (AGENTS.md a4f314fb): opt-in work lives in NEW files selected by the source list; the files main's
committed records pin are not edited.  The VM-H / C_rotate versions of six main files therefore live in
rtl/w11crot/ under their main basenames and module names (same ports and defaults: with VM_DIST = VM_CROT = 0
they are the main units plus opt-in parameters):

  ot_hdc_v41x_vec.sv        VMD_NG (VM-H), RD_LEAD / CROT_GX (C_rotate)
  ot_hdc_v41x_su_adapt.sv   pass-throughs
  ot_hdc_core_v41x.sv       VM_DIST trees, VM_DIST_H, VM_CROT / CR_*, SU_MLAT / SU_ALAT
  ot_chip_v41x_tile.sv      the banked VM (ot_v41_vm_dist / ot_v41_vm_crot) in place of the flat array
  ot_chip_v41x_die.sv       pass-throughs
  tb_hdc_v41x_vec.sv        the SU bench with VM_DIST / VM_DIST_H / VM_CROT

install() swaps them into the campaign tools' source lists (rtl_hdc_v41x_vec_campaign RTL / TB,
w11_su_softmax_spec TB_VEC / ADAPT, rtl_chip_v41x_die_smoke.sources) by basename, and installs VM-H's two python
rules that used to be edits of main's tools, now applied here:
  * the unit's VM-H layout (ot_hdc_v41x_vec VMD_NG h_seg): rtl_hdc_v41x_vec_campaign.layout lays an op one row a
    vector when C.VMD_NG is set and its streams would need a different rotation per row slot (C.VMD_NG = 0: the
    layout unchanged);
  * the builder's VM alignment (HDC_V41_VM_ALIGN, default 32 = unchanged): hdc_program_v41's allocator aligns every
    vector-memory region to it.
Importing this module installs everything (idempotent).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_isa_v41 as I                    # noqa: E402
import hdc_program_v41 as P                # noqa: E402
import rtl_hdc_v41x_vec_campaign as C      # noqa: E402

VARIANT_DIR = ROOT / "rtl/w11crot"
VARIANTS = {p.name: p for p in sorted(VARIANT_DIR.glob("*.sv"))}


def swap(paths):
    """The list with every main file that has a variant replaced by it (by basename), order kept."""
    out = []
    for p in paths:
        q = VARIANTS.get(Path(p).name, p) if Path(p).parent != VARIANT_DIR else p
        out.append(type(p)(q) if isinstance(p, (str, Path)) else q)
    return out


# ---- VM-H layout rule (was an edit of rtl_hdc_v41x_vec_campaign.layout) -----------------------------------------
def vmd_segmented(f, S, no_f, ni_f, ng):
    """Option H: an op packed several rows a vector whose streams would need a different rotation in every row
    slot (a unit stream with so != S mod ng, a per-row scalar with so != 0).  The unit then lays it out one row a
    vector (ot_hdc_v41x_vec VMD_NG, h_seg)."""
    mk = ng - 1
    if no_f <= 1:
        return False
    st = []
    for s in "abcd":
        if f[f"{s}src"] == I.SRC_VM and not (s == "a" and f["aind"]) and not (s == "c" and f["cpair"]) and \
                not (s in "bd" and f["bhalf"] and f[f"{s}si"] != 0):
            st.append((f[f"{s}so"], f[f"{s}si"]))
    if f["aind"] == I.IND_I:
        st.append((0, 1))
    elif f["aind"] == I.IND_O:
        st.append((1, 0))
    if f["dst"] == I.DST_VM:
        st.append((f["oso"], f["osi"]))
    for so, si in st:
        if (si == 1 or ni_f == 1) and ((so - S) & mk) != 0:
            return True
        if si == 0 and ni_f > 1 and so != 0:
            return True
    return False


def _install_layout():
    if getattr(C, "_w11_vm_layout", None):
        return
    base = C.layout
    C.VMD_NG = getattr(C, "VMD_NG", 0)

    def layout(f, N, M):
        if not C.VMD_NG:
            return base(f, N, M)
        lay = base(f, N, M)
        if not lay["nsh"]:
            return lay
        no_f, ni_f = (1, f["nout"] * f["nin"]) if lay["flat"] else (f["nout"], f["nin"])
        if not vmd_segmented(f, lay["S"], no_f, ni_f, C.VMD_NG):
            return lay
        # re-lay one row a vector: the layout as if the op could not pack (nsh = 0)
        return _unpacked(base, f, N, M, lay)
    C._w11_vm_layout = base
    C.layout = layout


def _unpacked(base, f, N, M, lay):
    """The H layout of a packed op laid one row a vector: rtl_hdc_v41x_vec_campaign.layout with nsh forced to 0.
    Implemented by re-running the layout's vector walk with nslot = 1 (the function's own code path for nsh = 0)."""
    import numpy as np
    ls, S = lay["ls"], lay["S"]
    flat = lay["flat"]
    no_f, ni_f = (1, f["nout"] * f["nin"]) if flat else (f["nout"], f["nin"])
    ni = f["nin"]
    vecs = []
    o_v = i_v = 0
    use = 1 << ls
    while True:
        lanes = np.arange(use)
        d_o, d_i = lanes >> ls, lanes & (S - 1)
        oo, ii = o_v + d_o, i_v + d_i
        live = (oo < no_f) & (ii < ni_f)
        if flat:
            g = ii[live]
            vecs.append((g // ni, g % ni))
        else:
            vecs.append((oo[live], ii[live]))
        wrap = lay["packed"] or (i_v + S >= ni_f)
        last = wrap and (o_v + 1 >= no_f)
        if last:
            break
        if wrap:
            o_v, i_v = o_v + 1, 0
        else:
            i_v += S
    return dict(lay, nsh=0, vecs=vecs, nv=len(vecs))


# ---- the builder's VM alignment (was an edit of hdc_program_v41.Layout) ----------------------------------------
def _install_align():
    if getattr(P, "_w11_vm_align", None):
        return
    base = P.Alloc

    class Alloc(base):
        def __init__(self, size, align=None):
            if align is not None:
                return super().__init__(size, align=align)
            va = 32
            if size in (I.VM_ELEMS, getattr(I, "VM_ELEMS_MTP", None)):      # the vector memory's allocator only
                va = int(os.environ.get("HDC_V41_VM_ALIGN", "32"))
                assert va >= 32 and va & (va - 1) == 0, "HDC_V41_VM_ALIGN: a power of two >= 32"
            super().__init__(size, align=va)
    P._w11_vm_align = base
    P.Alloc = Alloc


def install():
    _install_layout()
    _install_align()
    C.RTL[:] = swap(C.RTL)
    C.TB = swap([C.TB])[0]
    try:
        import w11_su_softmax_spec as SM
        SM.TB_VEC = swap([SM.TB_VEC])[0]
        SM.ADAPT = swap([SM.ADAPT])[0]
    except ImportError:
        pass
    import rtl_chip_v41x_die_smoke as ds
    if not getattr(ds, "_w11_vm_sources", None):
        base = ds.sources
        ds._w11_vm_sources = base
        ds.sources = lambda *a, **k: swap(base(*a, **k))


install()
