"""Per-die configuration for the feedthrough tools (FT-PLAN, owner 10-23).

Every value here is a planning input with a named source; die agents may override any of them from the command line
(census.py / plan.py --reach-um, --rep-um, --big-min-um2, --ft-layers).

reach_um   one-cycle M8/M9 relay hop with margin (REACH-M89, claude/die-reach-m89-1022 @3fc75c0e3,
           results/arch/die_reach_m89_1022.json): S81 1.5 mm, KV 1.2, HBM 1.0-1.2 (1.0 used), Qwen 1.0.
rep_um     repeater spacing on the M7-M9 RC: <=450 um (600 breaks the 320-ps slew limit; claude/die-rep600-1022).
relay_re   die-level relay / landing / reset-repeater families (FT-PLAN "Relay families"); a matching master is a
           pipeline STAGE of a lane, everything else is an endpoint block.
"""
import re

FT_LAYERS = ("M8", "M9")          # reserved for die-level and feedthrough wires (target architecture item 1)
FT_RATIO_MAX = 0.6                # bits / tracks on a face (cut-analysis rule, owner 10-12)
REP_UM = 450.0
BIG_MIN_UM2 = 100_000.0           # a block >= 0.1 mm2 that is not a relay is a "big block" the census checks crossings of

DIES = {
    "s81": dict(
        label="S81 cap24 (DS ROM)", reach_um=1500.0,
        relay_re=r"^(dsfd_dvrlyh_|dsfd_rly_|dsfd_dvland)",
        land_re=r"dvland",
        dump="ot-epyc5:/srv/opentallas-scratch/claude/ft-tool/dump-s81",
        odb="ot-epyc5:/srv/opentallas-scratch/claude/coord-rep600-s81/case/out/post_repair.odb"),
    "kv": dict(
        label="Qwen KV sqc3s", reach_um=1200.0,
        merge_gap_um=30.0, merge_min_um2=1000.0,   # head / lane / PV arrays of small blocks are one obstacle
        relay_re=r"^(qkd_rlys|qkd_rlysh|qkd_rlyi_|qkd_astk_rly|qkd_landsh)",
        land_re=r"landsh",
        dump="ot-epyc5:/srv/opentallas-scratch/claude/ft-tool/dump-kv",
        odb="ot-epyc5:/srv/opentallas-scratch/claude/sqc-kdie5/repprobe/f9b69ebb3-sqc3s/def/floorplan_pdn.odb"),
    "qc": dict(
        label="Qwen compute r50", reach_um=1000.0,
        relay_re=r"^(qfd_rlyh|qfd_rlyr|qfd_landh|qfd_rst_rep)",
        land_re=r"landh",
        dump="ot-gold1:/srv/opentallas-scratch/claude/ft-tool/dump-qc",
        odb="ot-gold1:/srv/opentallas-scratch/claude/codex-qdie-2000/dv2f21g5r50cxc/chain/case_r22k/floorplan.odb"),
    "hbm": dict(
        label="HBM r18h5", reach_um=1000.0,
        relay_re=r"^hbfd_(rly|lh|lh0|land|land0)_",
        land_re=r"^hbfd_(lh|lh0|land|land0)_",
        dump="ot-epyc5:/srv/opentallas-scratch/claude/ft-tool/dump-hbm",
        odb="ot-epyc5:/srv/opentallas-scratch/claude/codex-hbmc-r18h5-2140-1022/chainsM/probe600/out/place.odb"),
}

RESET_BUS_RE = re.compile(r"^(rs|rst|rst_n|rstn|reset|reset_n|rs_o|rst_o)$", re.I)
CLOCK_BUS_RE = re.compile(r"^(ck|clk|ck_o|clk_o|ck_i|fck|fclk)(_.*)?$", re.I)


def get(die, **over):
    cfg = dict(DIES[die]) if die in DIES else dict(label=die, reach_um=1000.0, relay_re=r"(rly|relay|land)",
                                                     land_re=r"land", dump=None, odb=None)
    cfg.setdefault("rep_um", REP_UM)
    cfg.setdefault("big_min_um2", BIG_MIN_UM2)
    cfg.setdefault("ft_layers", FT_LAYERS)
    cfg.setdefault("ft_ratio_max", FT_RATIO_MAX)
    for k, v in over.items():
        if v is not None:
            cfg[k] = v
    cfg["name"] = die
    return cfg
