#!/usr/bin/env python3
"""DIE-KV-64/RF-B 11-03 CONSERVATIVE form (OWNER 18:57, <=150k cells -> split): qkd_kvs_pc[_h_head_p] -> PCC + PCF.

Cut: u_path.u_front (qkd_kv_hbm_elastic_front_mc_nc, ~43.5k cells) + u_path.u_return (qkd_static_kv_return_slots_mc_nc,
~13.0k cells) move to the new core qkd_kvs_pcf; everything else (u_ctrl/u_sched, calendar, chain, esm, embr) stays in
PCC.  Inter-core face = {corrected_epoch[15:0], controller_co[281:0]} (298 b, PCC -> PCF only), registered on both
sides (PCC pin flop + PCF pin flop, +2 edges in front of the elastic front).  Die-face pins moving to PCF:
i_grp[104:71] (front_blk_go, expected_*) and the front/return o_grp bits; PCC keeps the rest.

    rf_kv3_split.py KIT_RTL_DIR PCC_OUT PCF_OUT TOP
KIT_RTL_DIR = a generated qkd_kvs_pc kit rtl/ (face/private/core-clock transforms applied); TOP = qkd_kvs_pc or
qkd_kvs_pc_h_head_p.  Writes the PCC sources (module-renamed copies) and the PCF top.
"""
import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rf_kv3_hhp_1105 import hhp_form_1105

# o_grp bit -> owner (from the leaf concat {return_idle_hbm .. actual_data})
OG_PCC = [289, 290, 291, 292, 293, 294, 299, 300]
OG_PCF = list(range(0, 289)) + [295, 296, 297, 298, 301, 302, 303, 304]
IG_PCF = list(range(71, 105))
IG_PCC = list(range(0, 71)) + list(range(105, 128))
SFX = "_sc"


def sub1(pat, rep, s, what, flags=re.S):
    s2, n = re.subn(pat, rep, s, count=1, flags=flags)
    assert n == 1, what
    return s2


def inst_block(s, mod, inst):
    m = re.search(r"\n(\s*)" + re.escape(mod) + r"\b[^;]*?\b" + re.escape(inst) + r"\s*\((.*?)\n\s*\);", s, re.S)
    assert m, (mod, inst)
    return m


def sub_once(s, old, new, what):
    assert s.count(old) == 1, what
    return s.replace(old, new)


def lec_twin_ties(src):
    """DIE-KV-67/LEC 11-04: the registers synthesis folds or merges, read through the surviving flop in the RTL (PCC only).
    Same class as the pcf_x ties: the gate has one flop, or a tie, where the RTL has separate state.  All are bit-exact after
    reset and the first load; PCF sources stay byte-identical."""
    out = dict(src)
    cal = "qkd_controller_hbm_calendar.sv"
    s = out[cal]
    s = sub_once(s, "output reg static_cmd_owner,", "output wire static_cmd_owner,", "cal port")
    s = sub_once(s, " reg sealed;reg [15:0] active_epoch;reg [18:0] active_row;\n",
                 " reg sealed;reg [15:0] active_epoch;reg [18:0] active_row;\n"
                 " // DIE-KV-67/LEC 11-04: owner = active_row[6]: same reset, same load, ROW0+layer has bit 6 set for layer<64.\n"
                 " initial if(ROW0!=64)$fatal(1,\"static_cmd_owner reads active_row[6]: ROW0 must be 64\");\n"
                 " assign static_cmd_owner=active_row[6];\n", "cal decl")
    s = sub_once(s, " static_cmd_owner<=0;static_cmd<=0;", " static_cmd<=0;", "cal reset")
    s = sub_once(s, "static_cmd_owner<=1;idle<=0;", "idle<=0;", "cal set")
    out[cal] = s
    tim = "ot_qkd_static_kv_timing.sv"
    s = out[tim]
    s = sub_once(s, "reg streaming; reg [2:0] last; reg [10:0] nm1;",
                 "reg streaming; reg [2:0] last_q; reg [10:0] nm1;  // DIE-KV-67/LEC 11-04: last = nm1[9:7] without context descriptors\n"
                 "    wire [2:0] last = CONTEXT_DESC != 0 ? last_q : nm1[9:7];\n   ", "tim decl")
    s = sub_once(s, "context_count<=0; last <= 0; nm1 <= 0;", "context_count<=0; last_q <= 0; nm1 <= 0;", "tim reset")
    s = sub_once(s, "nm1 <= desc_n - 11'd1; last <= context_accept", "nm1 <= desc_n - 11'd1; last_q <= context_accept", "tim load")
    out[tim] = s
    hd = "qkd_embedding_static_return_head.sv"
    if hd in out:
        s = out[hd]
        s = sub_once(s, "#(parameter integer MUT = 0) (", "#(parameter integer MUT = 0, parameter [297:0] TIE0 = 298'd0) (", "head param")
        s = sub_once(s, "wire [297:0] upo_d = ts_q ? retained : 298'd0;",
                     "// DIE-KV-67/LEC 11-04: TIE0 = record bits the PC strap holds 0 (unreset retained, X until the first capture;\n"
                     "    // synthesis ties these pin flops)\n"
                     "    wire [297:0] upo_d = ts_q ? (retained & ~TIE0) : 298'd0;", "head upo")
        out[hd] = s
        lf = "qkd_kvs_pc_h_head_p__leaf.sv"
        # word_index[3:0] and half load only spc[4:0] or 0, so a 0 strap bit holds its record bit 0
        out[lf] = sub_once(out[lf], "qkd_embedding_static_return_head #(.MUT(0)) u_embr",
                           "qkd_embedding_static_return_head #(.MUT(0), .TIE0({17'd0, ~PC[0], 2'b00, ~PC[4:1], 274'd0})) u_embr", "head inst")
    return out


