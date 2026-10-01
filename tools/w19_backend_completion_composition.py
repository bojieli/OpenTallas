#!/usr/bin/env python3
"""Compose retained burst callbacks and frontend completion, model-only."""
import argparse, hashlib, importlib.util, json, subprocess, tempfile
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PINS={
 'provider':('6e1158394262bc47773993e04efce0672ac4552e','tools/common_hbm_backend_provider_contract.py'),
 'completion':('83235527160371894cb27f9b8fd1e4be654faa4e','tools/common_wrack_completion_calendar.py'),
 'provider_record':('6e1158394262bc47773993e04efce0672ac4552e','results/uarch/qwen_hbm_connected_20261001/common_HBM_backend_provider_binding_r2.json'),
 'frontend_record':('ec3e96c4d39df355a577ec5d433b43965d808ff9','results/uarch/qwen_hbm_connected_20261001/common_WRACK_frozen_model_bench_r2.json')}
def raw(pin):return subprocess.check_output(['git','show',pin[0]+':'+pin[1]],cwd=ROOT)
def digest(b):return hashlib.sha256(b).hexdigest()
def load_sources(directory):
    modules={}
    for name in ('provider','completion'):
        b=raw(PINS[name]);p=Path(directory)/(name+'.py');p.write_bytes(b)
        spec=importlib.util.spec_from_file_location('w16_'+name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.ROOT=ROOT;modules[name]=m
    return modules

def replay(provider,completion,mutate=None):
    """Four real bench backing actions, supplied synthetic kernel boundaries."""
    model=provider.BurstVisibilityModel();commands=[];events=[];receipts=[]
    for tag in range(4):
        sector=(1<<27)+tag;old=bytes([tag])*32;new=bytes([tag+4])*32
        model.preload(sector,old);model.reserve(tag,sector,new)
    # One stack command/source cycle. Fractional fabric edges stay exact in the
    # frontend; backend captures ceil timestamps and preserves column identity.
    model.tick(3)
    for tag in range(4):
        sector=(1<<27)+tag;column=model.now
        model.WR_issue(tag,sector,column);scheduled=model.take_scheduled(tag)
        commands.append(dict(stack=0,tag=tag,sector=sector,kind='write',bytes=32,issue_ps=Fraction(model.cycle*2500,3)))
        receipts.append(scheduled);model.tick()
    model.tick(12)
    for tag in range(4):
        visible=model.take_visible(tag);sector=(1<<27)+tag
        if model.read(sector,True)!=bytes([tag+4])*32:raise ValueError('visible callback not bound to exact backing action')
        if visible['sector']!=receipts[tag]['sector']:raise ValueError('callback identity changed')
        events.append(dict(stack=0,tag=tag,sector=sector,epoch=42,completion_epoch=42,reserve_ps=0,
            column_ps=receipts[tag]['column_ps'],visible_ps=visible['visible_ps'],landing_accept_ps=25000,
            opcode_finish_ps=100000,result_visible_ps=110000,consumer_done_ps=120000))
    backend_free_before_frontend_done=len(model.slots)==0
    if mutate:mutate(events,commands)
    calendar=completion.completion_calendar(events,commands)
    if Fraction(calendar['done_ps'])!=122500:raise ValueError('reverse completion CDC changed')
    return dict(provider_callbacks=receipts,backing_commits=len(events),backend_slots_free_before_frontend_done=backend_free_before_frontend_done,
        timeline=calendar['timeline'],credit_release_ps=calendar['done_ps'],
        kernel_event_scope='Synthetic supplied landing/opcode/result/finaldone only. No actual kernel cost provider or DRAMscheduler run.',
        actual_backend_RTL_provider_bound=False,actual_kernel_cost_provider_bound=False)

def build():
    with tempfile.TemporaryDirectory(prefix='w16-provider-composition-') as d:
        modules=load_sources(d);provider=modules['provider'];completion=modules['completion']
        contract=provider.compose();record=json.loads(raw(PINS['provider_record']))
        if contract!=record:raise ValueError('source-bound provider record reproduction changed')
        demonstration=replay(provider,completion)
    storage=Decimal(contract['storage']['total_register_bits'])*Decimal('.2916')/Decimal('.5')/Decimal('1000000')
    total=Decimal(str(contract['additional_port_cost']['additive_footprint_mm2']))
    frontend=Decimal(str(json.loads(raw(PINS['frontend_record']))['scheduler_event_cost_candidate']['additional_footprint_mm2']))
    return dict(schema='opentallas.w19.backend-completion-composition.v1',status='MODEL_CALLBACK_COMPOSITION_PASS_ACTUAL_PROVIDERS_UNBOUND',
        source_pins={name:dict(commit=c,path=p,sha256=digest(raw((c,p)))) for name,(c,p) in PINS.items()},
        callback_replay=demonstration,once_only_area=dict(backend_total_addon_mm2=str(total),backend_storage_subcomponent_mm2=str(storage),backend_nonstorage_subcomponent_mm2=str(total-storage),storage_added_again=False,
            frontend_addon_mm2=str(frontend),backend_plus_frontend_addon_mm2=str(total+frontend),
            scope='Backend total already includes storage. Frontend ec3 addon separate; no summation with RF/SM/L2/die baseline without role-ledger reconciliation.'),
        composed_constraints=dict(backend_slot_release='Only both actual schedule and visible callbacks delivered',frontend_credit_release='Only actual finalconsumerdone/resultvisibility plus reverseCDC',
            command_ports='read/write share1command/stack/sourcecycle',byte_budget='750B/stack/sourcecycle, finite1024B bucket',
            exact_clock='ceil(cycle*2500/3)ps backend timestamps; rational frontend edges',
            publication='External ownership/epoch permission required before read; benchmark Boolean permission is NOT physical publication qualification'),
        remaining=['actual bank/refresh/turnaround DRAMscheduler and full-address loader providers','all shared client queues/port maps and RMW/epoch/publication ownership','actual kernel landing/opcode/result/finaldone costs','finite crossbar/CDC stage costs and once-only complete area/route ledger','whole-token dependency/contended calendar and legal full-size SS/FF physical fit'],
        graph_service_costs_bound=False,full_token_cycles=None,engine_RTL_build_ready=False,physical_admission=False,adopt=False,jobs_launched=0)

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(build(),indent=2)+'\n')
