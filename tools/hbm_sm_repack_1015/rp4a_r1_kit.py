#!/usr/bin/env python3
"""HBM-SMATT10 (10-20; RELEASE_TREE H.STA.BLK.9.1 + H.STA.BLK.14.6): rp4a attention-tile halves RE-PLANNED on the CLOSED
x store smh_xs_p192d_bay (f61a12bcc, 475.2 x 388.8, TT +18.63 / FF +12.47; record merged to main 2ed3c3170).  Replaces
the diagnostic stand-in kits of rp4a_kit.py (smh_rp4ah{n,s}_w{562,605}_standin), whose gates FAILED:
  clock_rule  pin-flop spread TT 132.4 / FF 130.1 ps (K=32 k-means roots over a 561.6 x 1425.6 half)
  trial_route GRT rc 137 (killed at 96 GB)
  macro->macro rl1 -187.7 ps (row_w 'first' -> x-store W-face rl1: one cycle of 300-560 um)
  reg->macro   ohl1 -360.6 ps (bk1[2060:2048] landing -> x-store W face)
  reg->reg     u_xb1 -312.6 ps (n bin -> S crossing relays unplaced: hops up to ~700 um)
Structural changes (one failed gate = re-plan, not a squeeze):
  * FRAME 691.2 wide (dx 129.6): a 172.8-um W channel for the rl1 relay stations, the beat-crossing relay column and
    the ohl1 copy; x store MX at (172.8, 734.4), E channel 43.2.  n 1,512 / s 1,209.6 tall (x store +86.4 vs stand-in).
  * LR = 2 leaf-input relay stages (RTL ot_rp4a_leaf #(LR), uniform: rl1 / bk1 / st / at / reset all +2, own 13-bit ohl1
    copy, gin padded +2 in n -> every gout lane +2, PRICED): rl1 FIRM stations (110, 600) / (130, 900) -> hops <= ~330 um.
  * XB = 2 and FIRM stations for every n beat-crossing stage down the W channel (y 1250 / 990 / 730 / 470, out stage at
    (150, 150) under the free SW corner): hops <= ~390 um.  PV merge moved E (x 302.4) to free that corner.
  * rows R0 (row_w 'first' faces N toward the x store; MX pointed it away), row_e R0.
  * GRT memory 192 GB.
  * two clock variants gated in parallel: r1a = one TritonCTS root (no k-means split), r1b = k-means K=8 regional roots.
r2 (FAM-HBM-C/C-SMH 10-21, s half only; `rp4a_r1_kit.py r2`): the r1 s gates @ebacd091f reached GRT with 1,866 (r1a) /
14 (r1b) overflow, ALL horizontal in the top gcell rows y 1205-1210, x 250-420.  Cause: the n->s crossing xi_b (2,069 b) enters
the N face at x 4.3-410.4 (crossing range shared with the n half's S face) but the x store bk1 pins sit at x 216.1-613.2 (bay
MX at x 172.8), and io_flop_at_pins stacked the 2,069 u_lands flops against the N edge, so the ~206-um jog of ~1,050 bits per
cut ran in the top rows.  Fix (structural, no squeeze): s frame +43.2 tall (top channel 86.4 -> 129.6) and u_lands FIRM in
a band directly above bk1 (centre x 414.7, y 1150 +-14), so the jog uses the whole channel above it (pin -> flop wire
<= ~300 um < 405, flop -> bk1 short vertical).  No RTL / cycle change.
x-store / block-dot MX as before (track-legal per the L2H-SM9 / L2H-SMATT orientation notes; tct R0 only).
    python3 tools/hbm_sm_repack_1015/rp4a_r1_kit.py
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import rp4h_kit as H  # noqa: E402
import rp4a_kit as A  # noqa: E402

ROOT = H.ROOT
W = 691.2
DX = 129.6
XSH = 388.8                          # closed XS bay height (stand-in 302.4)
HN, HS = 1512.0, 1209.6              # stand-in 1425.6 / 1123.2 + 86.4
LR, XB, GN, GS, OS = 2, 2, 2, 1, 1
V = dict(A.V)
V["xs"] = "physical/ref_tile/smh_xs_p192d_bay/views/ot_hbm_accel_smh_xs"
VARIANTS = {"r1a": 0, "r1b": 8}      # k-means clock regions (0 = single TritonCTS root)
R2 = {"r2a": 0, "r2b": 8}            # s half only (see header): HS 1252.8 + FIRM u_lands band above bk1
HS_R2 = HS + 43.2
LANDS = "st_box lands {u_lands.} 414.7 1150 196 14 2069\n"
WIT = "results/arch/hbm_smatt10_1020/bench"
CORE = "g_lr.u_c"


def leaf(j):
    p = f"u_lf{j}.{CORE}"
    return [("pvm", f"{p}.u_merge", 302.4, 43.2, "R0"),
            ("tct", f"{p}.u_qk", 216.0 + DX, 388.8, "R0"),
            ("bdc", f"{p}.u_bdc", 43.2 + DX, 518.4, "MX"),
            ("tcl", f"{p}.u_h0", 216.0 + DX, 518.4, "R0"),
            ("tcl", f"{p}.u_h1", 345.6 + DX, 518.4, "R0"),
            ("xs", f"{p}.u_xs", 43.2 + DX, 734.4, "MX")]


def kids(half):
    j = 0 if half == "n" else 1
    return leaf(j) + [("roww", f"u_row{j}", 86.4 + DX, 388.8, "R0"), ("rowe", f"u_rowe{j}", 475.2 + DX, 388.8, "R0")]


BOX = '''proc sr_place_box {group cx cy hw hh} {
  set cx [expr {round($cx*$::sr_dbu)}]; set cy [expr {round($cy*$::sr_dbu)}]; set hw [expr {round($hw*$::sr_dbu)}]; set hh [expr {round($hh*$::sr_dbu)}]; set rows {}
  foreach r $::sr_rows {lassign $r ox oy xe ori; if {abs($oy-$cy) <= $hh} {lappend rows [linsert $r 0 [expr {abs($oy-$cy)}]]}}
  set rows [lsort -integer -index 0 $rows]
  foreach i [$group getInsts] {
    set w [[$i getMaster] getWidth]; set h [[$i getMaster] getHeight]; set w [expr {max($w,$::sr_mw_dff)+4*$::sr_sw}]; set found 0
    foreach r $rows {lassign $r delta ox oy xe ori
      set x [expr {$ox+int(ceil(double(max($ox,$cx-$hw)-$ox)/$::sr_sw))*$::sr_sw}]
      while {$x+$w <= min($xe,$cx+$hw)} {
        set jump $x; for {set k [expr {int(floor(double($oy)/$::sr_rh))}]} {$k <= int(floor(double($oy+$h-1)/$::sr_rh))} {incr k} {
          if {![dict exists $::sr_used $k]} continue; foreach iv [dict get $::sr_used $k] {lassign $iv a b; if {$x+$w > $a && $x < $b} {set jump [expr {max($jump,$ox+int(ceil(double($b-$ox)/$::sr_sw))*$::sr_sw)}]}}
        }
        if {$jump > $x} {set x $jump; continue}
        $i setOrient $ori; $i setLocation [expr {$x+2*$::sr_sw}] $oy; $i setPlacementStatus FIRM; incr ::sr_fixed; sr_occupy $x $oy [expr {$x+$w}] [expr {$oy+$h}]; set found 1; break
      }; if {$found} break
    }; if {!$found} {error "STRAP_REGION no legal station site for [$i getName]"}
  }
}
proc st_box {name pats cx cy hw hh expect} {
  set gr [odb::dbGroup_create $::sr_blk $name]; set n 0
  foreach i [$::sr_blk getInsts] {
    set nm [string map {\\\\ {}} [$i getName]]
    foreach p $pats { if {[string first $p $nm] == 0 && [string match *DFF* [[$i getMaster] getName]]} { $gr addInst $i; incr n; break } }
  }
  if {$n == 0} {puts "RP4_STATION WARNING $name: no DFFs matched ($pats)"; odb::dbGroup_destroy $gr; return} elseif {$n != $expect} {puts "RP4_STATION WARNING $name: expected $expect DFFs, got $n"}
  sr_place_box $gr $cx $cy $hw $hh
  odb::dbGroup_destroy $gr
  puts "RP4_STATION $name $n flops at ($cx, $cy) box +-$hw x +-$hh"
}
'''


def stations(name, half, h):
    src = (H.SPECS / "smh_tile_rp4lp_stations.tcl").read_text()
    head = src[:src.index("st_group gl0_mid")]
    body = head[head.index("set ::sr_blk"):]
    j = 0 if half == "n" else 1
    lf = f"u_lf{j}.g_lr"
    hdr = (f"# HBM-SMATT10 {name}: generated by tools/hbm_sm_repack_1015/rp4a_r1_kit.py (procs from smh_tile_rp4lp_stations.tcl\n"
           "# + sr_place_box / st_box: the same legal-row search in a +-hw x +-hh box for the 818 / 2,069-bit stages).\n"
           "# FIRM: leaf rl1 relays (LR 2) and the ohl1 copy in the W channel, n beat-crossing relays (XB 2) down the W\n"
           "# channel, gather relays as rp4a_kit (shifted by dx 129.6).\n")
    g = (f"st_box rl0 {{{lf}.u_rl.g_s[0].}} 110 600 60 10 818\n"
         f"st_box rl1 {{{lf}.u_rl.g_s[1].}} 130 900 40 14 818\n"
         f"st_box oh1 {{{lf}.u_oh.g_s[1].}} 140 770 20 4 13\n")
    if half == "n":
        y3 = round(h * 0.75, 1)
        g += (f"st_box xb1 {{u_xb1.}} 80 1250 70 10 2069\n"
              f"st_box xb2 {{g_xb2.u_xb2. u_xb2.}} 80 990 70 10 2069\n"
              f"st_box xb3a {{g_xb3.u_xb3.g_s[0].}} 80 730 70 10 2069\n"
              f"st_box xb3b {{g_xb3.u_xb3.g_s[1].}} 80 470 70 10 2069\n"
              f"st_box xbo {{u_xbo.}} 150 150 90 8 2069\n"
              f"st_group gl0_mid {{u_gn.g_gl[0].u_v2/ u_gn.g_gl[0].u_d2/ u_gn.g_gl\\[0\\].u_v2/ u_gn.g_gl\\[0\\].u_d2/}} {300 + DX} {y3} 50\n"
              f"st_group gl1_mid {{u_gn.g_gl[1].u_v2/ u_gn.g_gl[1].u_d2/ u_gn.g_gl\\[1\\].u_v2/ u_gn.g_gl\\[1\\].u_d2/}} {330 + DX} {y3} 50\n"
              f"st_group xpr0 {{u_xpr.g_s[0]. u_xpr.g_s\\[0\\].}} {490 + DX} 712.8 100\n"
              f"st_group xgr0 {{u_xgr.g_s[0]. u_xgr.g_s\\[0\\].}} {530 + DX} 712.8 50\n"
              f"st_group xpr1 {{u_xpr.g_s[1]. u_xpr.g_s\\[1\\].}} {490 + DX} 367.2 100\n"
              f"st_group xgr1 {{u_xgr.g_s[1]. u_xgr.g_s\\[1\\].}} {530 + DX} 367.2 50\n")
    else:
        if h > HS:
            g += LANDS
        g += (f"st_group xg2_mid {{u_xg2.}} {530 + DX} 748.8 50\n"
              f"st_group xp2_mid {{u_xp2.}} {530 + DX} 800.0 100\n"
              f"st_group xg3 {{u_xg3.g_s[0]. u_xg3.g_s\\[0\\].}} {500 + DX} 367.2 50\n"
              f"st_group xp3 {{u_xp3.g_s[0]. u_xp3.g_s\\[0\\].}} {530 + DX} 367.2 100\n")
    return hdr + body + BOX + g + 'puts "RP4_STATION fixed $::sr_fixed"\n'


def pins(half, h):
    p, rng = A.pins(half, h)
    if half == "n":
        rng["bin"] = [1127.52, 1506.96]
        rng["bout"] = [1127.52, 1506.96]
    return p, rng


def benches():
    one = A.BENCH_ONE
    a = f"1 13 {GN} {GS} {XB} {LR} {OS}"
    out = [{"name": "h2a_lockstep_r1", "cmd": f"bash {one} {{RUN}}/h2a 0 {a}", "expect": "pass",
            "pass_regex": "^H2A_LOCKSTEP PASS MUT=0 compared=", "pass_witness": f"{WIT}/mut0.log", "threads": 4,
            "peak_ram_gb": 24}]
    for m in (1, 2, 3, 5, 6):
        out.append({"name": f"h2a_r1_mut{m}", "cmd": f"bash {one} {{RUN}}/h2am{m} {m} {a}", "expect": "fail",
                    "fail_regex": f"^H2A_LOCKSTEP FAIL MUT={m} mismatches=[1-9]", "fail_witness": f"{WIT}/mut{m}.log",
                    "threads": 4, "peak_ram_gb": 24})
    return out


def spec(name, half, K, base, h=None):
    h = h or (HN if half == "n" else HS)
    k = dict(half=half, w=W, h=h, dx=DX, kids=kids(half))
    s = A.spec(name, k, base)
    s.pop("diagnostic", None)
    s.pop("standins", None)
    s["params"] = {"SOFTBEAT": 1, "GN": GN, "XB": XB, "LR": LR, "OS": OS} if half == "n" else {"GN": GN, "GS": GS, "XB": XB, "LR": LR, "OS": OS}
    s["children"] = [{"view": V[v], "count": 1, "at": [x, y], "orient": o, "inst": i} for v, i, x, y, o in k["kids"]]
    s["pins"], s["pin_ranges"] = pins(half, h)
    st = f"physical/ref_tile_specs/smh/{name}_stations.tcl"
    (ROOT / st).write_text(stations(name, half, h))
    s["orfs_vars"] = {"OT_IO_REF_CLASS": "1", "POST_TAPCELL_TCL": st}
    if K:
        s["orfs_vars"].update({"OT_CKKM_K": str(K), "OT_CKKM_PORT": "clk"})
        s["pre_cts_extra"] = ["physical/common_flow/clock_split_km.tcl"]
    else:
        s.pop("pre_cts_extra", None)
    s["route"] = dict(s["route"], peak_ram_gb=192)
    s["job"].update({
        "owner": "Claude DRIVE-HBM/HBM-SMATT10", "branch": "claude/hbm-smatt10-1020", "tag": name.replace("smh_", ""),
        "purpose": (f"H.STA.BLK.9.1 / 14.6: HBM SM attention tile rp4a ({half} half, frame {W} x {h}) on the CLOSED XS "
                    f"bay view (smh_xs_p192d_bay f61a12bcc); clock variant {'K=%d k-means roots' % K if K else 'one TritonCTS root'}."),
        "structural_change": (
            "re-plan of the stand-in rp4a halves after their gate FAIL (spread 132/130, GRT rc137, rl1 -188, ohl1 -361, "
            "xb1 -313): frame 691.2 wide with a 172.8 W channel; LR=2 uniform leaf-input relays (rl1 hops <= ~330 um, own "
            "ohl1 copy), XB=2 beat-crossing relays FIRM down the W channel (<= ~390 um), PV merge moved E, rows R0, GRT 192 GB; "
            "core OS stages for the native census (kept per-slice copies); gout +LR+2 uniform (priced)."),
        "extra_paths": ["tools/hbm_sm_repack_1015", "rtl/hbm_accel/sm/repack/h2", "rtl/hbm_accel/sm/repack/h2a", WIT,
                        "physical/ref_tile/smh_xs_p192d_bay/views"],
        "benches": benches()})
    return s


README = """# {name}

