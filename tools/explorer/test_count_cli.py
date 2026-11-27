import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import count_cli as c


def test_summarize_reports_viewable_against_any_and_current():
    d = {"any_plan": {"total": {"signed": 605, "archived": 605, "viewable": 601, "current": 484, "current_viewable": 484}},
         "any_plan_not_viewable": ["b", "a"], "any_plan_not_archived": []}
    line, nv = c.summarize(d)
    assert "viewable 601/605 any-plan, 484/484 current" in line and "not viewable 2" in line
    assert nv == ["a", "b"]
