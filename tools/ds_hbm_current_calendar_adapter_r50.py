"""Source-pinned current calendar join, no old endpoint guard bypass.
Clone only the immutable endpoint execute source, replacing its whole-file
historical guard with exact current file AND unchanged executor AST validation.
Every producer/ownership/shared-home check stays source-identical. Default off.
"""
import ast,hashlib,inspect,json
from pathlib import Path
from ds_hbm_pc10_composed_engine_r46 import engine_class as predecessor_engine
from h4_hbm_pc10_r41_lineage import ProductionPC10
from h4_hbm_w19_pc10_endpoints import ProductionPC10 as Original,inputs
from h3_ds_connected_provider_r37 import ROOT
CURRENT_SHA='c0370e63dba0eadcc06c5522c28a956ddebfd10af9b8765a61fe0e4fe025b817'
ORIGINAL_ENDPOINT_SHA='5013e5695ef6ae80fa1988d5f5529f766d8dad60ae7254ff2139fd29834329fc'
def executor_ast(raw):
    return ast.dump(next(n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef) and n.name=='execute_ds_provider_group128'),include_attributes=False)
def verify_current_source(raw,reference):
    if hashlib.sha256(raw).hexdigest()!=CURRENT_SHA:raise ValueError('exact current calendar module source required')
    if executor_ast(raw)!=executor_ast(reference):raise ValueError('unchanged generic PC10 executor source required')
    return True

def current_source_mismatch(fn):
    import h3_complete_native_calendar as c
    source=ROOT/'tools/h3_complete_native_calendar.py'
    verify_current_source(source.read_bytes(),inputs()['calendar.py'])
    if fn is not c.execute_ds_provider_group128 or Path(fn.__code__.co_filename).resolve()!=source.resolve():raise ValueError('exact current runtime executor function required')
    return False

def adapted_execute():
    module=inspect.getmodule(Original);path=Path(module.__file__)
    if hashlib.sha256(path.read_bytes()).hexdigest()!=ORIGINAL_ENDPOINT_SHA:raise ValueError('original production endpoint source changed')
    tree=ast.parse(path.read_bytes());cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='ProductionPC10')
    fn=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='execute')
    # Its unique historical whole-file identity guard is replaced explicitly;
    # same-provider, exact actual PC9 ready, directory, lease and service calls
    # remain unchanged AST nodes, not rewritten implementations.
    guards=[n for n in fn.body if isinstance(n,ast.If) and "inputs()['calendar.py']" in ast.unparse(n.test)]
    if len(guards)!=1:raise ValueError('exact single historical calendar guard required')
    guards[0].test=ast.Call(func=ast.Name(id='current_source_mismatch',ctx=ast.Load()),args=[ast.Name(id='fn',ctx=ast.Load())],keywords=[])
    namespace=dict(vars(module));namespace['current_source_mismatch']=current_source_mismatch
    code=ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[]));exec(compile(code,__file__,'exec'),namespace)
    return namespace['execute']
class CurrentPC10(ProductionPC10):
    execute=adapted_execute()

def engine_class(prefix,*,finite_pc10=False,retire_unconsumed=False,physical_backend=False):
    base=predecessor_engine(prefix,finite_pc10=finite_pc10,retire_unconsumed=retire_unconsumed,physical_backend=physical_backend)
    if not finite_pc10:return base
    class Engine(base):
        def __init__(self,*args,**kwargs):
            super().__init__(*args,**kwargs)
            import h3_complete_native_calendar as c
            current_source_mismatch(c.execute_ds_provider_group128)
            endpoint=CurrentPC10(self.provider)
            if endpoint.lineage!='R41_full_source_regeneration':raise ValueError('complete current native/home lineage required')
            self.groups.endpoint=endpoint
            self.groups.shared=CurrentSharedFactory(self.provider.journal_budget)
            self.pc10_endpoint_scope.update(current_calendar_source_sha256=CURRENT_SHA,source_guard_adapter='R50 exact current file plus unchanged executor AST',physical_primitive_port_calendar_bound=False)
    return Engine

# Keep the exact original constructor class before any compact-install alias
# mutation; compact installation must not rewrite this source guard anchor.
from hbm_bound_event_journal_r30 import BoundSectorProvider as OriginalSectorProvider
from h4_hbm_w19_pc10_endpoints import ProductionSharedFactory as OriginalSharedFactory

def shared_provider_source_mismatch(provider_class):
    import h3_complete_native_calendar as c
    source=Path(OriginalSectorProvider.__init__.__code__.co_filename)
    if hashlib.sha256(source.read_bytes()).hexdigest()!='1efaea518056231512ebd1a59743d66ddedd775728183e70913a9755d53ba9f0':raise ValueError('original addressed sector source changed')
    if provider_class is OriginalSectorProvider:return False
    verify_current_source((ROOT/'tools/h3_complete_native_calendar.py').read_bytes(),inputs()['calendar.py'])
    expected=c.compact_sector_provider_class(OriginalSectorProvider)
    if provider_class.__bases__!=(OriginalSectorProvider,) or provider_class.__init__.__code__ is not expected.__init__.__code__:
        raise ValueError('exact current compact addressed provider constructor required')
    return False

def adapted_shared_call():
    source=Path(inspect.getmodule(OriginalSharedFactory).__file__)
    if hashlib.sha256(source.read_bytes()).hexdigest()!=ORIGINAL_ENDPOINT_SHA:raise ValueError('original shared factory source changed')
    tree=ast.parse(source.read_bytes());cl=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='ProductionSharedFactory');fn=next(n for n in cl.body if isinstance(n,ast.FunctionDef) and n.name=='__call__')
    guards=[n for n in fn.body if isinstance(n,ast.If) and 'BoundSectorProvider.__init__' in ast.unparse(n.test)]
    if len(guards)!=1:raise ValueError('one exact addressed provider source guard required')
    guards[0].test=ast.Call(func=ast.Name(id='shared_provider_source_mismatch',ctx=ast.Load()),args=[ast.Name(id='BoundSectorProvider',ctx=ast.Load())],keywords=[])
    namespace=dict(vars(inspect.getmodule(OriginalSharedFactory)));namespace['shared_provider_source_mismatch']=shared_provider_source_mismatch
    exec(compile(ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[])),__file__,'exec'),namespace)
    return namespace['__call__']
class CurrentSharedFactory(OriginalSharedFactory):
    __call__=adapted_shared_call()
