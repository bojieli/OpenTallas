"""Deterministic ft-input hold cells from the plan (S81/FTHOLD 2026-10-25; COORD 00:46 recipe "fix feedthrough-station
chains with deterministic delay cells from the plan").

Why.  An ft slot's station 0 is a FIRM face flop at the in pin (R2/R3) and the neighbour's last station drives the
abutted out pin, so the seam's min path has no logic.  The kit SDC holds that seam to the signed-early contract
(gen_phys.sdc): the neighbour launches at vclk = insertion_ps with min input delay -insertion_tol_ps (no clk-to-q / wire
credit, CP1 r9) and the receiver carries half the hold uncertainty (UNC_SPLIT).  Every ft input bit therefore needs, at
the FF corner, with its own capture clock at the budgeted insertion:

    need = insertion_tol_ps + UNC_SPLIT x UNC_HOLD_PS + t_hold(face flop, FF) - t(port buffer, FF)

(s81: 40 + 12.5 + 13.2 - 13.0 = 52.7 ps).  Measured on the S81 wavefront station kits (post-CTS, FF): t8 ft2_i
-71.2 ps = this need + 18.5 ps of capture insertion over the budget (tap tree clk_t12 271 ps FF vs vclk 250).  Before
this module the need was left to in-flow hold repair: 1858-6249 endpoints per kit, 17 of 30 station types stopped at
the post-CTS hold gate.

What.  With clock.ft_in_hold = "liberty" every ft input bit (data + epoch) goes through a fixed chain of ASAP7 hold
buffers (HB<n>xp67) before station 0: ot_dp_dly_<chain> in ot_dp_cells.sv, cells (* keep *), instance u_ftd_<slot>,
dont_touch for the whole flow (face_keep.tcl).  The chain is the one whose FF min delay (FF Liberty) covers the need
by 0..WINDOW_PS with the smallest TT max delay; the receiver's ft setup share grows by exactly that TT delay
(gen_phys.ft_hop_in_share: input delay max (1 - share) T, the sender's ft_o output delay max share T), so no cycle is
added and the sender keeps the rest of the seam.  clock.ft_in_hold_ps overrides the need (ps).  Off by default.

Residual negative hold after CTS is the capture tree's insertion above the budget (OT_TAP_CHECK WARN): a clock-tree
item, repaired in flow at margin 0..5 ps, never by a blanket margin here.
"""

# ASAP7 RVT Liberty (asap7sc7p5t_INVBUF_RVT_{FF,TT}_nldm_220122.lib), cell_rise / cell_fall at 15 ps input slew.
# ff_min_ps: min(rise, fall) at 0.6 fF (a chain stage: next cell / D pin + short wire; low load = early = hold-safe);
# tt_max_ps: max(rise, fall) at 0.9 fF (late = setup-safe).  Recompute with test_ft_hold.py when the library changes.
CELLS = {
    "HB1xp67_ASAP7_75t_R": (15.50, 23.54),
    "HB2xp67_ASAP7_75t_R": (22.70, 36.54),
    "HB3xp67_ASAP7_75t_R": (30.24, 51.11),
    "HB4xp67_ASAP7_75t_R": (38.45, 67.23),
}
# DFFHQNx1_ASAP7_75t_R hold_rising fall_constraint (SEQ_RVT_FF_nldm_220123), clock 10 ps / D 20 ps slew (HB output):
# 13.18 ps (STA on t8 4_cts: 12.1 ps)
TH_FF_PS = 13.2
# ORFS buffer_ports input buffer (BUFx2_ASAP7_75t_R) on every input port, FF min ~0.7 fF (STA on t8 4_cts: 13.1 ps)
PORT_BUF_FF_PS = 13.0
# chain length: face_flops.tcl finds an in port's face flop through <= 2 buffers (face_guard.MAX_CHAIN 3 incl. the
# port buffer), so at most 2 plan cells
MAX_CELLS = 2
WINDOW_PS = 5.0


class FtHoldError(Exception):
    pass


def enabled(P):
    return P.clock.get("ft_in_hold", "off") == "liberty"


