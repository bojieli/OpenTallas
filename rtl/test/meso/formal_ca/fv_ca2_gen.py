#!/usr/bin/env python3
"""MESO-COUNT-2: generate the SymbiYosys files for fv_ca2.sv (count-aligned landing, ot_dp_clk_landing_ca).

  fv_ca2_full.sby   full anyconst lag range, D4 (RRM 12, 63) and D8 (RRM 20, 127): BMC of A_SAFE/A_NOFLT/A_LIVE,
                    reachability (A_REACH), fail-closed (A_FLT), helper-invariant BMC, mutants K/FREERUN/NO_GUARD/NO_TAG
  fv_ca2_k4.sby / fv_ca2_k8.sby
                    one task per static configuration (phase PH 0..7 x whole-cycle start offset OFF = RR - SR), mode bmc
                    depth 1 (model build only); fv_ca2_kind.sh then runs abc on the folded model:
                      base case  bmc3 -F B   (no assertion fails in B steps)
                      step case  scorr; dc2; ind -F k -u   ("Networks are equivalent" = k-inductive, k <= B)
                    proving A_ALL = A_SAFE && A_NOFLT && strengthening invariants (FV_ONE, FV_NOLIVE) UNBOUNDED.
  fv_ca2_mut.sby    the same flow on mutants (base case must fail)
The strengthening invariants read DUT state through h_* / h2_* harness wires driven by `connect` after flatten.
"""
R = "ot_meso_fifo.sv ot_dp_clk_landing.sv ot_dp_clk_landing_ca.sv fv_ca2.sv"
FILES = ["../../../common/ot_meso_fifo.sv", "../../../common/ot_dp_clk_landing.sv",
         "../../../common/ot_dp_clk_landing_ca.sv", "fv_ca2.sv"]


def conn(D):
    c = ["proc", "flatten", "memory_map", "cd fv_ca2",
         "connect -set h_tc dut.u_ring.tc", "connect -set h_rp dut.u_ring.rp", "connect -set h_oh dut.u_ring.oh",
         "connect -set h_di dut.u_ring.dch[0].u_dsel.di", "connect -set h_sw dut.u_ring.s_w",
         "connect -set h_slap dut.u_ring.s_lap"]
    c += [f"connect -set h_stag[{3*i+2}:{3*i}] dut.u_ring.g_tag.s_tag[{i}]" for i in range(D)]
    c += [f"connect -set h_sd[{i}] dut.u_ring.s_d[{i}][0]" for i in range(D)]
    c += ["connect -set h2_seen dut.seen", "connect -set h2_fs dut.fault_state", "connect -set h2_rvq dut.u_ring.r_v_q",
          "connect -set h2_rlq dut.u_ring.r_lap_q", "connect -set h2_yq dut.u_ring.dch[0].u_dsel.genblk1.g_reg.y_q[0]",
          "connect -set h2_dxq dut.u_ring.fv_dx_q", "connect -set h2_arm dut.arm_cnt"]
    c += [f"connect -set h2_glo[{i}] dut.u_ring.glo{i}" for i in range(4)]
    c += [f"connect -set h2_ghi[{i}] dut.u_ring.ghi{i}" for i in range(4)]
    return c + ["cd .."]


def write(name, tasks):
    """tasks: name -> (mode, depth or None, engine, defines, D, helpers)"""
    o = ["[tasks]"] + list(tasks) + ["", "[options]"]
    for t, (m, dp, e, d, D, h) in tasks.items():
        o.append(f"{t}: mode {m}")
        if dp:
            o.append(f"{t}: depth {dp}")
    o += ["multiclock on", "aigsmt none", "", "[engines]"] + [f"{t}: {v[2]}" for t, v in tasks.items()]
    o += ["", "[script]"] + [f"{t}: read -formal -DOT_MESO_CA_FV {v[3]} {R}" for t, v in tasks.items()]
    o += ["hierarchy -top fv_ca2", "setattr -mod -unset keep_hierarchy *"]
    for t, v in tasks.items():
        if v[5]:
            o += [f"{t}: {c}" for c in conn(v[4])]
    o += ["prep -top fv_ca2", "", "[files]"] + FILES
    open(name, "w").write("\n".join(o) + "\n")


full = {}
for D, rrs in ((4, (12, 63)), (8, (20, 127))):
    for rr in rrs:
        b = f"D{D}_R{rr}"; dd = f"-DFV_D={D} -DFV_RRM={rr}"
        full[f"bmc_{b}"] = ("bmc", {12: 800, 63: 1100, 20: 1300, 127: 2100}[rr], "abc bmc3", dd, D, False)
        full[f"reach_{b}"] = ("bmc", 400, "abc bmc3", dd + " -DFV_REACH", D, False)
        full[f"flt_{b}"] = ("bmc", 420 if D == 4 else 600, "abc bmc3", dd + " -DFV_FLT -DFV_SAFE_ONLY", D, False)
        full[f"hbmc_{b}"] = ("bmc", 300, "abc bmc3", dd + " -DFV_HELP -DFV_HELPONLY", D, True)
        for m in ("K", "FREERUN", "NO_GUARD", "NO_TAG"):
            full[f"mut{m}_{b}"] = ("bmc", 1200, "abc bmc3", dd + f" -DOT_MESO_CA_MUTANT_{m}", D, False)
write("fv_ca2_full.sby", full)
for D, rr, offs in ((4, 12, range(-3, 12)), (8, 20, range(-3, 20))):
    k = {f"s{D}_P{p}_O{o}".replace("-", "m"): ("bmc", 1, "abc bmc3", f"-DFV_HELP -DFV_ONE -DFV_NOLIVE -DFV_D={D} -DFV_RRM={rr} "
                                                 f"-DFV_PH={p} -DFV_OFF={o}", D, True) for p in range(8) for o in offs}
    write(f"fv_ca2_k{D}.sby", k)
mut = {}
for m, D, p, o, rr in (("K", 4, 3, 0, 12), ("K", 8, 3, 3, 20), ("FREERUN", 4, 3, 0, 12), ("FREERUN", 8, 3, 3, 20),
                       ("NO_GUARD", 4, 2, -1, 12), ("NO_GUARD", 8, 2, -1, 20), ("NO_TAG", 4, 3, 9, 12), ("NO_TAG", 8, 3, 17, 20)):
    mut[f"m{m}_D{D}_P{p}_O{o}".replace("-", "m")] = ("bmc", 1, "abc bmc3", f"-DOT_MESO_CA_MUTANT_{m} -DFV_HELP -DFV_ONE -DFV_NOLIVE "
                                                     f"-DFV_D={D} -DFV_RRM={rr} -DFV_PH={p} -DFV_OFF={o}", D, True)
write("fv_ca2_mut.sby", mut)
