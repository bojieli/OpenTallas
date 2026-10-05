"""Layer-parallel tool: the audited host is a pure addition to the pinned host, and plans chain golden exits."""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import qwen_rom_layer_parallel_sim as L  # noqa: E402

PINNED = ROOT / L.HOST_CPP


def test_every_anchor_applies_once_and_pinned_host_is_untouched():
    before = PINNED.read_bytes()
    text = PINNED.read_text()
    for anchor, _ in L.AUDIT_EDITS:
        assert text.count(anchor) == 1, anchor[:60]
    gen = L.emit_host(text)
    assert PINNED.read_bytes() == before
    assert len(re.findall(r"lp_rd\(lp_vm_w, lp_vm_r, d, a, [0-4]\);", gen)) == 5         # va, vb, vc, x-chunk, sequencer reads
    assert "lp_rd(lp_kv_w, lp_kv_r, d, a * W + j, 5)" in gen
    assert 'printf("DEP stage=' in gen and 'printf("DRAIN stage=' in gen


def test_audit_is_runtime_gated_and_removing_it_restores_the_pinned_statements():
    gen = L.emit_host(PINNED.read_text())
    assert 'getenv("RT_DEP_AUDIT")' in gen
    # every inserted read hook is guarded by lp_audit inside lp_rd; strip hooks and the remaining read lines match
    stripped = re.sub(r"lp_rd\(lp_vm_w, lp_vm_r, d, a, [0-4]\); ", "", gen)
    for line in PINNED.read_text().splitlines():
        if "? m.vm[a] : 0;" in line:
            assert line in stripped
    # the last stage returns exactly as before when the audit is off
    assert "if (!lp_audit) return 0;" in gen


def test_plan_chains_golden_exits(tmp_path):
    orc = tmp_path / "oracle"
    orc.mkdir()
    (orc / "oracle.json").write_text(json.dumps({"next_token": 7, "next_logit_bits": "3f800000"}))
    for n in range(2):
        for d in range(2):
            (orc / f"L{n:02d}_die{d}_x.hex").write_text("".join(f"{(n * 4096 + i):08x}\n" for i in range(4096)))
    pre = tmp_path / "preload.hex"
    pre.write_text("@1000\n" + "00000000\n" * 4096)
    st = tmp_path / "stages.txt"
    st.write_text("L0 /a/L0-d0 /a/L0-d1 1\nL1 /a/L1-d0 /a/L1-d1 1\nhead /a/h0 /a/h1 0\n")
    fleet = tmp_path / "fleet.json"
    fleet.write_text(json.dumps({"hosts": [{"name": "h", "ssh": None, "binary": "/bin/true", "workroot": str(tmp_path / "w"),
                                            "slots": 8, "threads": 1}]}))
    pd = tmp_path / "plan"
    subprocess.run([sys.executable, str(ROOT / "tools/qwen_rom_layer_parallel_sim.py"), "--plan", "--plan-dir", str(pd),
                    "--stages", str(st), "--oracle", str(orc), "--preload", str(pre), "--fleet", str(fleet),
                    "--pairs", "head"], check=True, capture_output=True)
    plan = json.loads((pd / "plan.json").read_text())
    names = [j["name"] for j in plan["jobs"]]
    assert sorted(names) == ["L0", "L1", "head", "head+pair"]
    head = (pd / "jobs/head/entry.hex").read_text().split()
    assert head[0] == "@1000" and int(head[1], 16) == 4096                # golden L1 exit enters the head
    assert (pd / "jobs/L0/entry.hex").read_bytes() == pre.read_bytes()
    pair = next(j for j in plan["jobs"] if j["name"] == "head+pair")
    assert [s["entered_by"] for s in pair["stages"]] == ["wrapper_start", "host_h_start"]
    assert (pd / "jobs/head+pair/entry.hex").read_text().split()[1] == "00000000"   # golden L0 exit enters L1
