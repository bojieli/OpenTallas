#!/usr/bin/env python3
"""QTILE-R 10-23: qkd_kvs_emb on the source the KV GEN binds (rtl3 7f6d02e82: module qkd_kvs_emb of
qkd_kvs_tiles_hroot_ff_k_hl_mu_ba_n32_pj_nc32.sv; tile_views verdict ASSUMED = no closed view).  The e1/i2 kit was the
388.8 x 302.4 die frame slot: hard child u_rowtx (216 x 151.2) + 1.9k um2 std, logic only at the faces, ~70% empty.
Outline from content: child (MY: its 550 payload pins face the E tile face, its 554 word pins face the W join band)
+ a W join band + an S band for i_ctl / i_hroot_ES/EN + >=20-um E/N bands.  Pin registers on every pin (e1 rule,
same latency as e1: +1 per input / output, px_tok / px_tep +2).  a: W band 41 um (282.96 x 218.16); b: W band 84 um."""
import copy, json, os
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../.."))
base = json.load(open(f"{ROOT}/physical/ref_tile/qkd_kvs_emb/spec.json"))
E = "rtl/qwen_sys/static_embedding_20261014/"
for name, cx, w, tag in (("qkd_kvs_emb_nc32a", 43.2, 282.96, "nc32a"), ("qkd_kvs_emb_nc32b", 86.4, 326.16, "nc32b")):
    s = copy.deepcopy(base)
    s["name"] = name
    s["sources"] = ["rtl/lib/ot_rst_relay.sv", E + "qkd_embedding_static_join4_cal.sv", E + "qkd_embedding_static_join4.sv",
                    E + "qkd_embedding_static_join.sv", "rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_tiles_hroot_ff_k_hl_mu_ba_n32_pj_nc32.sv"]
    s["outline"] = {"w": w, "h": 218.16, "exact": True}
    s["children"][0]["at"] = [cx, 43.2]
    s["fill_reason"] = {"pin_bound": f"content = hard u_rowtx 216 x 151.2 + ~1.9k um2 std + ~2.0k pin flops; the outline is the child plus "
                        f"one W join band ({round(cx - 2.16, 1)} um), a 41-um S band (673 S pins, 2.4/um) and 21.6-um E/N bands "
                        f"(E 786 pins over 218 um = 3.6/um); smaller faces would exceed ~5 pins/um. Was 388.8 x 302.4 (frame slot)."}
    s["low_fill_reason"] = s["fill_reason"]["pin_bound"]
    s["slot_change_request"] = {"from": [388.8, 302.4], "to": [w, 218.16], "why": "COORD/OWNER 10-23 outline-from-content; KV die lead (STEWARD-QKd) re-derives the frame slot"}
    s["structural_change"] = ("QTILE-R 10-23: kit of the BOUND nc32 qkd_kvs_emb (join4_cal NATIVE32+PIPE_JOIN, rope_sweep) with the outline from "
                              "content (was the 388.8 x 302.4 frame slot, logic only at the faces); same faces, same every-pin registers as e1")
    s["job"] = {"owner": "QTILE-R", "branch": "claude/qtile-r-kvemb-1023", "tag": tag,
                "purpose": "K.STA.EMB qkd_kvs_emb nc32 (die rtl3 binding) re-kit, outline from content", "benches": []}
    for k in ("reroute_reason",):
        s.pop(k, None)
    d = f"{ROOT}/physical/ref_tile/{name}"; os.makedirs(d, exist_ok=True)
    json.dump(s, open(f"{d}/spec.json", "w"), indent=1)
    print(name, w, 218.16, round(w * 218.16))
