import json, sys
import cut_ledger as CL

ROW_OK = """# PROBLEM: hub_Eo reset path 2200 um
import json, sys
p = json.load(open(sys.argv[1])); p["partition_types"]["a"]["x"] = 2; json.dump(p, open(sys.argv[2], "w"))
"""
ROW_BAD = ROW_OK.replace('["a"]', '["b"]')
ROW_FAIL = "import sys; sys.exit(3)\n"
ROW_PART = ROW_OK + 'print("relay_depth matched no sink")\n'
ROW_NOOP = "import shutil, sys; shutil.copy(sys.argv[1], sys.argv[2])\n"


def setup(tmp_path, scripts, listed):
    rd = tmp_path / "rows"; rd.mkdir()
    base = tmp_path / "base.json"; base.write_text(json.dumps({"partition_types": {"a": {"x": 1}, "b": {"y": 1}}}))
    man = []
    for name, src in scripts.items():
        (rd / f"ROWS_{name}.py").write_text(src)
        if name in listed:
            man.append({"owner": name, "script": str(rd / f"ROWS_{name}.py"), "types": ["a"]})
    return base, man, rd


def run(tmp_path, scripts, listed):
    base, man, rd = setup(tmp_path, scripts, listed)
    plan, led = CL.compose(base, tmp_path / "out", man, str(rd))
    return plan, {r["owner"]: r for r in led}


def test_every_status(tmp_path):
    scripts = {"OK": ROW_OK, "BAD": ROW_BAD, "FAIL": ROW_FAIL, "PART": ROW_PART, "NOOP": ROW_NOOP, "LOOSE": ROW_OK}
    plan, led = run(tmp_path, scripts, {"OK", "BAD", "FAIL", "PART", "NOOP"})
    assert {k: v["status"] for k, v in led.items()} == {"OK": "APPLIED", "BAD": "REFUSED", "FAIL": "DROPPED", "PART": "PARTIAL",
                                                        "NOOP": "NOOP", "LOOSE": "UNLISTED"}
    assert led["OK"]["problem"] == "hub_Eo reset path 2200 um"
    assert plan["partition_types"]["b"] == {"y": 1}          # refused row left no trace
    assert "matched no sink" in led["PART"]["reason"]


def test_missing_manifest_script_is_dropped(tmp_path):
    base, man, rd = setup(tmp_path, {"OK": ROW_OK}, {"OK"})
    man.append({"owner": "GONE", "script": str(rd / "ROWS_GONE.py"), "types": ["a"]})
    _, led = CL.compose(base, tmp_path / "o", man, str(rd))
    assert [r["status"] for r in led if r["owner"] == "GONE"] == ["DROPPED"]


def test_cli_ledger_post_and_seal(tmp_path, capsys):
    base, man, rd = setup(tmp_path, {"OK": ROW_OK, "LOOSE": ROW_OK}, {"OK"})
    (tmp_path / "m.json").write_text(json.dumps(man))
    post = tmp_path / "post.sh"; post.write_text('echo "$1|$2" >> %s/posts.txt\n' % tmp_path)
    ld = tmp_path / "ld"
    args = ["--die", "KV", "--event", "D28", "--ledger-dir", str(ld)]
    rc = CL.main(["compose", *args, "--base", str(base), "--out", str(tmp_path / "o"), "--manifest", str(tmp_path / "m.json"),
                  "--rows-dir", str(rd), "--post-cmd", str(post)])
    assert rc == 1
    tsv = (ld / "CUT-LEDGER-KV-D28.tsv").read_text().splitlines()
    assert len(tsv) == 3 and any("UNLISTED" in ln for ln in tsv)         # header + one line per input row
    posts = (tmp_path / "posts.txt").read_text()
    assert posts.count("DROPPED") == 1 and "-> LOOSE" in posts and "Open problem" in posts
    assert CL.main(["seal", *args]) == 5                                 # unacknowledged drop blocks the seal
    assert CL.main(["seal", *args, "--allow-drop", "ROWS_LOOSE.py"]) == 0
    (ld / "CUT-ACK-KV-D28.tsv").write_text("ROWS_LOOSE.py\tLOOSE\tmoved to D29\n")
    assert CL.main(["seal", *args]) == 0                                 # owner ACK also opens it


def test_clean_cut_posts_nothing(tmp_path):
    base, man, rd = setup(tmp_path, {"OK": ROW_OK}, {"OK"})
    (tmp_path / "m.json").write_text(json.dumps(man))
    rc = CL.main(["compose", "--die", "QC", "--event", "V4", "--ledger-dir", str(tmp_path / "l"), "--base", str(base), "--out",
                  str(tmp_path / "o"), "--manifest", str(tmp_path / "m.json"), "--rows-dir", str(rd), "--post-cmd", "/nonexistent"])
    assert rc == 0 and CL.main(["seal", "--die", "QC", "--event", "V4", "--ledger-dir", str(tmp_path / "l")]) == 0
