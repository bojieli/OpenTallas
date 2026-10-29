"""DIE-KV-14d 10-28: KV param_regen hook = the bind-of-record hook (kvbind1025/regen_kv_2350.py, unchanged) + the PV
pair ctl TRUNK_D / FLAG_D from the BOUND (padded) column depths.

The law is the MAIN regen_constants.kv_pv_trunk one, evaluated by kv_pv_col_pads.plan() on the bind's own legs
(landed = bound + R8 pad):  TRUNK_D = TRUNK_D_asb + C,  FLAG_D = max_s(cmd + flag) - k0 - TRUNK_D.
Fail closed: the hook raises (bind PARAM_REGEN error) unless the bind is already equalised, i.e. every PV column command
lands at as-built + C and every column's cmd + flag total is equal per side (the kv_pv_col_pads.py table is in
land_r8_extra).  Without the pads the two parameters cannot describe the die (one check slot for 32 columns)."""
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load(name, f):
    s = importlib.util.spec_from_file_location(name, f)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def pv_trunk(ctx):
    P = _load("kv_pv_col_pads", HERE / "kv_pv_col_pads.py")
    V = P.LegView(ctx)
    law, members = P.plan(V)
    owed = {k: (r["cmd_pad"], r["flag_pad"]) for k, r in law["columns"].items() if r["cmd_pad"] or r["flag_pad"]}
    if owed:
        raise ValueError(f"PV columns not equalised ({len(owed)} of {len(law['columns'])} owe pads, e.g. "
                         f"{dict(list(owed.items())[:4])}): add kv_pv_col_pads.py output to land_r8_extra")
    params = {p: {"TRUNK_D": law["TRUNK_D"], "FLAG_D": law["FLAG_D"]} for p in sorted(V.ctl)}
    return params, {k: law[k] for k in ("TRUNK_D_asb", "FLAG_D_asb", "C", "TRUNK_D", "FLAG_D", "k0")}


def regen(ctx):
    base = _load("kv_regen_2350", HERE.parent / "bind/kvbind1025/regen_kv_2350.py")
    r = base.regen(ctx)
    p, rec = pv_trunk(ctx)
    base._merge(r["params"], p, "pv_trunk")
    r["record"]["pv_trunk"] = dict(rec, rule="regen_constants.kv_pv_trunk law on the padded bind (kv_pv_col_pads.py)")
    r["record"]["hook"] = "physical/die_plan/qwen_kvsys/r8/kv_pv_col_regen.py"
    return r
