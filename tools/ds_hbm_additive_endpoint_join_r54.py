"""Default-off exact additive calendar endpoint join. No runtime or PHY credit.

Original calendar, endpoint, constructor and checkpoint files remain immutable.
Only the old calendar guard and the group's calendar import are adapted; every
producer/home/lease/service predicate is retained from the pinned source AST.
"""
import ast
import hashlib
import inspect
import types
from pathlib import Path
from h3_ds_connected_provider_r37 import ROOT
from ds_hbm_pc10_composed_engine_r46 import engine_class as predecessor_engine
from h4_hbm_pc10_r41_lineage import ProductionPC10
from h4_hbm_w19_pc10_endpoints import ProductionPC10 as Original, ProductionSharedFactory, inputs
from ds_hbm_pc10_engine_r44 import PC10Groups
from hbm_bound_event_journal_r30 import BoundSectorProvider as OriginalSectorProvider

CALENDAR_SHA='dc04ddb7da27b7a1230691a01bba6af6bdd45bacf59b8afc58b0ad853c6c0a21'
ORIGINAL_CALENDAR_SHA='c0370e63dba0eadcc06c5522c28a956ddebfd10af9b8765a61fe0e4fe025b817'
ENDPOINT_SHA='5013e5695ef6ae80fa1988d5f5529f766d8dad60ae7254ff2139fd29834329fc'
GROUP_SOURCE_SHA='96949401e4ef66977211d03d4d64821ca7cff4bd818a8701d8806344484bc31d'
HELPER_SHA='0a6ce36d0357adbb32ce16408702cfc6927608e5b6124b5ab82b8f9250d969c1'


def function_ast(raw,name):
    return ast.dump(next(n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef) and n.name==name),include_attributes=False)


def verify_calendar():
    import h3_complete_native_calendar_successor_r1 as calendar
    path=ROOT/'tools/h3_complete_native_calendar_successor_r1.py'
    original=ROOT/'tools/h3_complete_native_calendar.py'
    if hashlib.sha256(path.read_bytes()).hexdigest()!=CALENDAR_SHA or Path(calendar.__file__).resolve()!=path.resolve():
        raise ValueError('exact additive calendar source required')
    if hashlib.sha256(original.read_bytes()).hexdigest()!=ORIGINAL_CALENDAR_SHA:
        raise ValueError('original calendar changed')
    if function_ast(path.read_bytes(),'execute_ds_provider_group128')!=function_ast(original.read_bytes(),'execute_ds_provider_group128'):
        raise ValueError('original generic executor AST changed')
    fn=calendar.execute_ds_provider_group128
    if fn.__globals__ is not vars(calendar) or Path(fn.__code__.co_filename).resolve()!=path.resolve():
        raise ValueError('exact successor runtime executor origin required')
    return calendar


def successor_source_mismatch(fn):
    calendar=verify_calendar()
    if fn is not calendar.execute_ds_provider_group128:
        raise ValueError('exact successor runtime executor object required')
    return False


def clone_method(cls,name,transform):
    module=inspect.getmodule(cls);path=Path(module.__file__)
    if cls is PC10Groups and hashlib.sha256(path.read_bytes()).hexdigest()!=GROUP_SOURCE_SHA:
        raise ValueError('original group endpoint source changed')
    tree=ast.parse(path.read_bytes())
    owner=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==cls.__name__)
    fn=next(n for n in owner.body if isinstance(n,ast.FunctionDef) and n.name==name)
    transform(fn)
    namespace=dict(vars(module));namespace['successor_source_mismatch']=successor_source_mismatch
    exec(compile(ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[])),__file__,'exec'),namespace)
    return namespace[name]


def endpoint_transform(fn):
    if hashlib.sha256(Path(inspect.getmodule(Original).__file__).read_bytes()).hexdigest()!=ENDPOINT_SHA:
        raise ValueError('original endpoint source changed')
    guards=[n for n in fn.body if isinstance(n,ast.If) and "inputs()['calendar.py']" in ast.unparse(n.test)]
    if len(guards)!=1:raise ValueError('one exact historical calendar guard required')
    guards[0].test=ast.Call(func=ast.Name(id='successor_source_mismatch',ctx=ast.Load()),args=[ast.Name(id='fn',ctx=ast.Load())],keywords=[])


def group_transform(fn):
    imports=[n for n in fn.body if isinstance(n,ast.Import) and len(n.names)==1 and n.names[0].name=='h3_complete_native_calendar']
    if len(imports)!=1:raise ValueError('one original group calendar import required')
    imports[0].names[0].name='h3_complete_native_calendar_successor_r1'


class SuccessorPC10(ProductionPC10):
    execute=clone_method(Original,'execute',endpoint_transform)


class SuccessorGroups(PC10Groups):
    run=clone_method(PC10Groups,'run',group_transform)


def verify_installed_provider(cls):
    calendar=verify_calendar()
    if cls.__bases__!=(OriginalSectorProvider,) or cls.__init__ is not OriginalSectorProvider.__init__:
        raise ValueError('literal original addressed provider constructor required')
    parent_code=next(c for c in calendar.install_compact_provider_journals_preserving_constructor.__code__.co_consts
                     if isinstance(c,types.CodeType) and c.co_name=='ConstructorPinnedProvider')
    log_code=next(c for c in parent_code.co_consts if isinstance(c,types.CodeType) and c.co_name=='log')
    if cls.log.__code__ is not log_code or inspect.getclosurevars(cls.log).nonlocals.get('original') is not OriginalSectorProvider:
        raise ValueError('exact checksum logger and original-provider closure required')
    if OriginalSectorProvider.__init__.__globals__['DiskEvents'] is not calendar.CompactDiskEvents:
        raise ValueError('exact compact evidence backend required')
    return True


def install(modules):
    import hbm_bound_event_journal_r30 as journal
    import sys
    if sys.modules[__name__] in modules:
        raise ValueError('immutable constructor anchor excluded from alias install')
    receipt=verify_calendar().install_compact_provider_journals_preserving_constructor(modules)
    verify_installed_provider(journal.BoundSectorProvider)
    return receipt


def engine_class(prefix,*,finite_pc10=False,retire_unconsumed=False,physical_backend=False):
    base=predecessor_engine(prefix,finite_pc10=finite_pc10,retire_unconsumed=retire_unconsumed,physical_backend=physical_backend)
    if not finite_pc10:return base
    class Engine(base):
        def __init__(self,*args,**kwargs):
            super().__init__(*args,**kwargs)
            verify_calendar()
            self.groups.endpoint=SuccessorPC10(self.provider)
            self.groups.shared=ProductionSharedFactory(self.provider.journal_budget)
            self.groups.__class__=SuccessorGroups
            self.pc10_endpoint_scope.update(additive_calendar_sha256=CALENDAR_SHA,
                source_guard_adapter='R54 exact additive source and unchanged executor AST',
                original_shared_factory_and_constructor_retained=True)
    return Engine
