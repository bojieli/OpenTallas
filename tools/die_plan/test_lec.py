"""lec.py (LEC lane 10-24): RTL vs synthesised-netlist logic equivalence check, run by run_kit.sh after synth.
    python3 -m pytest -q tools/die_plan/test_lec.py
The integration tests run lec.py on the csa31 fixture (examples/lec_csa31: the 10-24 slang out-of-range select
bug, synthesised by ORFS with the slang frontend) and need docker + the ORFS image; the rest is pure python."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lec  # noqa: E402

FX = HERE / "examples" / "lec_csa31"


# ------------------------------------------------------------------------------------------------ pure python
def test_flop_key_polarity_and_names():
    # gold: the techmap keep wire of a yosys $_DFF_P_; gate: an ASAP7 flop stores IQN = !D
    assert lec.flop_key("u_dut.a.q[3]$_DFF_P_.lecq") == ("u_dut.a.q[3]", False)
    assert lec.flop_key("u_dut.a.q[3]$_DFF_P_.IQN$_DFF_P_.lecq") == ("u_dut.a.q[3]", True)
    assert lec.flop_key("u_dut.a.r[0]$_DFF_PN0_.IQN$_DFFSR_PPP_.lecq") == ("u_dut.a.r[0]", True)


def test_genblk_scopes_are_dropped():
    assert lec.GENBLK.sub("", "u_dut.u_s.genblk1.genblk1.g_l5.genblk12.r[0]") == "u_dut.u_s.g_l5.r[0]"
    assert lec.GENBLK.sub("", "genblk2.a.mygenblk1.b") == "a.mygenblk1.b"


def test_aig_strash_simulate_and_roundtrip(tmp_path):
    m = lec.Aig()
    a, b = m.add_input("a"), m.add_input("b")
    x = m.XOR(a, b)
    assert m.AND(a, b) == m.AND(b, a)                    # structural hashing
    assert m.AND(a, a ^ 1) == 0 and m.AND(a, 1) == a     # trivial cases
    m.outs, m.onames = [x, m.XOR(x, m.XOR(a, b))], ["x", "zero"]
    val, mask = m.simulate(2, seed=3)
    assert lec.lit_val(val, mask, m.outs[1]) == 0
    assert lec.lit_val(val, mask, x) == lec.lit_val(val, mask, a) ^ lec.lit_val(val, mask, b)
    p = tmp_path / "m.aig"
    m.write(p)
    r = lec.read_aig(p)
    assert r["I"] == 2 and r["O"] == 2 and lec.aig_outputs(p)[1] == 0
    assert m.cone_inputs(x) == {a >> 1, b >> 1}


def test_array_maps_relates_the_two_frontend_layouts():
    # read_verilog: mem[i][bit] (4 x 3 bits); slang + ORFS: mem[h][flat] with flat = i * 3 + bit, split in halves
    g = [f"ff:t.m[{i}][{b}]" for i in range(4) for b in range(3)]
    t = [f"ff:t.m#t[{h}][{k}]" for h in range(2) for k in range(6)]
    maps = lec.array_maps(g, t)["ff:t.m"]
    assert {"ff:t.m[0][0]": "ff:t.m#t[0][0]", "ff:t.m[2][1]": "ff:t.m#t[1][1]",
            "ff:t.m[3][2]": "ff:t.m#t[1][5]"}.items() <= maps[0].items()
    assert len(maps) >= 2                                # outer-index reversed variants too


def test_merged_copy_pairs_with_its_own_name_shape():
    c = ["ff:u.g_ctl[1].u_c.g_c[0].f[0]", "ff:u.g_ctl[0].u_c.g_c[0].f[1]", "ff:u.g_ctl[0].u_c.g_c[0].f[0]"]
    assert lec.closest("ff:u.g_ctl[0].u_c.g_c[10].f[0]", c)[0] == "ff:u.g_ctl[0].u_c.g_c[0].f[0]"


def _sim_prove(m, *a, **k):
    """stand-in for ABC in pure-python tests: 1024 random patterns (enough for these tiny cones)."""
    val, mask = m.simulate(16, seed=12345)
    return {n: ("proved" if lec.lit_val(val, mask, o) == 0 else "differs") for n, o in zip(m.onames, m.outs)}


def _design(tmp_path, merged):
    """a 2-flop shift register (gold) vs gate: same, or with the second flop renamed (`merged`)."""
    def aig_and_map(names):
        # binary AIGER: input d = var 1, latches q0 / q1 = vars 2 / 3; next-state literals d and q0
        p = tmp_path / f"{names[1]}.aig"
        I, L = 1, 2
        hdr = f"aig {I + L} {I} {L} 0 0\n".encode()
        body = f"{2}\n{4}\n".encode()                   # q0' = d, q1' = q0
        p.write_bytes(hdr + body)
        mp = {"input": {0: [("d", 0)]}, "latch": {0: [(f"u_dut.{names[0]}$_DFF_P_.lecq", 0)],
                                                   1: [(f"u_dut.{names[1]}$_DFF_P_.lecq", 0)]}, "output": {}}
        return lec.read_aig(p), mp
    g, gm = aig_and_map(("q0", "q1"))
    t, tm = aig_and_map(("q0", "q1x" if merged else "q1"))
    return lec.Lec(g, gm, t, tm)


def test_correspondence_pairs_a_renamed_register(tmp_path, monkeypatch):
    monkeypatch.setattr(lec, "prove", _sim_prove)
    L = _design(tmp_path, merged=True)
    assert L.gonly == ["ff:u_dut.q1"] and L.tonly == ["ff:u_dut.q1x"]
    lec.correspond(L, tmp_path, 100, [])
    assert L.hyp[("gate", "ff:u_dut.q1x")] == ("eq", "gold", "ff:u_dut.q1", 0)
    m, kind = L.build(with_compare=True, with_hyp=True)
    assert set(_sim_prove(m).values()) == {"proved"}


def test_rtl_x_is_a_dont_care(tmp_path, monkeypatch):
    """gold q' = d | X (an out-of-range select): gate q' = 1 refines it (equal wherever the RTL is not X),
    gate q' = 0 does not (d = 1)."""
    monkeypatch.setattr(lec, "prove", _sim_prove)
    g = tmp_path / "g.aig"
    g.write_bytes(b"aig 4 2 1 0 1\n9\n" + bytes([3, 2]))            # inputs d, x; q' = !(!d & !x)
    gm = {"input": {0: [("d", 0)]}, "latch": {0: [("u_dut.q$_DFF_P_.lecq", 0)]}, "output": {}}
    for nxt, want in ((1, "proved"), (0, "differs")):
        t = tmp_path / f"t{nxt}.aig"
        t.write_bytes(f"aig 2 1 1 0 0\n{nxt}\n".encode())
        tm = {"input": {0: [("d", 0)]}, "latch": {0: [("u_dut.q$_DFF_P_.lecq", 0)]}, "output": {}}
        L = lec.Lec(lec.read_aig(g), gm, lec.read_aig(t), tm)
        assert L.gx and "ff:u_dut.q" in L.matched
        m, kind = L.build(with_compare=True, with_hyp=False)
        assert _sim_prove(m)["ff:u_dut.q"] == want


