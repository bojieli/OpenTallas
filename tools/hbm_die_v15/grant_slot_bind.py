"""Resolve an explicitly bound instance grant before a historical contract slot alias."""


def resolve_slot(name, instance, slots, plan, override=None):
    if override is not None:
        return override
    exact = slots.get(name)
    if exact and exact.get('instance') == name:
        if exact.get('cell') != instance['master']:
            raise ValueError(f'{name}: explicit grant cell {exact.get("cell")} != contract {instance["master"]}')
        return name
    legacy = instance.get('slot')
    if legacy:
        return legacy
    if name in slots or (name in plan and isinstance(plan[name], dict) and 'x' in plan[name]):
        return name
    return None
