#!/usr/bin/env python3
"""Prepare KV45 native C2 interfaces in a private copy of the reconstructed source tree.

Preserves the measured C2 FIFO/join/pacer architecture. No post-bind RTL edits.
The final schedule and wavefront binder are separate inputs; this is not a gate.
"""
import gzip
import copy
import json
import re
import subprocess
import sys
from pathlib import Path

tree = Path(sys.argv[1]).resolve()
base = tree / "physical/die_plan/qwen_kvsys/bind"
out = base / "kv45"
out.mkdir(parents=True, exist_ok=True)


def once(text, old, new):
    if text.count(old) != 1:
        raise ValueError(f"expected exactly one {old!r}, got {text.count(old)}")
    return text.replace(old, new)


host = (tree / "rtl/qwen_sys/kv_host_obs_20261019/qkd_host_root_admission_obsx_bo1.sv").read_text()
host = once(host, "module qkd_host_root_admission_obsx_bo1 #(",
            "module qkd_host_root_admission_obsx_bo1_c45 #(")
host = once(host, " input wire phy_rx_v,", " input wire phy_rx_v_w,\n input wire phy_rx_v_e,")
host = host.replace(".phy_rx_v(phy_rx_v)", ".phy_rx_v(kv45_join_v)")
host = host.replace(".phy_rx_flit(phy_rx_flit)", ".phy_rx_flit(kv45_join_d)")
host = host.replace(".phy_up(phy_up)", ".phy_up(kv45_paced_up)")
insert = """
 // Native C2: same order-join and 19/24 pacing as the measured staged vehicle.
 wire kv45_join_v, kv45_slot, kv45_paced_up;
 wire [1042:0] kv45_join_d;
 ot_fdi_join2 #(.WA(522), .WB(521), .DEPTH(16)) u_fdi_join (
   .clk(ck_pad), .rst_n(link_rst_n),
   .a_v(phy_rx_v_w), .a_d(phy_rx_flit[521:0]),
   .b_v(phy_rx_v_e), .b_d(phy_rx_flit[1042:522]),
   .o_v(kv45_join_v), .o_d(kv45_join_d));
 ot_fdi_tx_pace #(.NUM(19), .DEN(24)) u_fdi_pace (
   .clk(ck_pad), .rst_n(link_rst_n), .slot(kv45_slot));
 assign kv45_paced_up = phy_up & kv45_slot;
"""
host = once(host, "generate if(MU==0)begin:g_plain", insert + "\ngenerate if(MU==0)begin:g_plain")
(out / "qkd_host_root_admission_obsx_bo1_c45.sv").write_text(host)

phy = """`timescale 1ns/1ps
`default_nettype none
// Native C2: exactly one Gray-pointer FIFO crossing per direction at each PHY half.
module ot_qfd_serdes_112g_x6_phy_c45 #(parameter W=522) (
 input wire clk, clk_phy, rst_n, tx_v,
 input wire [W-1:0] tx_flit,
 output wire tx_up, rx_v,
 output wire [W-1:0] rx_flit
);
 wire p_rst_n, p_tx_v, p_rx_v, p_tx_up;
 wire [W-1:0] p_tx_d, p_rx_d;
 ot_fdi_phy_cdc #(.W(W), .DEPTH(8)) u_fdi_cdc (
  .clk(clk), .link_rst_n(rst_n), .c_tx_v(tx_v), .c_tx_d(tx_flit),
  .c_rx_v(rx_v), .c_rx_d(rx_flit), .c_tx_up(tx_up), .clk_phy(clk_phy),
  .p_rst_n(p_rst_n), .p_tx_v(p_tx_v), .p_tx_d(p_tx_d),
  .p_rx_v(p_rx_v), .p_rx_d(p_rx_d), .p_tx_up(p_tx_up));
 ot_qfd_serdes_112g_x6_phy #(.W(W)) u_phy (
  .clk(clk_phy), .rst_n(p_rst_n), .tx_v(p_tx_v), .tx_flit(p_tx_d),
  .tx_up(p_tx_up), .rx_v(p_rx_v), .rx_flit(p_rx_d));
endmodule
module ot_qfd_serdes_112g_x12_phy_s2_c45 (
 input wire clk, clk_phy, rst_n, tx_v,
 input wire [1042:0] tx_flit,
 output wire tx_up, rx_v_w, rx_v_e,
 output wire [1042:0] rx_flit
);
 wire up_w, up_e;
 ot_qfd_serdes_112g_x6_phy_c45 #(.W(522)) u_W (
  .clk(clk), .clk_phy(clk_phy), .rst_n(rst_n), .tx_v(tx_v), .tx_flit(tx_flit[521:0]),
  .tx_up(up_w), .rx_v(rx_v_w), .rx_flit(rx_flit[521:0]));
 ot_qfd_serdes_112g_x6_phy_c45 #(.W(521)) u_E (
  .clk(clk), .clk_phy(clk_phy), .rst_n(rst_n), .tx_v(tx_v), .tx_flit(tx_flit[1042:522]),
  .tx_up(up_e), .rx_v(rx_v_e), .rx_flit(rx_flit[1042:522]));
 assign tx_up = up_w & up_e;
endmodule
module ot_qfd_serdes_112g_x12_phy_c45 (
 input wire clk, clk_phy, rst_n, tx_v,
 input wire [1042:0] tx_flit,
 output wire tx_up, rx_v_w, rx_v_e,
 output wire [1042:0] rx_flit
);
 ot_qfd_serdes_112g_x12_phy_s2_c45 u_sub (.*);
endmodule
// The reconstructed PHY-to-host data path has four core relay stages. Carry
// each half-valid through exactly the same age before the planner replaces it.
module qkd_rlys_kv45_valid4 (input wire ck, input wire [1:0] a, output wire [1:0] b);
 reg [1:0] q0, q1, q2, q3;
 always @(posedge ck) begin q0<=a; q1<=q0; q2<=q1; q3<=q2; end
 assign b=q3;
endmodule
`default_nettype wire
"""
(out / "serdes_c45.sv").write_text(phy)

