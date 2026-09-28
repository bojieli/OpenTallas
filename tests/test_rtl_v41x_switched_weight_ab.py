"""Checks for the switched matched source campaign's verdict parser."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def campaign():
    spec = importlib.util.spec_from_file_location("swab", ROOT / "tools/rtl_v41x_switched_weight_ab.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sample(whbm, bad_state=False):
    lines = ["TOK user=0 pos=0 token=2815 cycle=10", "TOK user=1 pos=0 token=1209 cycle=20",
             "TOK user=0 pos=1 token=3537 cycle=30", "TOK user=1 pos=1 token=1918 cycle=40"]
    for node in range(5):
        lines.append(f"NODE node={node} busy=4 side_wait=0 tx_wait=0 starved=0 jobs=4 "
                     f"state_mismatch={int(bad_state and node == 4)}")
        reads = 100 if whbm and node < 3 else 0
        records = 1 if node < 3 else 0
        lines.append(f"HBM_NODE node={node} q_bad=0 q_words={reads} q_reads={reads} q_fault=0 "
                     f"idx_records={records} idx_writes={12*records} idx_read_stalls=0 "
                     "idx_writer_stalls=0 idx_refresh=0")
    lines += ["HDC41_ARRAY nodes=5 users=2 generated=2 mismatches=0 logit_mismatch=0 "
              f"lm_head_checks=8 state_mismatch={int(bad_state)} total_cycles=40",
              "USERS_DONE 2", "LINK_STALLS 0", "PASS"]
    return "\n".join(lines)


def test_switched_parser_checks_all_users_and_package_state():
    c = campaign()
    man = dict(steps_per_user=2, packages=5,
               golden_tokens={"0": [2815, 3537], "1": [1209, 1918]})
    assert c.parse(sample(0), 0, man)["pass_"]
    assert c.parse(sample(1), 1, man)["pass_"]
    assert not c.parse(sample(1, bad_state=True), 1, man)["pass_"]
    assert not c.parse(sample(1).replace("1918", "1919"), 1, man)["pass_"]
