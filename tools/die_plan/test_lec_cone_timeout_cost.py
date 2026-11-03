"""DIE-HBM-58/LEC gap test for LEC-CONE-TIMEOUT (FLOW-22 9034ba3c4): the hang must be bounded IN PRACTICE, i.e. the
total wall time a prove() spends on hung cones must scale with (number of hung cones) x (per-cone limit), not with
bisection depth x stages.

Measured 11-02 (capped epyc2 probe on the swept AIGs of the hung HBM kits): tailx_sk_step0 x100 batch = 256 cones,
49 cones need > 60 s (10 run to the end: 23-37 min each, all NOT EQUIVALENT); tailx_sk_steady x100 = ~300 cones, all
> 60 s.  ABC's stdout is block-buffered on a pipe, so a killed batch usually returns no partial text (done = []).
With bisection and no per-cone limit inside ABC, each tree node holding a hung cone costs one full wall limit, and the
same hung cones are bisected again at x1000: step0 ~190 timeouts x 600 s ~ 32 h per stage, steady >= 2 x 300 x 600 s
~ 100 h.  This test charges each timed-out call its wall limit and requires
    total <= 3 x hung cones x OT_LEC_CONE_S   (whole prove(), all stages)."""
import re
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parent))
import lec


def test_hung_cone_cost_is_linear_in_hung_cones(tmp_path, monkeypatch):
    N, L = 64, 10.0
    hung = set(range(0, N, 4))                       # 16 hung cones spread over the batch
    monkeypatch.setattr(lec, "xor_sat", lambda *a: {})
    m = lec.Aig()
    x = m.add_input("x")
    m.outs, m.onames = [x] * N, [f"o{i}" for i in range(N)]
    monkeypatch.setattr(lec, "abc_bin", lambda: "fake-abc")
    monkeypatch.setattr(lec, "aig_outputs", lambda p: [2] * N)
    monkeypatch.setattr(lec, "lit_val", lambda *a: 0)
    monkeypatch.setenv("OT_LEC_CONE_S", str(int(L)))
    if hasattr(lec, "CONE_S"):                       # an implementation that reads the limit at import
        monkeypatch.setattr(lec, "CONE_S", int(L))
    charged = []

    def run(args, **kw):
        script = Path(args[-1]).read_text() if args[1] == "-f" else args[-1]
        if "&fraig" in script:
            (tmp_path / "c_swept.aig").touch()
            return SimpleNamespace(stdout=f"Undef calls {N}", stderr="")
        out = []
        for line in script.splitlines():
            if line.startswith("echo "):             # a per-cone marker, if the implementation uses one
                out.append(line[5:])
                continue
            mm = re.search(r"&cone -O (\d+)", line)
            if not mm:
                continue
            i = int(mm[1])
            tl = re.search(r"-T (\d+)", line)
            if i in hung:
                if tl and float(tl[1]) <= L:         # ABC honours its own per-cone limit: cost <= -T (+ one call)
                    charged.append(float(tl[1]))
                    out.append(f"Timed out after {tl[1]} seconds.")
                    continue
                charged.append(kw.get("timeout") or 1e9)   # never returns: killed at the wall limit, text lost
                raise lec.subprocess.TimeoutExpired(args, kw.get("timeout") or 0, output=None)
            out.append("Networks are equivalent")
        return SimpleNamespace(stdout="\n".join(out), stderr="")
    monkeypatch.setattr(lec.subprocess, "run", run)
    st = lec.prove(m, tmp_path, 100, [], tag="c")
    assert all(st[f"o{i}"] == ("undecided" if i in hung else "proved") for i in range(N))
    total = sum(charged)
    assert total <= 3 * len(hung) * L, f"{total:.0f} s on {len(hung)} hung cones (bound {3 * len(hung) * L:.0f} s)"
