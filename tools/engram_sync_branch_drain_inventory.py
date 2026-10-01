"""Conditional registered control tree and non-destructive drain reservation."""
import hashlib,json
from pathlib import Path
ROOT=Path('results/quality/w16_engram_rom_constructive_home_20261001')
def run():
    raw=(ROOT/'repacked_192_enable_mask_contract.json').read_bytes();old=json.loads(raw)
    nodes=8191;leaves=8192;wire=old['path_geometry']['wire_stage_sum'];hops=nodes+wire;homes=192
    # Reserve every role independently: no reuse deduction from prior E32 control.
    storage=dict(forward_REQ_and_reverse_ACK_level=2*hops,locked_branch_selector=nodes,
                 registered_branch_drain=nodes,registered_leaf_idle=leaves,
                 wire_drain_pipeline=wire,root_quiesce_FSM=3)
    count=sum(storage.values())
    truth=[]
    for req in (0,1):
        for select in (0,1):
            for left in (0,1):
                for right in (0,1):
                    lreq=req & (1-select);rreq=req & select;ack=(left if not select else right)
                    assert lreq+rreq==req and not (lreq and rreq)
                    truth.append([req,select,left,right,lreq,rreq,ack])
    drain_truth=[[a,b,c,a&b&c] for a in (0,1) for b in (0,1) for c in (0,1)]
    out=dict(schema='opentallas.engram.synchronous-branch-reset-drain-construction.v1',
        generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        geometry_source_SHA256=hashlib.sha256(raw).hexdigest(),geometry_source_commit='c8ea5395dfd8292dc329de9a629bcb14cf5cc4b3',
        status='CONDITIONAL_CONSTRUCTIVE_RESERVATION_NO_ACTUAL_INSTANCES',
        Boolean_gate_checks=dict(branch_cases=truth,drain_cases=drain_truth,no_dualbranch_REQ=True),
        clock_binding=dict(home_clock='One common ungated1.2GHz clock for selected internal tree; actual port/net/CTS pinsNULL.',
            no_async_primitives_on_synchronous_hops=True,clock_tree_actual=None,
            actual_interdie_and_operator_CDC=None),
        synchronous_branch=dict(nodes_per_home=nodes,physical_hops_per_home=hops,
            selector='Lock one branch-select FF during source-owned fullword27 setup; hold through ACK1, REQ0, ACK0 and final context retirement. Never recompute from a changing next request.',
            forward=['left_REQ = held_REQ AND NOT locked_select','right_REQ = held_REQ AND locked_select'],
            reverse='held_ACK_next = locked_select ? right_ACK : left_ACK',
            drain='branch_idle_next = local_idle AND left_idle AND right_idle; both child idle paths participate, including unselected sibling.',
            forwarding='EveryREQ/ACK hop is a same-clock register, sampled on each edge. Newword setup inhibited until drain has propagated and locked context matches.',
            logical_fanout=dict(REQ_to_branch_gates=2,select_to_control_gates=3,ACK_return_to_parent=1,child_idle_to_parent=1,
                caveat='Select also drives existing payload/tag routing. Those actual mux loads and inserted buffers are unbound. Logical fanout is NOT physical capacitance/route proof.'),
            conditional_gate_recipe_per_branch=dict(select_inverter_NAND2_tied=1,REQ_two_AND2=2,ACK_MUX2=1,drain_threeinput_via_two_AND2=2,
                NAND2_equivalent=1+2*2+4+2*2,
                excludes='local_idle predicate, clock/reset buffers, selector capture enable/feedback, controller decode, word/image/tag equality, setup serializer, link/CDC and physical load buffers'),
            conditional_branch_NAND2_equivalent_total=nodes*homes*13),
        control_storage=dict(per_home_roles=storage,per_home_total=count,homes=homes,
            added_register_bits=count*homes,prior_all_E32_FF_preserved=4361491198,
            conditional_total_register_bits=4361491198+count*homes,
            placement='Wire-drain pipeline reservation uses all16737 forwardgeometry wire stages; each branch and leaf receives an independentregisteredidle role. No claim they exist or match placed control-return geometry.',
            reservation_not_minimum=True,actual_incremental_FF=None,
            reuse_subtractions=0,clock_gating_credit=False),
        reset_drain_protocol=[
            'RUN: admit only complete source-owned identity/session requests; increment bounded ownership records before any macro/read publication.',
            'QUIESCE: inhibit new root admissions and lock image/E32/row/shard/path. Continue existing data and ACK progression; never drop a consumed word or force ACK0.',
            'WAIT_CONSUMERS: obtain finalword/row actualconsume publications, return ACK1/REQ0/ACK0 through every required path; preserve locked identity.',
            'WAIT_ALL_IDLE: every leaf idle requires noissued ROM reply/capture/reassembly/pending publication/consumer lease; every branch idle includes both children and local payload/setup/ACK queues. Registered reductions must stabilize across all pipeline delays.',
            'BOUNDARY_BARRIER: interdie/serial-domain queues and owner consumer records must issue actual ordered idle acknowledgements under same identity; synchronous tree idle cannot substitute.',
            'RETIRE: only after root completion bitmap, finalrowconsume and boundarybarrier plus globalidle allow context/image/E32 change or reset.',
            'RESET: actualresetassert/deassert/online policy remainsNULL. Coldreset under externallyproved noleases may clear control; destructive flush is NOT successful completion. Unexpectedreset while leased must fault/recover preserved ownership, never return reusable credit.'
        ],
        mandatory_idle_inputs=['REQ/ACKregisteredlevelszero','no requestsetup fragment/payload outstanding','no response fragment/reassembly/published-or-consumed-unretired word','no macroissued reply/capture outstanding','no external queue/link/CDC receipt or ownership record outstanding','final row consumed and reverse rowACK returned'],
        missing_actual_bindings=['Fullword27,row29,shard,imageSHA,E32 setup producer and immutable endpoint copies/compares','Selector setup acceptance/capture timing and actual payload mux fanout','Localidle predicates for every prior storage/registerinstance; zeroREQ/ACK alone is insufficient','Boundary barrier source/clock pins and ordered transport','Reset controller state transitions/nextstate gates and retention on faults','SS/FF CTS control/return routing and finite source capacitance/activity'],
        exact_all_control_storage=False,complete_composed_model=False,physical_admission=False,
        L1_generated_source=None,checkpoint_reads=0,RTL_or_PnR_runs=False)
    # TwoAND request=4NAND, mux4, inverter1, twoAND drain4 =>13.
    assert out['synchronous_branch']['conditional_gate_recipe_per_branch']['NAND2_equivalent']==13
    dest=ROOT/'sync_branch_drain_inventory.json';assert not dest.exists();dest.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps(dict(per_home_bits=count,extra=count*homes,branch_NAND2=nodes*homes*13,sha256=hashlib.sha256(dest.read_bytes()).hexdigest())))
if __name__=='__main__':run()
