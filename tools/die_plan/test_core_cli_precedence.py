"""Exercise physical CLI parsing and emitted kit fields without running synthesis.

The three older generators build large unrelated RTL/plan inventories before writing
config.mk. Execute their actual parser declarations and output expressions on the
smallest recipe fixture, including a value equal to the historical CLI default.
"""
import argparse
import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
GENERATORS = {
    "kv": ("physical/die_plan/qwen_kvsys/cores/harden/gen_core_kit_kv.py", 0.6),
    "hbm": ("physical/die_plan/hbm/cores/harden/gen_core_kit.py", 0.5),
    "svc": ("physical/die_plan/s81/cores/svc/gen_core_kit_s81.py", 0.5),
}


def emit(name, argv, recipe):
    path, _ = GENERATORS[name]
    tree = ast.parse((ROOT / path).read_text())
    main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    ap = argparse.ArgumentParser()
    for stmt in main.body:
        if (isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call)
                and isinstance(stmt.value.func, ast.Attribute)
                and stmt.value.func.attr == "add_argument" and stmt.value.args
                and isinstance(stmt.value.args[0], ast.Constant)
                and stmt.value.args[0].value in ("--util", "--sigmax")):
            exec(compile(ast.Module(body=[stmt], type_ignores=[]), path, "exec"), {"ap": ap})
    context = {"a": ap.parse_args(argv), "rec": recipe}
    cfg = {}
    for node in ast.walk(main):
        if not isinstance(node, ast.JoinedStr) or not isinstance(node.values[0], ast.Constant):
            continue
        prefix = node.values[0].value
        if prefix not in ("export PLACE_DENSITY = ", "export MAX_ROUTING_LAYER = "):
            continue
        line = eval(compile(ast.Expression(node), path, "eval"), context)
        key, value = line.removeprefix("export ").split(" = ")
        cfg[key] = value
    freeze_layer = next(k.value for node in ast.walk(main) if isinstance(node, ast.Call)
                        for k in node.keywords if k.arg == "signal_max")
    cfg["freeze_signal_max"] = eval(compile(ast.Expression(freeze_layer), path, "eval"), context)
    return cfg


@pytest.mark.parametrize("name", GENERATORS)
@pytest.mark.parametrize("equals", [False, True])
def test_explicit_safe_form_overrides_recipe(name, equals):
    flags = ["--util=0.45", "--sigmax=M7"] if equals else ["--util", "0.45", "--sigmax", "M7"]
    fields = emit(name, flags, {"util": 0.6, "sigmax": "M5"})
    assert fields == {"PLACE_DENSITY": "0.45", "MAX_ROUTING_LAYER": "M7", "freeze_signal_max": "M7"}


@pytest.mark.parametrize("name", GENERATORS)
def test_omitted_density_keeps_recipe(name):
    fields = emit(name, [], {"util": 0.31, "sigmax": "M6"})
    assert fields["PLACE_DENSITY"] == "0.31"
    # KV historically consumes recipe sigmax; HBM/SVC keep their CLI fallback.
    layer = "M6" if name == "kv" else "M5"
    assert fields["MAX_ROUTING_LAYER"] == fields["freeze_signal_max"] == layer


@pytest.mark.parametrize("name", GENERATORS)
def test_explicit_old_default_is_still_an_override(name):
    _, old_default = GENERATORS[name]
    fields = emit(name, ["--util", str(old_default), "--sigmax", "M5"], {"util": 0.31, "sigmax": "M6"})
    assert float(fields["PLACE_DENSITY"]) == old_default
    assert fields["MAX_ROUTING_LAYER"] == fields["freeze_signal_max"] == "M5"


@pytest.mark.parametrize("name", GENERATORS)
def test_no_recipe_uses_historical_fallback(name):
    fields = emit(name, [], {})
    assert float(fields["PLACE_DENSITY"]) == GENERATORS[name][1]
    assert fields["MAX_ROUTING_LAYER"] == fields["freeze_signal_max"] == "M5"
