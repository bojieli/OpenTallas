"""ADV-PHANTOM-STATION: fixture = the real HEAD positive (FABLE-FIX-HEAD-LEP0N 11-22 19:07 RETRACT).  r18m
(3dd49f406010) = r18j + LEP-H2R-STN-1: hd_lep0N.internal_stations {conn bus:o_h2r1_p, launch u_core.h2r1, from_um
[344,605], to_um [0,795.312], regs_um [[200,720]], bits 574} and lane L2 fixed_cycles 1, latency {cycles 3, boundary 2,
fixed 1, natural 3}.  hd_lep0N (module ot_s81hd_lep0N) has no realize_internal_stations, so the gen wrapper keeps only
the face register u_bout_o_h2r1_p (real line copied, bind_r18m/gen) and the kit inserts nothing: 2 registers vs 3 planned.
The baseline (r18j) has neither the row nor the +1.  Reduced to the one lane L2 (lep0N -> lep0N_w)."""
import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import adv_phantom_station as A  # noqa: E402

# lane_asbuilt_latency lives beside the module in tools/die_plan; in the PRECHECK-R2 work dir use the lane clone's
REPO = None if (HERE / "lane_asbuilt_latency.py").is_file() else HERE.parent.parent / "repo"

SRC_RTL = """module ot_s81hd_lep0N (
    input  wire clk,
    input  wire rst_n,
    output wire [574:0] o_h2r1_p  // 574 data + epoch [574]
);
    wire [573:0] o_h2r1_p_d;
    wire rst_n_t137 = rst_n;
    ot_dp_ste #(.W(574)) u_bout_o_h2r1_p (.clk(clk), .rst_n(rst_n_t137), .d(o_h2r1_p_d), .ea(rst_n_t137), .q(o_h2r1_p[573:0]), .eq(o_h2r1_p[574]));
    ot_s81hd_lep_core u_core (.clk(clk), .h2r1(o_h2r1_p_d));
endmodule
"""
DST_RTL = """module hd_lep0N_w_part (
    input  wire clk,
    input  wire rst_n,
    input  wire [574:0] i_h2r1_p
);
    wire [573:0] i_h2r1_p_q;
    wire i_h2r1_p_eq;
    ot_dp_st #(.W(574)) u_bin_i_h2r1_p (.clk(clk), .rst_n(rst_n), .d(i_h2r1_p[573:0]), .ea(i_h2r1_p[574]), .q(i_h2r1_p_q), .eq(i_h2r1_p_eq));
endmodule
"""
ROW = {"conn": "bus:o_h2r1_p", "from_um": [344.0, 605.0], "to_um": [0.0, 795.312], "regs_um": [[200.0, 720.0]],
       "bits": 574, "launch": "u_core.h2r1",
       "note": "LEP-H2R-STN-1 (FABLE-FIX-HEAD-LEP0N 11-22; cycles pre-approved): 1 FIRM station hub stamp logic -> W cut face"}


def base_plan():
    return {
        "die": {"name": "s81_head"},
        "partition_types": {
            "hd_lep0N": {"module": "ot_s81hd_lep0N", "outline_um": [1100.0, 1450.0], "internal_stations": [],
                         "buses": [{"name": "o_h2r1_p", "dir": "out", "width": 574, "face": "W"}]},
            "hd_lep0N_w": {"module": "hd_lep0N_w_part", "outline_um": [700.0, 1450.0], "internal_stations": [],
                           "buses": [{"name": "i_h2r1_p", "dir": "in", "width": 574, "face": "E"}]},
        },
        "partitions": [{"name": "lep0N", "type": "hd_lep0N", "origin_um": [700.0, 0.0]},
                       {"name": "lep0N_w", "type": "hd_lep0N_w", "origin_um": [0.0, 0.0]}],
        "ports": [{"id": "L2_0", "src": {"part": "lep0N", "bus": "o_h2r1_p"},
                   "dst": {"part": "lep0N_w", "bus": "i_h2r1_p"}}],
        "lanes": [{"id": "L2", "ports": ["L2_0"],
                   "note": "head_lep0N_we_split_r8e1b: cut route type net h2r1 piece 1 -> 0"}],
        "latency": {"lanes": {"L2": {"cycles": 2, "stations": 0, "boundary": 2, "faces": 1, "fixed": 0, "natural": 2,
                                     "pad": 0, "param": "LAT_L2"}}},
    }


def r18m_plan():
    p = base_plan()
    p["partition_types"]["hd_lep0N"]["internal_stations"].append(copy.deepcopy(ROW))
    p["lanes"][0]["fixed_cycles"] = 1
    p["latency"]["lanes"]["L2"].update(cycles=3, fixed=1, natural=3)
    return p


def gen_dir(tmp_path, src=SRC_RTL):
    g = tmp_path / "bind_r18m" / "gen"
    g.mkdir(parents=True)
    (g / "ot_s81hd_lep0N.sv").write_text(src)
    (g / "hd_lep0N_w_part.sv").write_text(DST_RTL)
    (g / "gen_clock_landings.json").write_text(json.dumps({"lane_added_cycles": {}}))
    return g


