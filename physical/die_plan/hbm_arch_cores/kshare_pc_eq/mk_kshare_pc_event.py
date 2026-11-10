#!/usr/bin/env python3
# DIE-HBM-97/KSHARE-PC 2026-11-10: pin-cycle event kshare_pc_1109 on p11t (corelat rows + compiler_core_delta pending entry)
import json, hashlib
from pathlib import Path
P = Path(".")
IN = [("w_k_v", 4, "u_wbk_Q"), ("w_k_addr", 120, "u_wbk_Q"), ("w_k_wdata", 1024, "u_wbk_Q"),
      ("c_kr_v", 4, "u_ctl_Q_p*"), ("c_kr_tag", 68, "u_ctl_Q_p*"), ("c_kr_beat", 16, "u_ctl_Q_p*"), ("c_kr_data", 1024, "u_ctl_Q_p*")]
OUT = [("fill_v", 4), ("fill_bank", 4), ("fill_slot", 24), ("fill_epoch", 64), ("fill_data", 1024)]
ZERO = "g_k_v,g_k_rdy,g_k_addr,g_k_len,g_k_tag,g_k_we,g_k_wdata,g_k_wstrb,g_k_wr_done,g_kr_v,g_kr_rdy,g_kr_tag,g_kr_beat,g_kr_data,c_k_v,c_k_rdy,c_k_addr,c_k_len,c_k_tag,c_k_we,c_k_wdata,c_k_wstrb,c_k_wr_done,c_kr_rdy,w_k_rdy,w_k_wr_done,vm_v,vm_bank,vm_epoch,vm_row,vm_col,wbw_v,wbw_base,wbw_total,sm_stream,sm_hbm,fault"
rows = ["core\tsub_block\tport_or_bus\tdir\tadded_cycles\tnote"]
for v in ("v8e478a", "v700685"):
    c = f"ot_hbm_svc_vm_kshare_splitstrap__{v}"
    rows.append(f"{c}\t\t{','.join(n for n, _, _ in IN)}\tport\t1\tface_shell in-stage relay u_bimid0_<bus> (hbm_clk, free-placed) after the face flop u_bin_<bus>; 7 buses, 2260 bits; exact: new shell == vR shell with these inputs delayed 1 hbm edge (lockstep bench MODE 0)")
    rows.append(f"{c}\t\t{','.join(n for n, _ in OUT)}\tport\t1\tcore PCF (2): stream_clk register fa_v/fa_d between the fill FIFO read port and the fill pin registers (registered hbm_clk-tree -> stream_clk-tree crossing); 5 buses, 1120 bits")
    rows.append(f"{c}\t\thbm_rst_n\tport\t1\tcore PCF (1): lane reset relay lrst_q[l] (async assert, release +1 hbm edge after hrst_q); reset contract rst_n >= 64 edges unchanged")
    rows.append(f"{c}\t\t{ZERO}\tport\t0\tunchanged (PCF (3) lane-state flag copies q_issue/q_wb/q_norm are loaded from the exact next state: 0 cycles)")
    rows.append(f"{c}\t\t(c_kr->fill)\tin->out\t+2\tVM read beat -> fill pin: c_kr relay +1, fill stage +1 (window command -> first VM request unchanged)")
    rows.append(f"{c}\t\t(w_k->c_k)\tin->out\t+1\tWB write request -> controller request: w_k relay +1")
tsv = P / "corelat/cycles_kshare_pc_1109.tsv"
tsv.write_text("\n".join(rows) + "\n")
d = json.loads((P / "compiler_core_delta.json").read_text())
d["pending_not_folded"]["DIE-HBM-97/KSHARE-PC kshare_pc_1109"] = (
    "ot_hbm_svc_vm_kshare_splitstrap__v8e478a/__v700685 (q_hub_nw/q_hub_ne u_vmks_Q0..Q3, 8 instances): w_k_* and c_kr_* inputs +1, "
    "fill_* outputs +1, hbm_rst_n lane release +1 (corelat/cycles_kshare_pc_1109.tsv). VM fill window: last VM beat -> fill +2 hbm edges per window; "
    "WB write window: w_k request -> controller +1. Type-internal crossings u_ctl_Q_p* -> u_vmks (c_kr), u_wbk_Q -> u_vmks (w_k), u_vmks -> u_vmdel_Q* (fill). "
    "Fold into ext/crossing_latency (type_internal rows, added_rtl_cycles) and the compiler fill/WB window calendar at the next ext_census regen (TOK lane), "
    "after the PC form signs off and its RTL merges (branch claude/die-hbm-97-kshare-pc-1109). Owner 11-03: pin cycles are a lever (compiler + token); "
    "owner 12.21: tok/s loss from closure fixes accepted")