# ------------------------------------------------------------------------------------------------ integration
def _have_image():
    if not shutil.which("docker"):
        return False
    r = subprocess.run(["docker", "image", "inspect", lec.IMAGE], capture_output=True)
    return r.returncode == 0


def _kit(tmp_path, rtl, netlist):
    k = tmp_path / Path(rtl).stem
    (k / "rtl").mkdir(parents=True)
    shutil.copyfile(FX / "lec_bbx.v", k / "rtl" / "lec_bbx.v")
    shutil.copyfile(FX / rtl, k / "rtl" / "lec_t1.sv")
    n = k / "run" / "results" / "asap7" / "lec_t1" / "base"
    n.mkdir(parents=True)
    shutil.copyfile(FX / netlist, n / "1_2_yosys.v")
    (k / "config.mk").write_text(
        "export DESIGN_NAME = lec_t1\nexport PLATFORM = asap7\n"
        "export VERILOG_FILES = /work/rtl/lec_bbx.v /work/rtl/lec_t1.sv\nexport VERILOG_INCLUDE_DIRS = /work/rtl\n"
        "export VERILOG_DEFINES = -DSYNTHESIS\nexport SYNTH_HDL_FRONTEND = slang\nexport SYNTH_BLACKBOXES = lec_bbx\n")
    return k


