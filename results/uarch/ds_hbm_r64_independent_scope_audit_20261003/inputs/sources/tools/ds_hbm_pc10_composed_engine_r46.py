"""Default-off R45 retirement + R44 PC10 join, no numerical/physical GO."""
from ds_hbm_pc10_engine_r44 import engine_class as endpoint_engine_class
from ds_hbm_unconsumed_retirement_r45 import retirement_class


def require_PC9_origin(engine):
    if not set(range(10))<=engine.retired:raise ValueError('same-instance actual PC0..9 retirement required')
    witness=getattr(engine.provider,'witness',None)
    if witness is None or getattr(witness,'failed',True):raise ValueError('actual byte-exact PC9 witness required')
    op=engine.native['instructions'][9]
    producer=[r['rank'] for r in op['rank_bindings'] if not r.get('empty_owned_extent')]
    if producer!=list(range(64)) or len(op['writes'])!=1:raise ValueError('exact64 PC9 producer rank contract')
    version=op['writes'][0]['version']
    if any((9,version,r,engine.generation,'data') not in witness.seen for r in producer):
        raise ValueError('all64 PC9 actual byte-exact producer publications required')
    # Same instance backing/origin is then checked and read by ProductionPC10;
    # no filesystem/golden restoration, cache callback or source substitution.
    for r in range(96):
        identity=engine.groups.endpoint.identity(r)
        if (10,identity['version'],r,engine.generation,'data') not in witness.expected:
            raise ValueError('complete96 source-bound PC10 observer expectations required')


def engine_class(prefix,*,finite_pc10=False,retire_unconsumed=False,physical_backend=False):
    if type(retire_unconsumed)is not bool:raise ValueError('explicit boolean retirement opt-in required')
    base=endpoint_engine_class(prefix,finite_pc10=finite_pc10,physical_backend=physical_backend)
    if retire_unconsumed:base=retirement_class(base)
    if not finite_pc10:return base
    class Engine(base):
        def execute_operation(self,op):
            if op['pc']==10:require_PC9_origin(self)
            return super().execute_operation(op)
    return Engine
