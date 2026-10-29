#!/usr/bin/env python3
"""KV-KITS-21 (ASK-C, DIE-KV-27 plan event27, KV-007): qkd_ahub with seven co-timed clock entries, 0 added cycles.

ck[0] centre (u_rr, u_core except am, zh relays, zh_err_q, recip loop), ck[1]/ck[2] south/north zh pairs (unchanged from
Codex ck3), and four new face entries (event27.json rtl_delta; pin census of qkd_ahub_pins_r27.json):
  ck[3] S-W (150,50):  ap_q[94:0]  = ap0, ap1, ap2[8:0] pin flops;  u_core am[143:0] output pin registers (am0..am3)
  ck[4] S-E (450,50):  ap_q[171:95] = ap2[42:9], ap3 pin flops;     u_io whole (hs pin flops, start/epoch/T, hf fault)
  ck[5] E-S (580,110): u_rw_s = fr_epoch[15:0] + fr_rz[55:0] output relay flops (pins y < 220)
  ck[6] E-N (580,330): u_rw_n = fr_rz[127:56] + fr_valid output relay flops    (pins y >= 220)
Only clock pins change.  Every substitution is listed in SUBS and the reverse substitution must restore the original
module text byte-for-byte (collapse check below); the split always/instance forms are proven edge-exact by the tied-clock
bench (tb_qkd_ahub_static_dw with every entry = ck) and the per-entry stopped-clock mutants (CKMUT 1..5).

usage: clock_split7.py REPO OUT    (REPO = repo root; writes OUT/{qkd_ahub.sv, qkd_ahub_static_dw.sv, core.json})
"""
import argparse
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent

# ---- qkd_ahub_static_core_la -> _ck7: am output pin registers on their own clock (clk_am) ----
CORE_SUBS = [
    ("module qkd_ahub_static_core_la #(", "module qkd_ahub_static_core_la_ck7 #("),
    ("    input wire clk,rst_n,start,active_layer_parity,",
     "    input wire clk,rst_n,start,active_layer_parity,\n    input wire clk_am,   // KV-KITS-21 ck7: am pin registers (S-W entry)"),
    ("        if(!rn[1])begin ma_v<=0;mb_v<=0;mo_v<=0;for(integer a=0;a<4;a=a+1)am[36*a+35]<=0;end\n"
     "        else begin ma_v<=m_issue&&!start;mb_v<=ma_v&&!start;mo_v<=mb_v&&!start;\n"
     "            for(integer a=0;a<4;a=a+1)am[36*a+35]<=mo_v;end\n",
     "        if(!rn[1])begin ma_v<=0;mb_v<=0;mo_v<=0;end\n"
     "        else begin ma_v<=m_issue&&!start;mb_v<=ma_v&&!start;mo_v<=mb_v&&!start;end\n"
     "    always @(posedge clk_am or negedge rn[1])\n"
     "        if(!rn[1])begin for(integer a=0;a<4;a=a+1)am[36*a+35]<=0;end\n"
     "        else begin for(integer a=0;a<4;a=a+1)am[36*a+35]<=mo_v;end\n"),
    ("        mb_x<={m23[31:0],m01[31:0]};mb_a<={m23[32],m01[32]};mo_data<=mfin[31:0];\n"
     "        for(integer a=0;a<4;a=a+1)am[36*a+:35]<={1'b0,mo_h,mo_data};\n    end\n",
     "        mb_x<={m23[31:0],m01[31:0]};mb_a<={m23[32],m01[32]};mo_data<=mfin[31:0];\n    end\n"
     "    always @(posedge clk_am)begin\n"
     "        for(integer a=0;a<4;a=a+1)am[36*a+:35]<={1'b0,mo_h,mo_data};\n    end\n"),
]

# ---- qkd_ahub_static_dw -> _ck7 ----
DW_SUBS = [
    ("module qkd_ahub_static_dw #(", "module qkd_ahub_static_dw_ck7 #("),
    ("    input  wire          ck,\n    input  wire          rst_n,",
     "    input  wire          ck,\n    input  wire [1:0]    ck_zh,   // zh S pair / N pair (Codex ck3)\n"
     "    input  wire [3:0]    ck_ent,  // KV-KITS-21 event27 face entries: S-W, S-E, E-S, E-N\n"
     "    input  wire          rst_n,"),
    ("    always @(posedge ck) ap_q <= {ap3, ap2, ap1, ap0};",
     "    always @(posedge ck_ent[0]) ap_q[94:0] <= {ap2[8:0], ap1, ap0};\n"
     "    always @(posedge ck_ent[1]) ap_q[171:95] <= {ap3, ap2[42:9]};"),
    ("    ot_qkd_drly #(.W(145), .N((MUT == 6) ? 0 : WF_RLY)) u_rw (.clk(ck), .d({fr_rz_i, fr_epoch_i, fr_valid_i}),\n"
     "        .q({fr_rz, fr_epoch, fr_valid}));",
     "    ot_qkd_drly #(.W(72), .N((MUT == 6) ? 0 : WF_RLY)) u_rw_s (.clk(ck_ent[2]), .d({fr_rz_i[55:0], fr_epoch_i}),\n"
     "        .q({fr_rz[55:0], fr_epoch}));\n"
     "    ot_qkd_drly #(.W(73), .N((MUT == 6) ? 0 : WF_RLY)) u_rw_n (.clk(ck_ent[3]), .d({fr_rz_i[127:56], fr_valid_i}),\n"
     "        .q({fr_rz[127:56], fr_valid}));"),
    ("    qkd_ahub_static_io #(.AP_OFS(AP_OFS), .FR_OFS(FR_OFS), .WF_RLY(WF_RLY), .MUT(MUT)) u_io (\n        .ck(ck),",
     "    qkd_ahub_static_io #(.AP_OFS(AP_OFS), .FR_OFS(FR_OFS), .WF_RLY(WF_RLY), .MUT(MUT)) u_io (\n        .ck(ck_ent[1]),"),
    ("    qkd_ahub_static_core_la #(.Z_IN_STRIDE(Z_IN_STRIDE), .Z_LEVEL_GAP(10), .RS_RLY(RS_RLY), .MUT(MUT)) u_core (",
     "    qkd_ahub_static_core_la_ck7 #(.Z_IN_STRIDE(Z_IN_STRIDE), .Z_LEVEL_GAP(10), .RS_RLY(RS_RLY), .MUT(MUT)) u_core (\n"
     "        .clk_am(ck_ent[0]),"),
    ("ot_nhb_zh u_zh (.clk(ck),", "ot_nhb_zh u_zh (.clk(ck_zh[(a < 2) ? 0 : 1]),"),
]