# r2c was a mapped fanout-copy of this r2 wrapper (plan_leaf_variants.py).
# Reconstruct its intended RTL rather than keep old phase/calendar logic baked
# into gate primitives. Keep all four-hop relays and the uniform 29-edge fan age.
wrap = (tree / "rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_grp_r2.sv").read_text()
wrap = once(wrap, "module qkd_kvs_grp_r2 (", "module qkd_kvs_grp_r2c (")
wrap = once(wrap, "module qkd_kvs_grp_h_r2 (", "module qkd_kvs_grp_h_r2c (")
(out / "group_r2c_native.sv").write_text(wrap)
for tile in (tree / "rtl/qwen_sys/static_kv_die_20261017").glob("qkd_kvs_tiles*.sv"):
    text = tile.read_text()
    text = re.sub(r"(qkd_kv_landing_cal|qkd_static_kv_phase_launch) #\((?!\.SAME_CLOCK)",
                  r"\1 #(.SAME_CLOCK(1), ", text)
    text = re.sub(r"(qkd_static_kv_pc_path(?:_fan)?_nc(?:_b)?) #\((?!\.CORE_CLOCK)",
                  r"\1 #(.CORE_CLOCK(1), ", text)
    tile.write_text(text)
# Chain-head/position-strap variants must inherit CORE_CLOCK/SAME_CLOCK too;
# retaining the old generated clone would silently keep the old timing mode.
subprocess.run([sys.executable, str(tree / "tools/qwen_kv_die/plan_leaf_variants.py")], cwd=tree, check=True)

source = base / "inputs/kv_bound_rtl6/die_bound.v.gz"
net = gzip.open(source, "rt").read()
hs = re.search(r"(?m)^  \w+(?: #\([^;]*?\))? host \([^;]+\);", net)
ss = re.search(r"(?m)^  \w+ serdes_host \([^;]+\);", net)
if not hs or not ss:
    raise ValueError("missing original host/SerDes instance")
h = hs.group()
h = re.sub(r"^  \w+", "  qkd_host_root_admission_obsx_bo1_c45", h)
h = once(h, "#(", "#(.D2D_BOOT_ORDER(1), ")
h = once(h, " host (", " host (.d2d_boot_begin(kv45_boot_begin), ")
h, n = re.subn(r"\.phy_rx_v\([^)]*\),", ".phy_rx_v_w(kv45_rv_landed[0]), .phy_rx_v_e(kv45_rv_landed[1]),", h)
assert n == 1
for old in ("n_clk_phy[0]", "n_clk_host[0]", "n_clk_ingest[0]"):
    h = h.replace(old, "n_clk_core_c[0]")