def need_ps(P):
    """FF hold need of an ft input bit at the budgeted capture insertion (ps); clock.ft_in_hold_ps overrides."""
    if "ft_in_hold_ps" in P.clock:
        return float(P.clock["ft_in_hold_ps"])
    import gen_phys
    return (float(P.clock["insertion_tol_ps"]) + gen_phys.UNC_SPLIT * gen_phys.UNC_HOLD_PS + TH_FF_PS
            - PORT_BUF_FF_PS)


def pick(need):
    """the cell chain for a need (ps): FF sum in [need, need + WINDOW_PS], smallest TT max (then fewest cells);
    else the smallest FF sum >= need.  -> (cells tuple, ff_ps, tt_ps); () for need <= 0."""
    if need <= 0:
        return (), 0.0, 0.0
    names = sorted(CELLS)
    combos = [(a,) for a in names] + [(a, b) for i, a in enumerate(names) for b in names[i:]]
    combos = [c for c in combos if len(c) <= MAX_CELLS]
    rows = []
    for c in combos:
        ff = sum(CELLS[x][0] for x in c)
        tt = sum(CELLS[x][1] for x in c)
        if ff >= need:
            rows.append((c, ff, tt))
    if not rows:
        raise FtHoldError(f"ft_in_hold: need {need:.1f} ps exceeds {MAX_CELLS} x HB4 "
                          f"({MAX_CELLS * CELLS['HB4xp67_ASAP7_75t_R'][0]:.1f} ps FF): fix the clock contract")
    win = [r for r in rows if r[1] <= need + WINDOW_PS]
    pool = win or rows
    key = (lambda r: (r[2], len(r[0]))) if win else (lambda r: (r[1], r[2]))
    c, ff, tt = min(pool, key=key)
    # largest cell first (the slow edge leaves the port buffer, the fast HB1/HB2 edge drives the face flop D)
    c = tuple(sorted(c, key=lambda x: -CELLS[x][0]))
    return c, round(ff, 2), round(tt, 2)


def chain(P):
    """(cells, ff_ps, tt_ps) of the plan, () when ft_in_hold is off."""
    if not enabled(P):
        return (), 0.0, 0.0
    return pick(need_ps(P))


def module_name(cells):
    return "ot_dp_dly_" + "_".join(c.split("xp")[0].lower() for c in cells)


def module_text(P):
    """ot_dp_dly_<chain> for the plan's chain ('' when off).  Synthesis instantiates the Liberty cells; simulation and
    every other reader (`SYNTHESIS undefined) see a wire."""
    cells, ff, tt = chain(P)
    if not cells:
        return ""
    m = module_name(cells)
    nets = [f"n{i}" for i in range(len(cells) - 1)]
    ins = ["d[i]"] + nets
    outs = nets + ["q[i]"]
    inst = "\n".join(f"            (* keep *) {c} u{i} (.A({a}), .Y({y}));"
                     for i, (c, a, y) in enumerate(zip(cells, ins, outs)))
    decl = "".join(f"            wire {n};\n" for n in nets)
    return (f"// {m}: deterministic ft-input hold cells (tools/die_plan/ft_hold.py, plan clock.ft_in_hold): "
            f"{' + '.join(cells)} = {ff:g} ps FF min / {tt:g} ps TT max\n"
            f"// per bit before ft station 0 (need {need_ps(P):.1f} ps FF).  dont_touch in the kit (face_keep.tcl, never released).\n"
            "(* keep_hierarchy *)\n"
            f"module {m} #(parameter integer W = 1) (\n"
            "    input  wire [W-1:0] d,\n"
            "    output wire [W-1:0] q\n"
            ");\n"
            "`ifdef SYNTHESIS\n"
            "    genvar i;\n"
            "    generate\n"
            "        for (i = 0; i < W; i = i + 1) begin : g\n"
            f"{decl}{inst}\n"
            "        end\n"
            "    endgenerate\n"
            "`else\n"
            "    assign q = d;\n"
            "`endif\n"
            "endmodule\n")