def main(kit, pcc_out, pcf_out, top):
    kit, pcc_out, pcf_out = Path(kit), Path(pcc_out), Path(pcf_out)
    pcc_top = {"qkd_kvs_pc": "qkd_kvs_pcc", "qkd_kvs_pc_h_head_p": "qkd_kvs_pcc_h_head_p"}[top]
    pcf_top = "qkd_kvs_pcf"   # same front + return RTL in PC and HHP
    for d in (pcc_out, pcf_out):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)
    files = sorted(kit.glob("*.sv")) + sorted(kit.glob("*.v"))
    src = {f.name: f.read_text() for f in files}

    # ---- path_nc: drop u_front / u_return, export pcf_x
    pn = "qkd_static_kv_pc_path_nc.sv"
    s = src[pn]
    body_end = s.index("\nendmodule", s.index("module qkd_static_kv_pc_path_nc"))
    head, tail = s[:body_end], s[body_end:]
    fr = inst_block(head, "qkd_kv_hbm_elastic_front_mc_nc", "u_front")
    rt = inst_block(head, "qkd_static_kv_return_slots_mc_nc", "u_return")
    front_txt, ret_txt = fr.group(0), rt.group(0)
    head = head.replace(front_txt, "").replace(ret_txt, "")
    head = head.replace("module qkd_static_kv_pc_path_nc ", f"module qkd_static_kv_pc_path_nc{SFX} ", 1)
    head = sub1(r"(module qkd_static_kv_pc_path_nc" + SFX + r"\b[^\n]*\n)", r"\1    output wire [297:0] pcf_x,  // RF-B split: {corrected_epoch, controller_co} -> PCF\n", head, "pn port")
    head += ("\n    // RF-B split (DIE-KV-64/RF-B 11-03): u_front + u_return live in the PCF core; their outputs leave from PCF pins\n"
             # DIE-KV-66/LEC 11-04: bit 8 = controller l_sec[7], the literal 1'b0 of qkd_ctrl_pc_sched reached through unreset
             # s1/o_sec (X until the first ECC beat); synthesis ties it, so tie it here as KV-KITS-10 does at the landing.
             # DIE-KV-67/LEC 11-04: bits [17:12] = l_sec[16:11] = (row - ROW0)[5:0] = row[5:0] at ROW0=64, an unreset twin of
             # l_row[5:0] (co[23:18]); synthesis merges the two, so read the row flops here.
             "    assign pcf_x = {corrected_epoch, controller_co[281:18], controller_co[23:18], controller_co[11:9], 1'b0, controller_co[7:0]};\n"
             "    assign {front_blk_freed, front_hold, front_stall_edges, front_occupancy, front_idle_hbm, front_fault_overflow_hbm,"
             " front_fault_go_hbm} = 26'd0;\n"
             "    assign {actual_valid, actual_sector, actual_epoch, actual_layer, actual_data, return_fault_hbm, return_fault_core,"
             " return_idle_hbm, return_idle_core} = 293'd0;\n"
             "    wire unused_front_ret = &{front_put, front_co, front_epoch};\n")
    # front_co/front_epoch/front_put are now undriven wires; drop the declarations instead
    head = head.replace("    wire unused_front_ret = &{front_put, front_co, front_epoch};\n", "")
    for w in ("    wire [281:0] front_co;\n", "    wire [15:0] front_epoch;\n", "    wire front_put;\n"):
        assert w in head, w
        head = head.replace(w, "")
    src[pn] = head + tail

    # ---- pass pcf_x up the hierarchy: (module, child module, child instance), innermost first
    chain = {"qkd_kvs_pc": [("qkd_static_kv_pc_path_emb_nc_b", "qkd_static_kv_pc_path_nc", "u_path"),
                            ("qkd_static_kv_pc_path_fan_nc_b", "qkd_static_kv_pc_path_emb_nc_b", "u_pce"),
                            (f"{top}__leaf", "qkd_static_kv_pc_path_fan_nc_b", "u_pc")],
             "qkd_kvs_pc_h_head_p": [("qkd_static_kv_pc_path_emb_nc_b", "qkd_static_kv_pc_path_nc", "u_path"),
                                     ("qkd_static_kv_pc_path_fan_nc_b_head_p", "qkd_static_kv_pc_path_emb_nc_b", "u_pce"),
                                     (f"{top}__leaf", "qkd_static_kv_pc_path_fan_nc_b_head_p", "u_pc")]}[top]
    for mod, child, inst in chain:
        newm = f"{pcc_top}__leaf" if mod.endswith("__leaf") else mod + SFX
        fn = next(n for n, t in src.items() if re.search(r"^(\(\* [^)]*\*\) )?module " + re.escape(mod) + r"\b", t, re.M))
        s = src[fn]
        a0 = re.search(r"^(\(\* [^)]*\*\) )?module " + re.escape(mod) + r"\b", s, re.M).start()
        b0 = s.index("\nendmodule", a0)
        M = s[a0:b0]
        M = re.sub(r"module " + re.escape(mod) + r"\b", "module " + newm, M, count=1)
        k = M.index("module " + newm) + len("module " + newm)
        while M[k].isspace():
            k += 1
        if M[k] == "#":   # skip the parameter list
            k = M.index("(", k)
            dep = 0
            while True:
                dep += {"(": 1, ")": -1}.get(M[k], 0)
                k += 1
                if dep == 0:
                    break
        k = M.index("(", k) + 1
        M = M[:k] + "\n    output wire [297:0] pcf_x,   // RF-B split -> PCF" + M[k:]
        cm = re.search(r"\b" + re.escape(child) + r"\b(\s*#\s*\()?", M)
        assert cm, (mod, child)
        ci = re.search(r"\b" + re.escape(child) + r"(\s*#\s*\(.*?\))?\s+" + re.escape(inst) + r"\s*\(", M, re.S)
        assert ci, (mod, inst)
        rep = ci.group(0).replace(child, child + SFX, 1) + ".pcf_x(pcf_x), "
        M = M[:ci.start()] + rep + M[ci.end():]
        src[fn] = s[:a0] + M + s[b0:]
    # ---- top: rename, re-port i_grp/o_grp, registered pcf_x
    tf = f"{top}.sv"
    s = src[tf]
    s = s.replace(f"module {top} (", f"module {pcc_top} (", 1)
    # gen re-adds the 12.2a1 island ft ports / dont_touch BUFs from the pin table (island_ft): strip the kit's copies
    s, nft = re.subn(r"\n    (input|output) wire ft_ck_[io]_\d+,", "", s)
    s, nbf = re.subn(r"\n    \(\* keep = 1(, dont_touch = 1)? \*\) (BUFx24_ASAP7_75t_R mp_isl\d+_ck\d+ \([^;]*\);|wire ft_ck_o_\d+__p1;)", "", s)
    s = re.sub(r"\n    // KV-CORES-PV2 \(12.2a1\)[^\n]*", "", s)
    assert nft == 4 and nbf == 6, (nft, nbf)
    s = sub1(r"    input wire \[127:0\] i_grp,\n", "    input wire [93:0] i_grp_c,   // RF-B split: i_grp minus [104:71] (-> PCF)\n", s, "igrp")
    s = sub1(r"    output wire \[304:0\] o_grp,\n", "    output wire [7:0] o_grp_c,   // RF-B split: o_grp {300,299,294..289}\n"
             "    output wire [297:0] pcf_x,   // RF-B split: PCC -> PCF face (registered)\n", s, "ogrp")
    for k in range(305):
        pat = rf"\n    assign o_grp\[{k}\] = n0\[{k}\];"
        dff = rf"\n    \(\* keep \*\) ot_kvpc_pin_dff u_ogrp_{k} \(\.ck\(ck\[0\]\), \.d\(n0\[{k}\]\), \.q\(o_grp\[{k}\]\)\);[^\n]*"
        if k in OG_PCC:
            j = OG_PCC.index(k)
            s, n1 = re.subn(pat, f"\n    assign o_grp_c[{j}] = n0[{k}];", s)
            s, n2 = re.subn(dff, f"\n    (* keep *) ot_kvpc_pin_dff u_ogrp_{k} (.ck(ck[0]), .d(n0[{k}]), .q(o_grp_c[{j}]));   // PATH-KV-PC P3 (+1 edge)", s)
        else:
            s, n1 = re.subn(pat, "", s)
            s, n2 = re.subn(dff, "", s)
        assert n1 + n2 == 1, k
    s = sub1(r"\.i_grp\(i_grp\[127:0\]\),", ".i_grp({i_grp_c[93:71], 34'd0, i_grp_c[70:0]}),   /* [104:71] -> PCF */", s, "leaf igrp")
    s = sub1(r"qkd_kvs_pc(_h_head_p)?__leaf u_leaf \(", f"wire [297:0] pcf_x_d;\n    {pcc_top}__leaf u_leaf (\n        .pcf_x(pcf_x_d),", s, "leaf inst")
    regs = "".join(f"    (* keep *) ot_kvpc_pin_dff u_pcfx_{k} (.ck(ck[0]), .d(pcf_x_d[{k}]), .q(pcf_x[{k}]));\n" for k in range(298))
    s = s.replace("\nendmodule", "\n    // RF-B split: PCC -> PCF face launch flops (+1 edge)\n" + regs + "endmodule", 1)
    src[tf] = s
    pcc_src = lec_twin_ties(src)
    if top == "qkd_kvs_pc_h_head_p":   # DIE-KV-71/HHP 11-05 form: this core only
        pcc_src = hhp_form_1105(pcc_src, tf)
    for n, t in pcc_src.items():   # the PCF copies below read src, unpatched
        (pcc_out / (pcc_top + ".sv" if n == tf else n)).write_text(t)

    # ---- PCF top
    pf = []
    pf.append("// GENERATED by rf_kv3_split.py (DIE-KV-64/RF-B 11-03 CONSERVATIVE split): u_path.u_front + u_path.u_return of "
              f"{top}\n// moved out of the PC core; inputs {{corrected_epoch, controller_co}} from PCC (registered both sides).\n"
              "`timescale 1ns/1ps\n`default_nettype none\n")
    pf.append(f"module {pcf_top} (\n    input wire [0:0] ck,\n    input wire [0:0] rst_n,\n    input wire [0:0] hrst_n,\n"
              "    input wire [297:0] pcf_x,\n    input wire [33:0] i_grp_f,   // = i_grp[104:71]\n"
              "    output wire [296:0] o_grp_f   // = {o_grp[304:301], o_grp[298:295], o_grp[288:0]}\n);\n")
    pf.append("    wire [297:0] x_q;\n")
    pf.extend(f"    (* keep *) ot_kvpc_pin_dff u_pcfx_{k} (.ck(ck[0]), .d(pcf_x[{k}]), .q(x_q[{k}]));\n" for k in range(298))
    pf.append("    wire [281:0] controller_co = x_q[281:0];\n    wire [15:0] corrected_epoch = x_q[297:282];\n"
              "    // i_grp_f pin flops + 1 more edge: blk_go / expected_* see the same +2 edges as {co, epoch}, so PCF is the PC's\n"
              "    // front + return shifted uniformly by 2 edges (blk_go = nominal landing + GO_DLY keeps its full PHY jitter window)\n"
              "    // resets ride the same +2 edges (plain pin flops): PCF(t) == PC front + return (t-2) exactly, incl. reset edges\n"
              "    reg [33:0] ig_d1, ig_d2; reg rs_d1, rs_d2, hr_d1, hr_d2;\n"
              "    always @(posedge ck[0]) begin ig_d1 <= i_grp_f; ig_d2 <= ig_d1; rs_d1 <= rst_n[0]; rs_d2 <= rs_d1;"
              " hr_d1 <= hrst_n[0]; hr_d2 <= hr_d1; end\n"
              "    wire [127:0] i_grp = {23'd0, ig_d2, 71'd0};\n"
              "    wire front_hck = ck[0], return_hck = ck[0], return_ck = ck[0], hrst = hr_d2, rsi = rs_d2;\n"
              "    wire [3:0] front_hbm_data = {4{ck[0]}}, return_hbm_data = {4{ck[0]}};\n"
              "    wire front_blk_go = i_grp[71];\n    wire [15:0] expected_epoch = i_grp[87:72];\n"
              "    wire [5:0] expected_layer = i_grp[93:88];\n    wire expected_put = i_grp[94];\n"
              "    wire [9:0] expected_sector = i_grp[104:95];\n"
              "    wire [281:0] front_co;\n    wire [15:0] front_epoch;\n    wire front_put;\n"
              "    wire front_blk_freed, front_hold, front_idle_hbm, front_fault_overflow_hbm, front_fault_go_hbm;\n"
              "    wire [15:0] front_stall_edges;\n    wire [5:0] front_occupancy;\n"
              "    wire actual_valid, return_fault_hbm, return_fault_core, return_idle_hbm, return_idle_core;\n"
              "    wire [9:0] actual_sector;\n    wire [15:0] actual_epoch;\n    wire [5:0] actual_layer;\n    wire [255:0] actual_data;\n")
    pf.append(front_txt + "\n" + ret_txt + "\n")
    # o_grp as the PC leaf/top drive it: 295/296 through the PATH-KV-PC P3 pin flops (+1 edge), the rest direct
    pf.append("    wire [304:0] n0 = {return_idle_hbm, return_idle_core, return_fault_hbm, return_fault_core, 2'd0, front_idle_hbm,"
              " front_hold, front_fault_overflow_hbm, front_fault_go_hbm, 6'd0, actual_valid, actual_sector, actual_layer,"
              " actual_epoch, actual_data};\n")
    for j, k in enumerate(OG_PCF):
        if k in (295, 296):
            pf.append(f"    (* keep *) ot_kvpc_pin_dff u_ogrp_{k} (.ck(ck[0]), .d(n0[{k}]), .q(o_grp_f[{j}]));   // PATH-KV-PC P3 (+1 edge)\n")
        else:
            pf.append(f"    assign o_grp_f[{j}] = n0[{k}];\n")
    pf.append("endmodule\n`default_nettype wire\n")
    (pcf_out / f"{pcf_top}.sv").write_text("".join(pf))
    for n in ("qkd_static_kv_pc_path_nc.sv", "qkd_static_kv_return_slots_mc.sv", "qkd_kv_hbm_elastic_front_mc.sv",
              "ot_kvpc_pin_ff.sv"):
        t = src[n] if n != pn else (kit / n).read_text()
        if n == pn:  # PCF only needs the nc front / return modules from this file, not the path module
            a = t.index("module qkd_static_kv_pc_path_nc")
            b = t.index("endmodule", a) + len("endmodule")
            t = t[:a] + "// (qkd_static_kv_pc_path_nc removed: lives in PCC)\n" + t[b:]
        (pcf_out / n).write_text(t)
    json.dump(dict(og_pcc=OG_PCC, og_pcf=OG_PCF, ig_pcc=IG_PCC, ig_pcf=IG_PCF, pcc_top=pcc_top, pcf_top=pcf_top),
              open(pcf_out.parent / f"{pcf_top}_split_map.json", "w"), indent=0)
    print("RF_KV3_SPLIT", pcc_top, pcf_top, len(files))


if __name__ == "__main__":
    main(*sys.argv[1:5])