(P / "compiler_core_delta.json").write_text(json.dumps(d, indent=1) + "\n")
sh = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
ev = {
 "schema": "opentallas.hbm_plan_event.v1",
 "event": "kshare_pc_1109",
 "plan": "kshare_pc_1109 (plan_p12_kshare)",
 "base": "p11t (die_plan.json 4548550146e469dee3c7b93586d4428fd56eeeb8cf924b05f8722444f6b0acf9)",
 "lane": "DIE-HBM-97/KSHARE-PC",
 "date": "2026-11-10",
 "kind": "core pin cycles (COORD YES: pin-cycle form; owner 11-03 pin cycles are a lever, compiler reschedule + token)",
 "modules": ["ot_hbm_svc_vm_kshare_splitstrap__v8e478a", "ot_hbm_svc_vm_kshare_splitstrap__v700685"],
 "instances": {"q_hub_nw": {"u_vmks_Q0": "v700685", "u_vmks_Q1": "v8e478a", "u_vmks_Q2": "v700685", "u_vmks_Q3": "v700685"},
               "q_hub_ne": {"u_vmks_Q0": "v700685", "u_vmks_Q1": "v8e478a", "u_vmks_Q2": "v700685", "u_vmks_Q3": "v700685"}},
 "ports_plus1": {
   "inputs_hbm_clk": [{"port": n, "width": w, "dir": "input", "face": "w_k from u_wbk_Q" if n.startswith("w_k") else "c_kr from u_ctl_Q_p*", "added_cycles": 1} for n, w, _ in IN],
   "outputs_stream_fill": [{"port": n, "width": w, "dir": "output", "face": "fill to u_vmdel_Q*", "added_cycles": 1} for n, w in OUT],
   "reset": [{"port": "hbm_rst_n", "width": 1, "dir": "input", "added_cycles": 1, "note": "lane reset release"}]},
 "ports_zero": ZERO.split(","),
 "changes": {"corelat": "corelat/cycles_kshare_pc_1109.tsv (new)", "compiler_core_delta": "pending_not_folded[DIE-HBM-97/KSHARE-PC kshare_pc_1109] (new)",
             "die_plan.json": "unchanged (no pin, outline, station, lane or clock change; core cycles are not carried by latency.lanes)"},
 "rtl": {"core ot_hbm_svc_vm_kshare_splitstrap.sv (PCF=1)": "5b5fcd124cf5c35b84a5f50f91a4f9c0fca5e5546a1b62cd80025eb4767234ee",
         "v8e478a fshell": "e584156b6d5b69cff8d6e0a21a32b80fbab117d4d3e98560ffe8fe86ef186930", "v8e478a wrap": "6cb46fe6a780c46c375f7172146e0d6c92b829a130aa5901751c04877f07a824",
         "v700685 fshell": "ae5ca134aafd7808e3c5656a6b20208721418c2251f2e55cf2adda28bbb244b2", "v700685 wrap": "95f5f02f49d1b3bf82c2c3dba616a4ce145f61689138e3ab9d6e48a865604267"},
 "evidence": {"bench": "epyc4 /srv/opentallas-scratch3/claude/die-hbm-97-kshare-pc/bench (mk_bench.py lockstep: new vs vR shell, inputs delayed 1 on the 7 buses, fill compared one edge later; MODE 0 PASS, MODE 1 (no fill shift) and MODE 2 (no input delay) FAIL)",
              "kits": "intel1 /srv/opentallas-scratch2/claude/die-hbm-97-kshare-pc/kit_kshare_{v8e478a,v700685}_vPC (DO_NOT_COUNT)"},
 "risk": "valid/ready loops around the +1 inputs: KRL1 c_kr (ring depth 3 sized for ready latency 1 + face) and w_k (pin skid2) each see one more cycle between the core ready and the arriving valid; the static schedule must keep the c_kr / w_k issue inside the window the controller and wb_kport already honour, or the ring needs depth 4 + c_rdy_seen +1",
 "not_changed": "outline, origin, orient, pins, clock taps/entries, stations, partitions, lanes, every other type",
 "gate": "plan check (--completeness --plan-geom report) vs chk_plan_p11t g0_report.json: new-only must be 0",
}
(P / "kshare_pc_1109_event.json").write_text(json.dumps(ev, indent=1) + "\n")
print(sh(tsv)[:12], sh(P / "compiler_core_delta.json")[:12], sh(P / "kshare_pc_1109_event.json"))
