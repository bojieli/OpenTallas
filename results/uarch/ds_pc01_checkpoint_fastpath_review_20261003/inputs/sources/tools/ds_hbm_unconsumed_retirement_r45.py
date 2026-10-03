"""Opt-in source-declared unconsumed output retirement, after producer drain.
No numeric change, early release, RF alias-check waiver or physical ACK claim.
"""
from collections import Counter
from ds_hbm_bound_engine_r43 import engine_class as bound_engine_class


def strings(value):
    if isinstance(value,dict):
        for child in value.values():yield from strings(child)
    elif isinstance(value,list):
        for child in value:yield from strings(child)
    elif isinstance(value,str):yield value


def retirement_plan(native,manifest,homes):
    # Only these two source fields declare produced identities; every other
    # exact version occurrence is conservatively retained as a possible use.
    use_tree=dict(native)
    use_tree['instructions']=[{k:v for k,v in op.items() if k not in ('writes','source_outputs')}
                              for op in native['instructions']]
    refs=Counter(strings(use_tree));refs.update(strings(manifest))
    def exact_home_edge(op,w):
        ix=w['home_indices']
        return bool(ix) and all(homes[i].get('birth_pc')==op['pc'] and homes[i].get('retire_pc')==op['pc']
                               and homes[i]['version']==w['version'] for i in ix)
    return {op['pc']:[w['version'] for w in op['writes'] if refs[w['version']]==0 and exact_home_edge(op,w)]
            for op in native['instructions']}


def retirement_class(base):
    class Engine(base):
        def __init__(self,*args,**kwargs):
            super().__init__(*args,**kwargs)
            self.unconsumed_plan=retirement_plan(self.native,self.provider.manifest,self.homes)
            self.unconsumed_retired=set()
        def execute_operation(self,op):
            super().execute_operation(op)  # actual publication, all ranks, retirement and reverse fences
            if op['pc'] not in self.retired:raise ValueError('unconsumed retirement before producer terminal')
            for version in self.unconsumed_plan[op['pc']]:
                if version in self.last_use:raise ValueError('listed consumer contradicts unconsumed plan')
                if (op['pc'],version) in self.unconsumed_retired:raise ValueError('duplicate unconsumed retirement')
                witness=getattr(self.provider,'witness',None)
                ranks=[r['rank'] for r in op['rank_bindings'] if not r.get('empty_owned_extent')]
                if witness is None or getattr(witness,'failed',True) or any((op['pc'],version,r,self.generation,'data') not in witness.seen for r in ranks):
                    raise ValueError('all active producer ranks require exact witnessed publication')
                if self.provider._leased(version):raise ValueError('version still leased')
                for port in list(self.provider.rf.values())+list(self.provider.state.values()):
                    if any((port.live,port.queue,port.calendar,port.resident)):
                        raise ValueError('producer owner reverse debt retained')
                # Existing source release refuses live views before deleting any
                # locations. No fake consumer ACK or backing overwrite is added.
                self.provider.release_version(version,self.generation)
                self.unconsumed_retired.add((op['pc'],version))
                self.journal.append(dict(event='source_unconsumed_output_retired',PC=op['pc'],version=version,
                    generation=self.generation,producer_all_rank_reverse_retirement_complete=True,
                    source_or_manifest_consumer_references=0,hardware_qualified=False))
    return Engine


def engine_class(prefix,*,retire_unconsumed=False):
    if type(retire_unconsumed)is not bool:raise ValueError('explicit boolean opt-in required')
    original=bound_engine_class(prefix)
    return retirement_class(original) if retire_unconsumed else original
