#!/usr/bin/env python3
"""S81 as-built param_regen hook (DIE-S81-56/PLAN 11-04, COORD 17:3x).  The signed RF-J xrt1 / xrt3 were built with -DOT_S81SL_XRT_RFJ
-DOT_S81SL_XRT_OLAT (config.mk, signed kits flow-20261104-k-s81) and FOREG from the ref_tile spec.  The as-built elaboration has none of these,
so the bound parents pass RING_LAND 0 / FACE_LAND 1 / OLAT 0 (and FOREG 0 on xrt3).  Bound overrides take the signed values, so parent and
generated bb header (gen_phys.macro_param_blackboxes) state one identity; native_bb checks them against each other.  Black boxes in the parent: no
RTL body changes.  PDSK and QDELAYS already equal the signed build.
"""
SIGNED = {"ot_s81sl_xrt1": dict(FOREG=0, FACE_LAND=2, RING_LAND=2, OLAT=1),
          "ot_s81sl_xrt3": dict(FOREG=1, FACE_LAND=2, RING_LAND=2, OLAT=1)}


def regen(ctx):
    params = {c.path: SIGNED[c.module] for c in ctx.F.cells if c.module in SIGNED}
    return dict(params=params, record=dict(leaves=len(params), source="signed RF-J kits config.mk + spec FOREG"))