def _run(kit):
    r = subprocess.run([sys.executable, str(HERE / "lec.py"), str(kit), "--mem", "4"], capture_output=True,
                       text=True, timeout=900)
    return r.returncode, json.loads((kit / "lec" / "lec.json").read_text())


@pytest.mark.skipif(not _have_image(), reason="needs docker + the ORFS image")
def test_csa31_bug_is_not_equivalent(tmp_path):
    """the pre-fix RTL synthesised by the slang frontend drops y[30:24]: LEC names exactly those outputs."""
    rc, r = _run(_kit(tmp_path, "lec_t1_pre.sv", "netlist_pre.v"))
    assert rc == 1 and r["verdict"] == "NOT EQUIVALENT", r
    assert sorted(e["point"] for e in r["failing"]) == [f"po:y[{i}]" for i in range(24, 31)]
    assert r["gold_frontend"] == "verilog" and r["synth_frontend"] == "slang"


@pytest.mark.skipif(not _have_image(), reason="needs docker + the ORFS image")
def test_csa31_fix_is_equivalent(tmp_path):
    """fixed RTL (zero-extended operands) + its netlist: every compare point proved, black box pins matched."""
    rc, r = _run(_kit(tmp_path, "lec_t1_fix.sv", "netlist_fix.v"))
    assert rc == 0 and r["verdict"] == "EQUIVALENT", r
    assert r["black_boxes"] == {"lec_bbx": 3} and r["counts"]["differs"] == 0


def test_run_kit_runs_lec_after_face_guard_and_fails_closed():
    import gen_phys
    s = gen_phys.RUN_KIT
    assert s.index("face_guard_odb.json") < s.index("/work/lec.py") < s.index("\\$M $GOAL")
    seg = s.split("/work/lec.py", 1)[1].split("fi; fi;")[0]
    assert "if [ \\$lr = 1 ]; then" in seg and "FAIL_PREFLOOR LEC NOT EQUIVALENT" in seg and "rc=5" in seg
    assert s.index("/work/lec.py") < s.index("\\$M cts")      # NOT EQUIVALENT stops before floorplan/CTS


def test_correspondence_proves_feedback_copies_together(tmp_path, monkeypatch):
    """Two duplicated feedback registers: each frontend chooses a different copy for the feedback.
    Their equality is inductive, although no individual next-state compare holds with the copies free.
    """
    monkeypatch.setattr(lec, 'prove', _sim_prove)
    def side(name, feedback):
        m = lec.Aig()
        d, a, b = (m.add_input(x) for x in ('d', 'a', 'b'))
        nxt = m.XOR((a, b)[feedback], d)
        f = tmp_path / (name + '.aig')
        m.write(f)
        _, body = f.read_bytes().split(b'\n', 1)
        f.write_bytes(f'aig {m.ni + len(m.ands)//2} 1 2 0 {len(m.ands)//2}\n{nxt}\n{nxt}\n'.encode() + body)
        mp = {'input': {0: [('d', 0)]}, 'latch': {0: [('u_dut.a$_DFF_P_.lecq', 0)],
              1: [('u_dut.b$_DFF_P_.lecq', 0)]}, 'output': {}}
        return lec.read_aig(f), mp
    g, gm = side('gold', 0)
    t, tm = side('gate', 1)
    L = lec.Lec(g, gm, t, tm)
    before, _ = L.build(with_compare=True, with_hyp=False)
    assert set(_sim_prove(before).values()) == {'differs'}
    lec.correspond(L, tmp_path, 100, [])
    assert any(sd == 'both' and h[0] == 'eq' for (sd, k), h in L.hyp.items())
    after, _ = L.build(with_compare=True, with_hyp=True)
    assert set(_sim_prove(after).values()) == {'proved'}