s = ss.group()
s = re.sub(r"^  \w+ serdes_host", "  ot_qfd_serdes_112g_x12_phy_c45 serdes_host", s)
s = once(s, ".clk(n_clk_core_c[0]),", ".clk(n_clk_core_c[0]), .clk_phy(n_clk_phy[0]),")
s, n = re.subn(r"\.rx_v\([^)]*\),", ".rx_v_w(kv45_rv_w), .rx_v_e(kv45_rv_e),", s)
assert n == 1
relay = ("  wire kv45_rv_w, kv45_rv_e, kv45_boot_begin;\n  wire [1:0] kv45_rv_landed;\n"
         "  qkd_rlys_kv45_valid4 kv45_valid_age (.ck(n_clk_core_c[0]), "
         ".a({kv45_rv_e,kv45_rv_w}), .b(kv45_rv_landed));\n")
net = net.replace(hs.group(), h).replace(ss.group(), relay + s)
dest = out / "die_bound_native.v.gz"
with gzip.GzipFile(filename=str(dest), mode="wb", mtime=0) as f:
    f.write(net.encode())

a = json.loads((base / "kv44/asbuilt_kv44.json").read_text())
a["note"] = "KV45 native C1/C2+B+D core-clock source, pass0 metadata only; fresh R8, schedule constants and raw wavefront bind required before release."
a["netlist"] = [str(dest.relative_to(tree))]
a["split_bus_join"] = ["ot_qfd_serdes_112g_x12_phy_s2_c45"]
a["dissolve"] += ["ot_qfd_serdes_112g_x12_phy_c45", "ot_qfd_serdes_112g_x12_phy_s2_c45"]
a["transport"].append(dict(module="qkd_rlys_kv45_valid4", map={"b": "a"}, drop_in=["ck"], stages=4))
a["reducers"].append(dict(module=r"\$and", inst=r"serdes_host\.u_sub\.\$and\$serdes_c45\.sv:.*",
                          out="Y", op="and", stages=0))
a["substitute"].pop("ot_qfd_serdes_112g_x12_phy", None)
a["substitute_inst"] = [r for r in a.get("substitute_inst", []) if r["inst"] != "host"]
for r in a["sources"]:
    for pin in list(r.get("outputs", {})):
        if pin.startswith("pll_hbm_") or pin in ("pll_host", "pll_ingest", "pll_fwd"):
            r["outputs"][pin] = "core"
a["native_forwarded_clock"] = "pll_fwd is the same PLL1.2GHz source at pad-only qkd_ckbump; actual forwarded pin and physical phase/latency metadata remain in the clock plan; clk_phy stays separate."
new = [str((out / x).relative_to(tree)) for x in ("serdes_c45.sv", "qkd_host_root_admission_obsx_bo1_c45.sv", "group_r2c_native.sv")]
new += ["rtl/physical/" + x for x in ("ot_fdi_phy_cdc.sv", "ot_fdi_join2.sv", "ot_fdi_tx_pace.sv")]
a["files"] += new
a["prefer"] = [p for p in a["prefer"] if not p.endswith(("/qkd_kvs_grp_r2c.sv", "/qkd_kvs_grp_h_r2c.sv"))]
a["prefer"] += new
a["port_domains"] = [dict(module="ot_qfd_serdes_112g_x6_phy_c45", default="clk", sync=["rst_n"])]
# Rewire and plan-port names are keyed by the leaf's actual RTL module. Carry
# every existing BO1 alias across the native variant instead of losing chain
# identities (chf0/cha0/etc.) when the master name changes.
names = json.loads((base / "kv44/port_map_kv44.json").read_text())
host_map = next(v for v in names["masters"].values()
                if v.get("module") == "qkd_host_root_admission_obsx_bo1")
host_map = copy.deepcopy(host_map)
host_map["module"] = "qkd_host_root_admission_obsx_bo1_c45"
fdi = host_map["bundles"]["fdi"]
fdi["rtl_ports"] = [p for p in fdi["rtl_ports"] if p != "phy_rx_v"] + ["phy_rx_v_w", "phy_rx_v_e"]
fdi["die_bits"] += 1
fdi["rtl_bits"] += 1
names["masters"]["qkd_host_rt__kv45_c2"] = host_map
namefile = str((out / "port_map_kv45.json").relative_to(tree))
(out / "port_map_kv45.json").write_text(json.dumps(names, indent=1) + "\n")
a["port_names"] = namefile
a["rewires"]["port_map"] = namefile
a["land_align"] = False
for k in ("land_r8", "land_r8_extra", "param_regen"):
    a.pop(k, None)
a["lane_clock"] = "endpoint"
(out / "asbuilt_native_pass0.json").write_text(json.dumps(a, indent=1) + "\n")
print("prepared native C2 + controller/HOST core-clock source; release gate NOT RUN")
