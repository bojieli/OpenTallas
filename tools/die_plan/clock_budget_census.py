"""Collect native explicit clock budget failures before per-type emission."""

def census(P, active_types):
    import taps
    checked, failures = [], []
    for name in sorted(set(active_types)):
        typ = P.types[name]
        mode = typ.get("clock", {}).get("tap_mode")
        validate = {"explicit": taps.explicit_taps,
                    "grid+explicit": taps.grid_explicit_taps}.get(mode)
        if validate is None:
            continue
        checked.append(name)
        try:
            validate(P, name)
        except ValueError as error:
            failures.append(dict(type=name, mode=mode, error=str(error)))
    return dict(checked=checked, failures=failures)