def test_replica_candidates_keep_input_identity_and_prove_both_sides(tmp_path, monkeypatch):
    monkeypatch.setattr(lec, 'prove', _sim_prove)
    def design(name, second):
        p = tmp_path / (name + '.aig')
        p.write_bytes(f'aig 4 2 2 0 0\n2\n{second}\n'.encode())
        mp = {'input': {0: [('d0', 0)], 1: [('d1', 0)]},
              'latch': {i: [(f'u_dut.g_copy[{i}].q$_DFF_P_.lecq', 0)] for i in range(2)}, 'output': {}}
        return lec.read_aig(p), mp
    for gold_second, gate_second, want_pair, want_result in ((4, 4, False, 'proved'),
                                                            (2, 2, True, 'proved'),
                                                            (2, 4, True, 'differs')):
        g, gm = design('gold', gold_second)
        t, tm = design('gate', gate_second)
        L = lec.Lec(g, gm, t, tm)
        lec.replica_proposals(L, [])
        assert bool(L.hyp) == want_pair
        lec.correspond(L, tmp_path, 100, [])
        m, _ = L.build(with_compare=True, with_hyp=True)
        assert want_result in set(_sim_prove(m).values())


def test_parallel_cones_preserve_each_status(tmp_path, monkeypatch):
    import re
    from types import SimpleNamespace
    m = lec.Aig()
    x = m.add_input('x')
    m.outs, m.onames = [x, x], ['equivalent_cone', 'different_cone']
    monkeypatch.setattr(lec, 'abc_bin', lambda: 'fake-abc')
    monkeypatch.setattr(lec, 'aig_outputs', lambda p: [2, 2])
    monkeypatch.setattr(lec, 'lit_val', lambda *args: 0)  # neither leftover is resolved by simulation
    monkeypatch.setattr(lec, 'PROVE_JOBS', 2)
    def run(args, **kwargs):
        script = Path(args[-1]).read_text() if args[1] == "-f" else args[-1]   # single cones: abc -f script file
        if '&fraig' in script:
            (tmp_path / 'parallel_swept.aig').touch()
            return SimpleNamespace(stdout='Undef calls 2', stderr='')
        ids = [int(i) for i in re.findall(r'&cone -O (\d+)', script)]
        return SimpleNamespace(stdout='\n'.join('Networks are equivalent' if i == 0 else 'Networks are NOT EQUIVALENT' for i in ids), stderr='')
    monkeypatch.setattr(lec.subprocess, 'run', run)
    assert lec.prove(m, tmp_path, 100, [], tag='parallel') == {'equivalent_cone': 'proved', 'different_cone': 'differs'}


def test_naive_cone_unknown_does_not_shift_later_status(tmp_path, monkeypatch):
    import re
    from types import SimpleNamespace
    m = lec.Aig()
    x = m.add_input('x')
    m.outs, m.onames = [x, x, x], ['unknown', 'proved', 'different']
    monkeypatch.setattr(lec, 'abc_bin', lambda: 'fake-abc')
    monkeypatch.setattr(lec, 'aig_outputs', lambda p: [2, 2, 2])
    monkeypatch.setattr(lec, 'lit_val', lambda *args: 0)
    monkeypatch.setattr(lec, 'PROVE_JOBS', 1)  # mixed statuses in one serial batch
    def run(args, **kwargs):
        script = Path(args[-1]).read_text() if args[1] == "-f" else args[-1]   # single cones: abc -f script file
        if '&fraig' in script:
            (tmp_path / 'mixed_swept.aig').touch()
            return SimpleNamespace(stdout='Undef calls 3', stderr='')
        assert '&cec -n -m' in script or '&cec -m' in script     # naive pass, then SAT-sweeping escalation
        ids = [int(i) for i in re.findall(r'&cone -O (\d+)', script)]
        replies = ['UNSAT = 0. SAT = 0. UNDEC = 1. Trivial = 0.',
                   'Networks are equivalent. Time = 0.0 sec',
                   'UNSAT = 0. SAT = 1. UNDEC = 0. Trivial = 0.']
        return SimpleNamespace(stdout='\n'.join(replies[i] for i in ids), stderr='')
    monkeypatch.setattr(lec.subprocess, 'run', run)
    assert lec.prove(m, tmp_path, 100, [], tag='mixed') == {'unknown': 'undecided', 'proved': 'proved', 'different': 'differs'}


