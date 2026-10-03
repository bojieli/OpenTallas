"""Bind actual canonical output to exact enrolled plan AND priced projection.
No automatic repricing of arbitrary paths; refuse before provider/allocation.
"""
from pathlib import Path

def validate_output_root(actual,plan,projection):
    supplied=Path(actual)
    if not supplied.is_absolute() or str(supplied)!=str(supplied.resolve()):
        raise ValueError('actual output must be canonical absolute priced path')
    for owner,record in (('plan',plan),('projection',projection)):
        value=record.get('output_root')
        if not isinstance(value,str) or not Path(value).is_absolute() or str(Path(value).resolve())!=value:
            raise ValueError(owner+' requires exact canonical output_root')
        if value!=str(supplied):raise ValueError('actual output differs from exact '+owner+' priced root')
    return str(supplied)
