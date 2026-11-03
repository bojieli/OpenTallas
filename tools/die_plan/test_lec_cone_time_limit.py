"""prove(): per-cone ABC time limit + batch wall backstop (HBM tailx 11-02: one &cec -m x100 batch ran 45-151 h).

A cone that times out, or is cut off by the backstop, stays UNDECIDED and never shifts a verdict onto another cone;
finished cones keep their verdict. A cone that timed out under SAT sweeping (-m) skips the x1000 stage."""
import os
import stat
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lec


def test_cone_verdicts_segments():
    text = ("OTCONE 3 \nAssuming the current network is a single-output miter.\nTimed out after 64 seconds.\n"
            "OTCONE 4 \nAssuming ...\nNetworks are equivalent.  Time = 2.8 sec\n"
            "OTCONE 5 \nNetworks are NOT EQUIVALENT.\n"
            "OTCONE 6 \nUNSAT =      0.  SAT =      0.   UNDEC =      1.  Trivial = 0.\n"
            "OTCONE 7 \nUNSAT =      1.  SAT =      0.   UNDEC =      0.  Trivial = 0.\n"
            "OTCONE 8 \n")                       # killed by the backstop mid-cone
    v = lec.cone_verdicts(text)
    assert v == {3: ("undecided", True), 4: ("proved", False), 5: ("differs", False),
                 6: ("undecided", False), 7: ("proved", False), 8: ("undecided", True)}


def _fake_abc(tmp_path, body):
    p = tmp_path / "fake_abc.py"
    p.write_text("#!/usr/bin/env python3\n" + body)
    p.chmod(p.stat().st_mode | stat.S_IEXEC)
    return str(p)


def test_backstop_keeps_finished_cones(tmp_path, monkeypatch):
    abc = _fake_abc(tmp_path, "import sys, time\n"
                    "print('OTCONE 1 '); print('Networks are equivalent.'); sys.stdout.flush()\n"
                    "print('OTCONE 2 '); sys.stdout.flush(); time.sleep(30)\n")
    monkeypatch.setattr(lec, "CONE_S", 1)
    monkeypatch.setattr(lec, "CONE_WALL_S", 0)
    sf = tmp_path / "b.abc"
    sf.write_text("")
    t = lec.run_cone_batch(abc, sf, 2)              # wall = 2 s
    assert "BATCH WALL BACKSTOP" in t
    assert lec.cone_verdicts(t) == {1: ("proved", False), 2: ("undecided", True)}


def test_prove_time_limit_flow(tmp_path, monkeypatch):
    # 4 outputs, each a wide AND (random simulation never sets it -> 'undecided' after the sweep)
    m = lec.Aig()
    ins = [m.add_input(f"i{k}") for k in range(24)]
    for o in range(4):
        x = ins[o]
        for y in ins[4:]:
            x = m.AND(x, y)
        m.outs.append(x)
        m.onames.append(f"cmp{o}")
    calls = tmp_path / "calls"
    abc = _fake_abc(tmp_path, f"""import sys, re, shutil
calls = open({str(calls)!r}, 'a')
if sys.argv[1] == '-c':
    s = sys.argv[2]
    shutil.copy(re.search(r'&r (\\S+);', s)[1], re.search(r'&w (\\S+)', s)[1])
    print('Undef calls 4')
    sys.exit(0)
for ln in open(sys.argv[2]):
    ln = ln.strip()
    if ln.startswith('echo'):
        print(ln[5:]); continue
    i = int(re.search(r'-O (\\d+);', ln)[1]); opt = '-n' if ' -n -m' in ln else ('x1000' if '-C 100000' in ln else 'x100')
    calls.write(f'{{opt}} {{i}} {{"-T" in ln}}\\n')
    if opt == '-n':   # cone 0 proved, cone 1 differs, cone 2 / 3 time out
        print({{0: 'Networks are equivalent.', 1: 'Networks are NOT EQUIVALENT.'}}.get(i, 'Timed out after 9 seconds.'))
    elif opt == 'x100':  # cone 2 proved by sweeping, cone 3 times out again
        print('Networks are equivalent.' if i == 2 else 'Timed out after 9 seconds.')
    else:
        print('Networks are equivalent.')   # must never be reached for cone 3
""")
    monkeypatch.setattr(lec, "abc_bin", lambda: abc)
    monkeypatch.setattr(lec, "CONE_S", 5)
    log = []
    st = lec.prove(m, tmp_path, 100, log, tag="t")
    assert st == {"cmp0": "proved", "cmp1": "differs", "cmp2": "proved", "cmp3": "undecided"}
    seen = calls.read_text().split("\n")
    assert "x1000 3 True" not in seen and all(x.endswith("True") for x in seen if x)
    assert any("-T 5" in x for x in log)