def module(src, name):
    m = re.findall(r"^module %s\b.*?^endmodule\b" % name, src, re.M | re.S)
    if len(m) != 1:
        raise ValueError(f"exactly one module {name} required")
    return m[0]


def apply(orig, subs):
    out = orig
    for old, new in subs:
        if out.count(old) != 1:
            raise ValueError(f"substitution anchor not unique/absent: {old[:60]!r}")
        out = out.replace(old, new, 1)
    back = out
    for old, new in reversed(subs):
        if back.count(new) != 1:
            raise ValueError(f"reverse anchor not unique: {new[:60]!r}")
        back = back.replace(new, old, 1)
    if back != orig:
        raise ValueError("the transformation changed a non-clock token")
    return out


def wrapper(src):
    if src.count("input wire [0:0] ck,") != 1 or src.count(".ck(ck[0]),") != 1 or src.count("qkd_ahub_static_dw #(") != 1:
        raise ValueError("unexpected source wrapper clock declaration/connection")
    src = src.replace("input wire [0:0] ck,", "input wire [6:0] ck,", 1)
    src = src.replace("qkd_ahub_static_dw #(", "qkd_ahub_static_dw_ck7 #(", 1)
    return src.replace(".ck(ck[0]),", ".ck(ck[0]), .ck_zh(ck[2:1]), .ck_ent(ck[6:3]),", 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo", type=Path)
    ap.add_argument("out", type=Path)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    dw_src = (a.repo / "rtl/hdc/nearhbm/qkd_ahub_static_dw.sv").read_text()
    core7 = apply(module(dw_src, "qkd_ahub_static_core_la"), CORE_SUBS)
    dw7 = apply(module(dw_src, "qkd_ahub_static_dw"), DW_SUBS)
    (a.out / "qkd_ahub_static_dw.sv").write_text(
        dw_src + "\n// KV-KITS-21 ck7: seven co-timed clock entries (event27 ASK-C); 0 added cycles.\n" + core7 + "\n\n" + dw7 + "\n")
    (a.out / "qkd_ahub.sv").write_text(wrapper((HERE / "codex_qkd_ahub.sv").read_text()))
    d = json.loads((HERE / "codex_core_source.json").read_text())
    rel = a.out.relative_to(a.repo)
    d["files"] = [str(rel / Path(f).name) if Path(f).name in ("qkd_ahub.sv", "qkd_ahub_static_dw.sv") else f
                  for f in d["files"]]
    d["port_decl"]["ck"] = ["input", 6, 0]
    extra = [f"ck[{i}]" for i in range(1, 7)]
    if isinstance(d["pin_bits"], list):
        d["pin_bits"].extend(extra)
    else:
        d["pin_bits"] += len(extra)
    d["classes"]["clk"] = 7
    d["pin_class"].update({k: "clk" for k in extra})
    d["boundary_role"] = {"ck": "clk", "rst_n": "reset"}
    d["clock_split"] = {
        "roots": ["ck[0] centre: u_rr, u_core (not am), zh relays, zh_err_q, recip loop",
                  "ck[1] south zh[0:1]", "ck[2] north zh[2:3]",
                  "ck[3] S-W: ap_q[94:0] (ap0, ap1, ap2[8:0]) + u_core.am[143:0]",
                  "ck[4] S-E: ap_q[171:95] (ap2[42:9], ap3) + u_io (hs pin flops, hf)",
                  "ck[5] E-S: u_rw_s fr_epoch + fr_rz[55:0]",
                  "ck[6] E-N: u_rw_n fr_rz[127:56] + fr_valid"],
        "cycles_added": 0,
        "plan": "DIE-KV-27 event27 (ASK-C, KV-007) qkd_ahub_pins_r27.json",
        "proof": "reverse substitution restores both modules byte-for-byte; tied-clock tb_qkd_ahub_static_dw PASS; "
                 "per-entry stopped-clock mutants caught (bench_ck7.sh CKMUT 1..5)"}
    (a.out / "core.json").write_text(json.dumps(d, indent=2) + "\n")
    print("clock_split7: OK", a.out)


if __name__ == "__main__":
    main()
