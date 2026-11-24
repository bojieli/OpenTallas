"""Plan byte-style round trip of the seat emitters (type_relay_sites.py form): write the edited plan the way its bytes were written."""
import json


def style_of(raw_b):
    """-> function(plan) -> text that reproduces raw_b's own json formatting (value-exact when the style is unknown)"""
    for f in (lambda p: json.dumps(p, separators=(",", ":")) + "\n", lambda p: json.dumps(p) + "\n",
              lambda p: json.dumps(p, indent=1) + "\n", lambda p: json.dumps(p, indent=2) + "\n",
              lambda p: json.dumps(p, separators=(",", ":")), lambda p: json.dumps(p)):
        if f(json.loads(raw_b)).encode() == raw_b:
            return f
    return lambda p: json.dumps(p, indent=1, ensure_ascii=False) + "\n"