def _seq(tmp_path, name, inputs, latches, nxt_fn):
    """a sequential AIG: primary `inputs`, `latches` (names); nxt_fn(m, lits) -> next-state literal per latch."""
    m = lec.Aig()
    lits = {n: m.add_input(n) for n in list(inputs) + list(latches)}
    nxt = nxt_fn(m, lits)
    f = tmp_path / (name + ".aig")
    m.write(f)
    _, body = f.read_bytes().split(b"\n", 1)
    A = len(m.ands) // 2
    hdr = f"aig {m.ni + A} {len(inputs)} {len(latches)} 0 {A}\n" + "".join(f"{nxt[l]}\n" for l in latches)
    f.write_bytes(hdr.encode() + body)
    mp = {"input": {i: [(n, 0)] for i, n in enumerate(inputs)},
          "latch": {i: [(f"u_dut.{n}$_DFF_P_.lecq", 0)] for i, n in enumerate(latches)}, "output": {}}
    return lec.read_aig(f), mp


def test_merged_self_holding_copy_is_paired_on_its_care_set(tmp_path, monkeypatch):
    """PATH-KV-PC3 10-25 (ot_qfd_emb_pcport `if (r_v) begin kv_d <= r_d; c1 <= r_d; end`): synthesis merged the
    load-enable twin kv_d into c1.  D(kv_d) holds kv_d, which c1 does not share, so no plain / cofactor signature
    pairs them and every compare point fed by kv_d differed (987 points NOT EQUIVALENT).  care_pairs pairs them on
    the enabled patterns and the induction proves it."""
    monkeypatch.setattr(lec, "prove", _sim_prove)
    hold = lambda m, e, d, q: m.AND(m.AND(e, d) ^ 1, m.AND(e ^ 1, q) ^ 1) ^ 1           # e ? d : q
    g, gm = _seq(tmp_path, "gold", ["d", "e"], ["kv_d", "c1", "o"],
                 lambda m, l: {"kv_d": hold(m, l["e"], l["d"], l["kv_d"]), "c1": hold(m, l["e"], l["d"], l["c1"]),
                               "o": m.XOR(l["kv_d"], l["d"])})
    t, tm = _seq(tmp_path, "gate", ["d", "e"], ["c1", "o"],
                 lambda m, l: {"c1": hold(m, l["e"], l["d"], l["c1"]), "o": m.XOR(l["c1"], l["d"])})
    L = lec.Lec(g, gm, t, tm)
    assert L.gonly == ["ff:u_dut.kv_d"] and not L.tonly
    before, _ = L.build(with_compare=True, with_hyp=False)
    assert _sim_prove(before)["ff:u_dut.o"] == "differs"
    lec.correspond(L, tmp_path, 100, [])
    assert L.hyp[("gold", "ff:u_dut.kv_d")] == ("eq", "gold", "ff:u_dut.c1", 0)
    after, _ = L.build(with_compare=True, with_hyp=True)
    assert set(_sim_prove(after).values()) == {"proved"}
    # a different enable is no copy: never proved
    g2, gm2 = _seq(tmp_path, "gold2", ["d", "e", "f"], ["kv_d", "c1", "o"],
                   lambda m, l: {"kv_d": hold(m, l["f"], l["d"], l["kv_d"]), "c1": hold(m, l["e"], l["d"], l["c1"]),
                                 "o": m.XOR(l["kv_d"], l["d"])})
    t2, tm2 = _seq(tmp_path, "gate2", ["d", "e", "f"], ["c1", "o"],
                   lambda m, l: {"c1": hold(m, l["e"], l["d"], l["c1"]), "o": m.XOR(l["c1"], l["d"])})
    L2 = lec.Lec(g2, gm2, t2, tm2)
    lec.correspond(L2, tmp_path, 100, [])
    m2, _ = L2.build(with_compare=True, with_hyp=True)
    assert _sim_prove(m2)["ff:u_dut.o"] == "differs"


