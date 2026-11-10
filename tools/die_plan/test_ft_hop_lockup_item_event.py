"""FTLOCK-S81: the per-item ft hop lockup event changes only clock.ft_hop_lockup, names only the given types, and its
dry run flags any changed kit-wave row that is not named."""
import hashlib
import json
import subprocess
import sys
import types
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ft_hop_lockup_item_event as E  # noqa: E402
import gen_rtl  # noqa: E402


def _slot(name, k, w=8):
    return dict(name=name, width=w, stations=k, regs_um=[[100.0 * j, 0.0] for j in range(k)])


def _plan():
    return dict(partition_types=dict(a=dict(ft_slots=[_slot("ft0", 3), _slot("ft1", 1)]),
                                     b=dict(ft_slots=[_slot("ft0", 1)]),
                                     c=dict(ft_slots=[_slot("ft0", 4, 16)])),
                clock=dict(tap_window=dict(window_ps=140), x=1), reset=dict(y=2), lanes=[1])


def test_census_counts_internal_hops_with_epoch():
    c = E.hop_census(_plan(), "a")
    assert (c["slots"], c["hops"], c["latch_bits"]) == (1, 2, 2 * 9)
    assert c["max_hop_um"] == 100.0 and c["max_half_hop_um"] == 50.0
    assert E.hop_census(_plan(), "b")["hops"] == 0


def test_apply_changes_only_the_lockup_list():
    p = _plan()
    out = E.apply(p, ["c", "a", "a"])
    assert out["clock"]["ft_hop_lockup"] == {"types": ["a", "c"]}
    assert out["partition_types"] == p["partition_types"] and out["reset"] == p["reset"] and out["lanes"] == p["lanes"]
    assert {k: v for k, v in out["clock"].items() if k != "ft_hop_lockup"} == p["clock"]
    assert "ft_hop_lockup" not in p["clock"]                       # input untouched
    on = [t for t in out["partition_types"] if gen_rtl.ft_hop_lockup(out, t)]
    assert on == ["a", "c"] and not any(gen_rtl.ft_hop_lockup(p, t) for t in p["partition_types"])


def test_apply_refuses():
    with pytest.raises(ValueError):
        E.apply(_plan(), ["zz"])                                  # not a plan type
    with pytest.raises(ValueError):
        E.apply(_plan(), ["b"])                                   # no internal hop: nothing to latch
    with pytest.raises(ValueError):
        E.apply(_plan(), [])
    p = _plan()
    p["clock"]["ft_hop_lockup"] = {"all": True}
    with pytest.raises(ValueError):
        E.apply(p, ["a"])                                         # die-wide all/except form: edit it explicitly


def test_fragment_forms():
    f = E.fragment({}, ["c", "a"], "latch", plan="/p.json", script="/s.sh", note="n")
    assert f == {"item_inputs": {"a": {"plan": "/p.json", "kit_rtl": {"script": "/s.sh"}, "note": "n"},
                                 "c": {"plan": "/p.json", "kit_rtl": {"script": "/s.sh"}, "note": "n"}}}
    with pytest.raises(ValueError):
        E.fragment({"item_inputs": {"a": {}}}, ["a"], "latch", plan="/p", script="/s")
    h = E.fragment({"type_args": {"a": ["--slew-margin", "50"]}}, ["a"], "hb4", margin=85)
    assert h == {"type_args": {"a": ["--slew-margin", "50", "--hold-ff-margin", "85"]}}
    with pytest.raises(ValueError):
        E.fragment({"type_args": {"a": ["--hold-ff-margin", "5"]}}, ["a"], "hb4", margin=85)
    with pytest.raises(ValueError):
        E.fragment({}, ["a"], "hb4")


