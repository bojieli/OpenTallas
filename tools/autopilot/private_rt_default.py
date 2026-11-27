"""private_rt_default: private-spec runtime pin when no --rt is given (P-RUNTIME-MANIFEST, S81-INT-R3-PARAM 11-27).

Observed on S81 c085 (11-27): `kit_wave.py private-spec ... --tree T` without --rt silently took the TREE'S OWN tools ("RT-FLOOR UNKNOWN: no rt
pin").  T's tools/die_plan/schema.py predated the plan (no ft_polarity_local_group_by_type), so leaf probes died in gen phys (schema error) and
kit_istations.  Two rules, both stdlib + plan_gate_pre's own schema probe:

  event_rt(cfg, die)          the rt sha the die's event was bound on (kit_wave.json dies[die].tools_sha, == tree_switch_*.json
                              config.tools_sha): private-spec defaults to it when neither --rt nor the bind stamp picked one;
  tree_tools_refusal(sp, plan) '' or a refusal text when the spec still runs the tree's own tools and that tree's schema.py does not know
                              a key of the plan (SCHEMA-UNKNOWN-KEY: tree tools older than the plan schema).  Only a declared rt, an
                              explicit --rt-floor-exempt, or a sealed gen_tools_pin tree (gen_tools_manifest_sha) is let through."""
import re
import sys
from pathlib import Path


def event_rt(cfg, die):
    v = str((((cfg or {}).get("dies") or {}).get(die) or {}).get("tools_sha") or "").strip().lower()
    return v if re.fullmatch(r"[0-9a-f]{12,40}", v) else ""


def uses_tree_tools(sp):
    return not sp.get("tools_sha") and not sp.get("gen_tools_manifest_sha")


def tree_tools_refusal(sp, plan, exempt="", check_schema=None):
    if not uses_tree_tools(sp) or str(exempt or "").strip():
        return ""
    tree, plan = sp.get("src"), plan or sp.get("plan")
    if not tree or not plan:
        return ""
    if check_schema is None:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "die_plan"))
        import plan_gate_pre
        check_schema = plan_gate_pre.check_schema
    bad = [x for x in check_schema(str(tree), str(plan)) if x.startswith("FAIL SCHEMA")]
    if not bad:
        return ""
    return (f"private-spec: RT-PIN refused: no rt pin (the tree's own tools) and {tree}/tools/die_plan/schema.py is older than the plan "
            f"({bad[0][:260]}). Re-run with --rt <the event's tools_sha> (kit_wave.json dies.<die>.tools_sha), or --rt-floor-exempt WHY")
