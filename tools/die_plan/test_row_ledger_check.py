import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adv_fpconv2 as F2  # noqa: E402
import row_ledger_check as RL  # noqa: E402

PLAN = {"partition_types": {"leaf": {"outline_um": [100, 100]}}}


def ops(tmp, name, val):
    p = tmp / name
    p.write_text(json.dumps({"ops": [{"op": "replace", "path": "/partition_types/leaf/outline_um", "value": val}]}))
    return str(p)


def ledger(tmp, rows):
    p = tmp / "ledger.tsv"
    p.write_text("row_file\tsha256\towner\ttypes\tpre_verdict\tapplied_in_plan_sha\n" + "".join("\t".join(r) + "\n" for r in rows))
    return str(p)


def test_clean_ledger_and_mutants(tmp_path):
    f = ops(tmp_path, "a.json", [100, 100])
    good = [f, F2.sha256_file(f), "FP", "leaf", "PASS", "abc"]
    assert RL.check(PLAN, ledger(tmp_path, [good])) == []
    assert RL.check(PLAN, ledger(tmp_path, []), [f])[0].startswith("WARN ADV-ROW-LEDGER") and "not in the ledger" in RL.check(PLAN, ledger(tmp_path, []), [f])[0]
    bad = list(good); bad[1] = "0" * 64
    assert "ledger sha" in RL.check(PLAN, ledger(tmp_path, [bad]))[0]
    miss = list(good); miss[2] = ""
    assert "lacks owner" in RL.check(PLAN, ledger(tmp_path, [miss]))[0]


def test_unapplied_row_is_not_judged(tmp_path):
    f = ops(tmp_path, "b.json", [999, 999])           # value not in the plan: not applied -> no ledger duty
    assert RL.check(PLAN, ledger(tmp_path, []), [f]) == []
