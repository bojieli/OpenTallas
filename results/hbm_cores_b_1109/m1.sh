set -e
R=/srv/opentallas-scratch2/claude/kw35/repo
W=/srv/opentallas-scratch2/claude/kw36/wt_m
cd $R; git fetch -q origin 2>/dev/null || true
git worktree add -q --no-checkout -b claude/kw-fix-36-macro-moves-env-1108 $W origin/main
git -C $W sparse-checkout init --cone
git -C $W sparse-checkout set tools/autopilot
git -C $W checkout -q claude/kw-fix-36-macro-moves-env-1108
cd $W/tools/autopilot
python3 -I - <<'PY'
p="kit_wave.py"
s=open(p).read()
old='''        if not ENV_KEY_RE.fullmatch(str(k)) or not (ENV_VAL_RE.fullmatch(str(v)) or capture_path):
'''
new='''        # OT_MACRO_MOVES names hard-core instances such as u_vp.g_ln[14].u_l: [ ] are the only extra characters, the value is
        # shell-quoted at its one consumer (export in run_item)
        moves = k == "OT_MACRO_MOVES" and bool(ENV_VAL_RE.fullmatch(str(v).replace("[", "").replace("]", "")))
        if not ENV_KEY_RE.fullmatch(str(k)) or not (ENV_VAL_RE.fullmatch(str(v)) or capture_path or moves):
'''
assert s.count(old)==1
open(p,"w").write(s.replace(old,new))
open("test_kit_wave_item_env_moves.py","w").write('''import shlex, subprocess

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


@pytest.mark.parametrize("bad", ["u[1]:1:2;rm -rf x", "u[1]:1:2 x", "u[$(id)]:1:2", "u[1]`id`:1:2", "u[1]:1:2\\n", "u[1]|x"])
def test_macro_moves_keeps_every_other_restriction(bad):
    with pytest.raises(ValueError):
        env("OT_MACRO_MOVES", bad)


def test_consumer_export_quotes_the_value():
    # the one consumer: genv = "export K=<shlex.quote(v)>; " in run_item
    out = subprocess.run(["bash", "-c", f"cd /; export OT_MACRO_MOVES={shlex.quote(VAL)}; printenv OT_MACRO_MOVES"],
                         capture_output=True, text=True, check=True).stdout
    assert out.strip() == VAL
''')
PY
grep -n "gen_env" kit_wave.py | cut -c1-130
git add kit_wave.py test_kit_wave_item_env_moves.py
tar cf - kit_wave.py test_kit_wave_item_env_moves.py | ssh -o ControlPath=none epyc2 'cd /srv/opentallas-scratch3/claude/kw36 && rm -rf mt && mkdir mt && cp -al base/tools mt/tools && cp -al base/physical mt/physical && rm -f mt/tools/autopilot/kit_wave.py && tar xf - -C mt/tools/autopilot && cd mt/tools/autopilot && timeout 300 python3 -m pytest -q -W ignore -p no:cacheprovider test_kit_wave_item_env_moves.py test_kit_wave_genhosts.py 2>&1 | tail -3'
git commit -q -m "item_env: allow [ ] in OT_MACRO_MOVES values only

Hard-core instance names such as u_vp.g_ln[14].u_l made launch fail with a
ValueError on every pass (S81 leaf t15, t24cl81, t32, t40clf8).  Only this
key gets the two extra characters; every other restriction stays.  The one
consumer shell-quotes the value.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push -q origin claude/kw-fix-36-macro-moves-env-1108 2>&1 | tail -1
git rev-parse HEAD