def test_kept_register_merged_by_synthesis_fails(tmp_path):
    """fail-closed kept-register check: a (* keep *) copy (or a keep_hierarchy pin flop) merged into its twin is
    LEC-equivalent but must FAIL; the intact netlist passes (mutant test)."""
    keep = tmp_path / "gold.keep"
    keep.write_text("lec_top/u_dut.cp\n" "lec_top/u_dut.u_pin.q\n" "lec_top/lec_po_x\n")
    gold_l = ["cp[0]", "cp[1]", "u_pin.q", "plain"]
    nx = lambda m, l: {n: l["d"] for n in l if n != "d"}
    g, gm = _seq(tmp_path, "g", ["d"], gold_l, nx)
    for gate_l, want in ((gold_l, []), (["cp[0]", "u_pin.q"], ["ff:u_dut.cp[1]"]),
                         (["cp[0]", "cp[1]"], ["ff:u_dut.u_pin.q"])):
        t, tm = _seq(tmp_path, "t", ["d"], gate_l, nx)
        L = lec.Lec(g, gm, t, tm)
        declared, missing, const = lec.kept_registers(L, keep)
        assert declared == ["ff:u_dut.cp[0]", "ff:u_dut.cp[1]", "ff:u_dut.u_pin.q"] and missing == want and not const
        if want:                                     # the merged copy, paired by correspondence: still missing
            L.hyp[("gold", want[0])] = ("eq", "gold", "ff:u_dut.cp[0]", 0)
            assert lec.kept_registers(L, keep)[1] == want
            L.hyp[("gold", want[0])] = ("const", 0)  # proved constant: reported, not failed
            assert lec.kept_registers(L, keep)[1:] == ([], want)


def test_gold_script_marks_kept_registers():
    s = lec.gold_script({"VERILOG_FILES": "a.v", "DESIGN_NAME": "t"}, "/k", "verilog", [], "s.v", "w.v", "f.v", "/o/gold")
    assert s.index("a:keep %i") < s.index("setattr -mod -unset keep_hierarchy")
    assert "A:keep_hierarchy" in s and "select -write /o/gold.keep" in s