HBM-SMATT10 10-20 (DRIVE-HBM; RELEASE_TREE H.STA.BLK.9.1 + H.STA.BLK.14.6). {half} half of the HBM SM attention tile rp4a
(`ot_hbm_smh_rp4ah_{half}` #(LR 2, XB 2), rtl/hbm_accel/sm/repack/h2a/ot_hbm_smh_rp4ah.sv) in a {w} x {h} um frame half
(aspect {asp:.2f}), on the CLOSED x store smh_xs_p192d_bay (f61a12bcc).  Clock: {clk}.
Generated by `python3 tools/hbm_sm_repack_1015/rp4a_r1_kit.py` (see its header for the stand-in gate failures it answers).

## Children (all CLOSED views)
| inst | view | at / orient |
|---|---|---|
{kids}

## SAFE-DESIGN checklist (owner 10-19; 10-20 rule freeze: guidance, route timing decides)
1 Pins: PASS - every data pin registered in RTL (rin pinrow, bin pinbeat, straps, gin u_v/u_d, crossing in/out, gout u_gs);
  rst_n lands in 2 kept face stages + kept copies per consumer (ot_rp4h_rst); the leaf reset is delayed LR with its inputs.
2 Reach: FIXED - rl1 = row_w first -> LR 2 FIRM stations (110,600)/(130,900) -> x-store W face: hops <= ~330 um; ohl1 own
  kept copy stationed at the x-store W face; n beat crossing XB 2: FIRM stations y 1250/990/730/470 + out (150,150), hops
  <= ~390 um; gather lanes GN 2 / GS 1 FIRM stations as rp4a (+dx).
3 Fanout: FIXED after the r1 census FAIL (input_pv 257, attn_column 130/65/49, r_x 253, bdc ov 98, merge pub_v 89): core OS 1 =
  registered x-store outputs with 8 kept per-slice input_pv copies + 16 kept one-hot attn_column copies, child outputs
  registered before the g select (3 kept copies per valid), publication line reset from 16 kept copies (g +2 uniform).
  r1 census #2 FAIL (input_pv per slice 64 = 32 bits x 2 mux pins; k_b[1]/k_p[1] 64 on the 32-bit gy mux): HBM-SMATT11
  24 kept input_pv copies (<= 11 fx bits each, x pin 25 loads) and 4 + 2 kept gy / gt select copies per valid (8 bits
  each); cycle-neutral (same registered values), no schedule change.
4 Depth: PASS - relays are plain kept registers; no new combinational logic.
5 Storage: unchanged (publication delay 49x5 b + PV tag line 16x16 b < 2 kb flops; LR relays are 2-deep pipeline stages).
6 Floorplan: every hard child on the 43.2 lattice (xs/bdc MX, others R0); >= 43.2 channels at every pin face; W channel
  172.8 (relay columns), E channel 43.2; aspect {asp:.2f} ({aspnote}).
7 Clock: {clk}; clk on the W face at half height; hard children on TritonCTS macro trees; io_hold_margin 0.03; gate
  checks pin-flop spread <= 80 TT+FF.
8 Schedule: static; PRICED: gout +{gl} edges uniform vs the rp4h/lp record (GN+GS {gs} + LR {lr} + core OS 2); bin/rout/bout unchanged.
  Front per-hop result deskew + {gl} (compiler / die schedule owner).

## Bench (Verilator 5.050 via ot-run; witnesses {wit})
`rtl/hbm_accel/sm/repack/h2a/run_rp4ah2_one.sh OUT MUT 1 13 {gn} 1 {xb} {lr} 1`: lockstep flat (LR 0, OS 0) vs the two halves,
gout compared at +(2+GN+GS+LR+2*OS); MUT 1/2/3/5 as rp4a, MUT 6 = rl1 one relay short -> each must FAIL.
"""


def write_readme(name, half, K, s):
    rows = [f"| {c['inst']} | `{c['view']}` | {c['orient']} @ {c['at']} |" for c in s["children"]]
    h = s["outline"]["h"]
    asp = h / W
    note = "<= 2:1 PASS" if asp <= 2.0 + 1e-6 else "over 2:1 guidance: leaf stack forced by closed pin faces; frame-level die result decides"
    clk = f"k-means K={K} regional roots (clock_split_km.tcl)" if K else "one TritonCTS root (no k-means split)"
    (ROOT / "physical/ref_tile" / name / "README.md").write_text(README.format(
        name=name, half=half, w=W, h=h, asp=asp, kids="\n".join(rows), aspnote=note, clk=clk, gl=GN + GS + LR + 2 * OS,
        gs=GN + GS, lr=LR, gn=GN, xb=XB, wit=WIT))


def main():
    base = json.loads(H.BASE.read_text())
    r2 = sys.argv[1:] == ["r2"]
    for var, K in (R2 if r2 else VARIANTS).items():
        for half in (("s",) if r2 else ("n", "s")):
            name = f"smh_rp4ah{half}_{var}"
            s = spec(name, half, K, base, HS_R2 if r2 else None)
            if r2:
                s["job"]["owner"] = "Claude FAM-HBM-C/C-SMH"
                s["job"]["structural_change"] += (" r2: s frame +43.2 (top channel 129.6) and u_lands FIRM above the x-store bk1 "
                                                  "pins (r1 GRT overflow 1866/14 in the top rows from the 206-um xi_b->bk1 jog).")
            kd = ROOT / "physical/ref_tile" / name
            kd.mkdir(parents=True, exist_ok=True)
            (kd / "spec.json").write_text(json.dumps(s, indent=1) + "\n")
            write_readme(name, half, K, s)
            print(f"{kd / 'spec.json'}: {len(s['children'])} children, outline {W} x {s['outline']['h']}")


if __name__ == "__main__":
    main()