def run(tmp_path, plan, base, bind_out):
    pp = tmp_path / "plan" / "source_plan.json"
    pp.parent.mkdir(exist_ok=True)
    pp.write_text(json.dumps(plan))
    return A.findings(plan, str(pp), str(REPO) if REPO else None, baseline=base, bind_out=str(bind_out))


def flagged(lines):
    return [x for x in lines if x.startswith("WARN ADV-PHANTOM-STATION lane ")]


def test_positive_r18m_h2r1_row_flagged(tmp_path):
    out = run(tmp_path, r18m_plan(), base_plan(), gen_dir(tmp_path).parent)
    f = flagged(out)
    assert len(f) == 1, out
    assert "lane L2:" in f[0] and "plan 3 cycles" in f[0] and "vs 2 register stage(s)" in f[0]
    assert "1 phantom cycle(s)" in f[0] and "hd_lep0N.internal_stations bus:o_h2r1_p 1 reg(s)" in f[0]
    assert "realize_internal_stations" in f[0]
    assert out[-1].startswith("WARN ADV-PHANTOM-STATION summary: 1 lane(s) flagged")


def test_fixed_rows_stripped_not_flagged(tmp_path):
    out = run(tmp_path, base_plan(), base_plan(), gen_dir(tmp_path).parent)
    assert not flagged(out), out


def test_realized_station_not_flagged(tmp_path):
    """the same row on a gen type with realize_internal_stations: gen_rtl emits u_ist_o_h2r1_p_0 -> 3 registers"""
    p = r18m_plan()
    p["partition_types"]["hd_lep0N"]["realize_internal_stations"] = True
    src = SRC_RTL.replace(".d(o_h2r1_p_d), .ea(rst_n_t137)", ".d(o_h2r1_p_is0_q), .ea(o_h2r1_p_is0_eq)").replace(
        "endmodule", "    wire [573:0] o_h2r1_p_is0_q;\n    wire o_h2r1_p_is0_eq;\n"
        "    ot_dp_st #(.W(574)) u_ist_o_h2r1_p_0 (.clk(clk), .rst_n(rst_n), .d(o_h2r1_p_d), .ea(rst_n_t137), "
        ".q(o_h2r1_p_is0_q), .eq(o_h2r1_p_is0_eq));  // kit_istations: FIRM plan station\nendmodule")
    out = run(tmp_path, p, base_plan(), gen_dir(tmp_path, src).parent)
    assert not flagged(out), out


def test_no_baseline_in_core_claim_not_flagged(tmp_path):
    """without a baseline the s81_head fixed-in-core convention holds: shortfall 1 <= fixed_cycles 1 -> counted only"""
    out = run(tmp_path, r18m_plan(), None, gen_dir(tmp_path).parent)
    assert not flagged(out), out
    assert "1 with shortfall within fixed_cycles" in out[-1] and "1 carry station rows no gen kit realizes" in out[-1]


def test_no_bound_rtl_one_not_checked_line(tmp_path):
    (tmp_path / "empty").mkdir()
    out = run(tmp_path, r18m_plan(), base_plan(), tmp_path / "empty")
    assert len(out) == 1 and out[0].startswith("WARN ADV-PHANTOM-STATION not checked:"), out


def test_bound_same_plan_reads_bind_lane_asbuilt(tmp_path):
    """strict bind OUT of this very plan: the in-bind LATCHECK records are the count; delivered < table is flagged"""
    p = r18m_plan()
    b = tmp_path / "bind"
    (b / "rtl").mkdir(parents=True)
    (b / "bind_report.json").write_text("{}")
    pp = tmp_path / "plan" / "source_plan.json"
    pp.parent.mkdir()
    pp.write_text(json.dumps(p))
    (b / "provenance_bind.json").write_text(json.dumps({"provenance": {"plan": str(pp)}}))
    rec = dict(lane="L2", src="lep0N", dst="lep0N_w", table=3, delivered=2, verdict="FAIL",
               source=dict(face=1, pads=0, bound_ist=0, core_chain=0), receiver=dict(face=1, pads=0, lpad=0), ft=0,
               landing=0)
    (b / "bind_lane_asbuilt.json").write_text(json.dumps({"lanes": [rec]}))
    out = A.findings(p, str(pp), str(REPO) if REPO else None, bind_out=str(b))
    assert len(flagged(out)) == 1, out
    rec.update(delivered=3, verdict="PASS")
    (b / "bind_lane_asbuilt.json").write_text(json.dumps({"lanes": [rec]}))
    assert not flagged(A.findings(p, str(pp), str(REPO) if REPO else None, bind_out=str(b)))


def test_bound_other_plan_summary_only(tmp_path):
    p, base = r18m_plan(), base_plan()
    b = tmp_path / "bind"
    (b / "rtl").mkdir(parents=True)
    (b / "bind_report.json").write_text("{}")
    bp = tmp_path / "base.json"
    bp.write_text(json.dumps(base))
    (b / "provenance_bind.json").write_text(json.dumps({"provenance": {"plan": str(bp)}}))
    pp = tmp_path / "cand.json"
    pp.write_text(json.dumps(p))
    out = A.findings(p, str(pp), str(REPO) if REPO else None, bind_out=str(b))
    assert len(out) == 1 and "1 lane(s) changed" in out[0] and "cannot go phantom" in out[0], out
