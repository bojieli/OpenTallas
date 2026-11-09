import shlex, subprocess

import pytest

import kit_wave as K

VAL = "u_lf.u_vp.g_ln[14].u_l:172.8:163.776:MX,u_lf.u_vq:639.36:440.64:MX"


def env(k, v):
    return K.item_env({"item_env": {"i": {k: v}}}, "i")


def test_macro_moves_accepts_indexed_instances():
    assert env("OT_MACRO_MOVES", VAL) == {"OT_MACRO_MOVES": VAL}


def test_brackets_stay_rejected_on_other_keys():
    with pytest.raises(ValueError):
        env("OT_OTHER", VAL)


@pytest.mark.parametrize("bad", ["u[1]:1:2;rm -rf x", "u[1]:1:2 x", "u[$(id)]:1:2", "u[1]`id`:1:2", "u[1]:1:2\n", "u[1]|x"])
def test_macro_moves_keeps_every_other_restriction(bad):
    with pytest.raises(ValueError):
        env("OT_MACRO_MOVES", bad)


def test_consumer_export_quotes_the_value():
    # the one consumer: genv = "export K=<shlex.quote(v)>; " in run_item
    out = subprocess.run(["bash", "-c", f"cd /; export OT_MACRO_MOVES={shlex.quote(VAL)}; printenv OT_MACRO_MOVES"],
                         capture_output=True, text=True, check=True).stdout
    assert out.strip() == VAL
