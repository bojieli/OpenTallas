"""MU-ADOPT-TOK: mu_tok_cases (MU.TOK.QW case generator) checks."""
from qwen_static_schedule import mu_calendar as M
from qwen_static_schedule import mu_tok_cases as T


def test_image_fits_and_user0_is_identity():
    segs = T.segments()
    pw, dw = T.image(segs)
    assert dw[0] >> 32 == 0x43414C44 and (dw[0] & 0x1FF) * 2 + T.IMG_BASE <= 976
    for _, c in segs[1]:
        assert T.reloc(c, 0) == c
    assert all(t >= 4 + 3 for t, _ in segs[1][:1])            # filler first-entry rule T_0 >= 4 + (NU - 1)


def test_record_is_not_playable_and_layer_is():
    rec = T.cases("record", tokens=2)
    assert not rec["playability"]["rtl_playable"]
    assert rec["users"][0]["token_period"] == rec["single_user_token_cycles"]
    lay = T.cases("rtl_layer", tokens=3)
    assert lay["playability"]["rtl_playable"]
    assert lay["command_plane_clashes"] == dict(start=0, cmd=0, done=0)
    assert lay["users"][0]["token_period"] == lay["single_user_token_cycles"]


def test_kv_rows_and_stages():
    cs = T.cases("rtl_layer", tokens=2)
    u1 = cs["users"][1]
    assert u1["kv_rows"]["L0"] == 64 + 256 and u1["kv_rows"]["L35"] == 99 + 256
    st = {s["unit"]: s["stage"] for s in u1["starts"]}
    assert st["L0"] == 1 and st["L35"] == 36 and st["head.c0"] == T.LAST_STAGE and st["head"] == 0


def test_cmd_windows_hook_off_by_default():
    a = M.layer_block(dict(M.SOURCED))
    assert not any(r.startswith("cp.") for r in a["windows"])
    b = M.layer_block(dict(M.SOURCED, seg_windows=T.seg_windows(T.segments())))
    assert "cp.cmd" in b["windows"] and "cp.stn" in b["windows"]


def test_record_op_playable():
    """MU-QW-B1: the op-granular periodic frame (mu_opcal) is the RTL-playable case table of record"""
    cs = T.cases("record_op")
    assert cs["playability"]["rtl_playable"] and cs["granularity"] == "op_leaf"
    assert abs(cs["aggregate_tok_s_modelled"] - 13708.2) < 0.1          # MU-OPCAL-EMB: EMB after the result (was 13,711.4)
    assert [u["tokens_per_frame"] for u in cs["users"]] == [16, 15, 8, 7]
    assert all(s["src"] == "face" for s in cs["users"][0]["starts"])
    assert all(s["src"] == "leaf" for u in cs["users"][1:] for s in u["starts"])
    assert cs["leaf"]["entries"] + 1 <= 4096 and cs["relocation"]["UVM_STRIDE"] == M.DV_UVM_STRIDE