def _fake_kit_wave():
    K = types.SimpleNamespace()
    K.core_view_names = lambda names, cv: names
    K.item_key = lambda die, ev, item, block=None: f"{die}|{item}|b{block[:12]}" if block else f"{die}|{ev}|{item}"

    def spec_for(cfg, die, item, hub, parent=None, kind="type"):
        d = cfg["dies"][die]
        ii = (d.get("item_inputs") or {}).get(item) or {}
        return {"item": item, "plan": ii.get("plan") or d["plan"], "kit_rtl": dict(d.get("kit_rtl") or {}, **(ii.get("kit_rtl") or {})),
                "gen_args": list(d.get("gen_args") or []) + list((d.get("type_args") or {}).get(item) or []), "src_sha": d.get("src_sha")}
    K.spec_for = spec_for
    K.input_hash = lambda sp, pk=None: hashlib.sha256(json.dumps({k: v for k, v in sp.items() if k not in ("plan",)},
                                                                 sort_keys=True).encode()).hexdigest()
    return K


def _cfg_state():
    cfg = {"dies": {"s81": {"gen_host": "h", "plan": "/die.json", "event": "e1", "kit_rtl": {"script": "/k.sh"},
                            "gen_args": ["--hold-ff-margin", "0"], "src_sha": "s"}}}
    st = {"plans": {"h:/die.json|e1": {"blocks": {"a": "1" * 64, "b": "2" * 64, "c": "3" * 64}, "types": ["a", "b", "c"]}}}
    return cfg, st


def test_dryrun_only_named_rows_change():
    cfg, st = _cfg_state()
    frag = dict(items=["a"], set=E.fragment(cfg["dies"]["s81"], ["a"], "latch", plan="/ev.json", script="/kl.sh"))
    rep = E.dryrun(_fake_kit_wave(), cfg, st, "s81", frag, "hub")
    assert rep["ok"] and rep["changed"] == ["a"] and rep["key_changed"] == [] and rep["input_hash_changed"] == ["a"]
    assert cfg["dies"]["s81"].get("item_inputs") is None          # the config itself is never edited
    hb = dict(items=["a", "c"], set=E.fragment(cfg["dies"]["s81"], ["a", "c"], "hb4", margin=85))
    rep = E.dryrun(_fake_kit_wave(), cfg, st, "s81", hb, "hub")
    assert rep["ok"] and rep["changed"] == ["a", "c"]


def test_dryrun_flags_unnamed_changes_and_missing_items():
    cfg, st = _cfg_state()
    frag = dict(items=["a"], set={"item_inputs": {"a": {"plan": "/ev.json", "kit_rtl": {"script": "/kl.sh"}},
                                                  "b": {"plan": "/ev.json", "kit_rtl": {"script": "/kl.sh"}}}})
    rep = E.dryrun(_fake_kit_wave(), cfg, st, "s81", frag, "hub")
    assert not rep["ok"] and rep["blockers"] == ["b"]
    rep = E.dryrun(_fake_kit_wave(), cfg, st, "s81", dict(items=["zz"], set={}), "hub")
    assert not rep["ok"] and rep["named_missing"] == ["zz"]


def test_cli_plan_and_blocks(tmp_path):
    pf = tmp_path / "p.json"
    pf.write_text(json.dumps(_plan()))
    r = subprocess.run([sys.executable, str(HERE / "ft_hop_lockup_item_event.py"), "plan", str(pf), str(tmp_path / "o"),
                        "--items", "a", "c", "--note", "t"], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    rec = json.loads((tmp_path / "o" / "receipt.json").read_text())
    out = Path(rec["plan_out"])
    assert hashlib.sha256(out.read_bytes()).hexdigest() == rec["plan_out_sha256"] and out.name.startswith("plan_ftlk_")
    assert rec["lockup_on"] == ["a", "c"] and rec["lockup_on_before"] == [] and rec["pin_cycles_added"] == 0
    assert rec["partition_types_unchanged"] and rec["census"]["c"]["latch_bits"] == 3 * 17
    r = subprocess.run([sys.executable, str(HERE / "ft_hop_lockup_item_event.py"), "blocks", str(pf), str(out),
                        "--out", str(tmp_path / "b.json")], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert json.loads((tmp_path / "b.json").read_text())["changed"] == []   # die-level clock key: no block re-keys