def _exact_prove(m, *a, **k):
    """exhaustive stand-in for ABC (every input pattern; small test designs only): exact, unlike _sim_prove,
    so a rare event that random simulation never excites is still seen."""
    n = m.ni
    assert n <= 20
    W = 1 << n
    mask = (1 << W) - 1
    val = [0] * (n + len(m.ands) // 2 + 1)
    for v in range(1, n + 1):
        blk = 1 << (v - 1)
        pat = ((1 << blk) - 1) << blk                    # 0..0 1..1 repeated: input bit v-1 of the pattern index
        rep = 0
        for s in range(0, W, 2 * blk):
            rep |= pat << s
        val[v] = rep & mask
    for k in range(len(m.ands) // 2):
        r0, r1 = m.ands[2 * k], m.ands[2 * k + 1]
        val[n + 1 + k] = lec.lit_val(val, mask, r0) & lec.lit_val(val, mask, r1)
    return {nm: ("proved" if lec.lit_val(val, mask, o) == 0 else "differs") for nm, o in zip(m.onames, m.outs)}


def test_hint_pairs_a_rare_event_twin_and_a_wrong_hint_is_dropped(tmp_path, monkeypatch):
    """PATH-KV-PC4 10-25 (ot_qkd_static_kv_timing with REF_MODE=1: the row opcode is PRE 0 / ACT 1 / REFPB 6, so
    c_op[2] == c_op[1]; synthesis merged the twins c_op[2] -> c_op[1], row_op[2] -> row_op[1]).  Both bits are set
    only by a refresh, which random simulation never excites: their signatures look constant, the constant hypothesis
    fails the proof and no partner is ever proposed, so every consumer of row_op[2] differed (591 points).  A hint
    pairs them and the same induction proves it; a wrong hint (inverted) is dropped, never a waiver."""
    monkeypatch.setattr(lec, "prove", _exact_prove)
    ins = [f"a{i}" for i in range(14)]

    def rare(m, l):
        r = l["a0"]
        for i in ins[1:]:
            r = m.AND(r, l[i])
        return r                                          # 1 in 16384 patterns
    g, gm = _seq(tmp_path, "gold", ins, ["c1", "c2", "o"],
                 lambda m, l: {"c1": rare(m, l), "c2": rare(m, l), "o": m.XOR(l["c2"], l["a0"])})
    t, tm = _seq(tmp_path, "gate", ins, ["c1", "o"],
                 lambda m, l: {"c1": rare(m, l), "o": m.XOR(l["c1"], l["a0"])})
    for hint, want in (([["gold", "ff:u_dut.c2", ["eq", "gold", "ff:u_dut.c1", 0]]], "proved"),
                       ([["gold", "ff:u_dut.c2", ["eq", "gold", "ff:u_dut.c1", 1]]], "differs"),
                       ([["gold", "ff:u_dut.c2", ["const", 0]]], "differs"),
                       ([["gold", "ff:u_dut.nope", ["eq", "gold", "ff:u_dut.c1", 0]]], "differs")):
        L = lec.Lec(g, gm, t, tm)
        assert L.gonly == ["ff:u_dut.c2"] and not L.tonly
        sig, mask = L.build(with_compare=False, with_hyp=False)[0].simulate(16, seed=7)
        assert lec.lit_val(sig, mask, L.dlit[("gold", "ff:u_dut.c2")]) == 0      # looks constant to the signatures
        r = lec.apply_hints(L, hint, tmp_path, 100, [])
        m, _ = L.build(with_compare=True, with_hyp=True)
        assert _exact_prove(m)["ff:u_dut.o"] == want
        if want == "proved":
            assert r["applied"] == 1 and not r["dropped"] and L.hyp[("gold", "ff:u_dut.c2")][2] == "ff:u_dut.c1"
        elif "nope" in hint[0][1]:
            assert r["skipped"] and not r["applied"]
        else:
            assert r["dropped"] == ["ff:u_dut.c2"] and ("gold", "ff:u_dut.c2") not in L.hyp


def test_hints_are_read_from_the_kit_and_passed_into_the_image():
    s = Path(lec.__file__).read_text()
    assert 'Path(kit) / "lec_hints.json"' in s and '"--hints", "/lecout/hints.json"' in s


def test_undecided_naive_cone_escalates_to_sat_sweeping(tmp_path, monkeypatch):
    """PATH-KV-PC4 10-25: an ECC XOR cone naive SAT cannot finish (UNDEC) is retried with &cec -m (SAT sweeping
    inside the cone), where it is proved; a cone every pass leaves open stays undecided (never 'proved')."""
    import re
    from types import SimpleNamespace
    m = lec.Aig()
    x = m.add_input('x')
    m.outs, m.onames = [x, x], ['xor_tree', 'hard']
    monkeypatch.setattr(lec, 'abc_bin', lambda: 'fake-abc')
    monkeypatch.setattr(lec, 'aig_outputs', lambda p: [2, 2])
    monkeypatch.setattr(lec, 'lit_val', lambda *args: 0)
    monkeypatch.setattr(lec, 'PROVE_JOBS', 1)
    seen = []
    def run(args, **kwargs):
        script = Path(args[-1]).read_text() if args[1] == "-f" else args[-1]
        if '&fraig' in script:
            (tmp_path / 'esc_swept.aig').touch()
            return SimpleNamespace(stdout='Undef calls 2', stderr='')
        out = []
        for line in script.splitlines():
            i = int(re.search(r'&cone -O (\d+)', line)[1])
            naive = '&cec -n -m' in line
            seen.append((i, naive))
            out.append('UNSAT = 0. SAT = 0. UNDEC = 1. Trivial = 0.' if naive or i == 1 else
                       'Networks are equivalent. Time = 1.2 sec')
        return SimpleNamespace(stdout='\n'.join(out), stderr='')
    monkeypatch.setattr(lec.subprocess, 'run', run)
    assert lec.prove(m, tmp_path, 100, [], tag='esc') == {'xor_tree': 'proved', 'hard': 'undecided'}
    assert (0, True) in seen and (0, False) in seen and seen.count((0, False)) == 1   # proved once: not retried
