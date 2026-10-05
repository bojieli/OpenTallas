"""Conditional same-clock four-phase transport; boundary-specific CDC census."""
import hashlib,json,subprocess
from pathlib import Path
PIN='1fa3b30f088eea87a801605ba22a276835214b5e'
def pin(path):
    raw=subprocess.check_output(['git','show',PIN+':'+path]);return dict(commit=PIN,path=path,sha256=hashlib.sha256(raw).hexdigest())
def simulate(H,delay):
    req=[0]*H;ack=[0]*H;sender=1;peer=0;published=False;consumed=False;age=0;seen1=False
    events=[]
    for cycle in range(8*H+delay+20):
        oldreq=req[:];oldack=ack[:];oldsender=sender;oldpeer=peer
        req=[int(oldsender==1)]+oldreq[:-1]
        ack=[oldpeer]+oldack[:-1]
        if oldreq[-1] and not published:
            published=True;events.append(['request_arrived',cycle])
        if published and not consumed:
            if age==delay:consumed=True;peer=1;events.append(['consume_ACK1',cycle])
            else:age+=1
        if oldsender==1 and oldack[-1]:
            assert consumed;seen1=True;sender=2;events.append(['source_ACK1_REQ0',cycle])
        if consumed and peer and not oldreq[-1]:
            assert seen1;peer=0;events.append(['peer_REQ0_ACK0',cycle])
        if oldsender==2 and not oldack[-1]:
            assert consumed and seen1 and peer==0
            sender=0;events.append(['source_ACK0_credit',cycle]);break
    assert sender==0 and consumed and not any(req) and not any(ack)
    return dict(H=H,consumer_delay=delay,events=events,reuse_cycle=cycle)
def run():
    cases=[simulate(h,d) for h in range(1,50) for d in (0,1,17,37)]
    out=dict(schema='opentallas.engram.clock-boundary-specific-capture.v1',
        generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        pins=[pin(p) for p in ['AGENTS.md','docs/MICROARCH_MODEL.md','rtl/chip/ot_chip_v41x_tile.sv','rtl/hdc/v41x/ot_hdc_v41x_egather.sv','rtl/rom/ot_rom_pkg_link.sv','rtl/rom/ot_rom_link_cdc.sv','rtl/lib/ot_cdc_mailbox.sv']],
        boundaries=[dict(name='Internal home macro/mux/register tree',clock_class='CONDITIONAL_SAME_1_2GHz_HOME_CLOCK',
            rationale='Architecture streaming-domain assignment and single-clk gather source support a synchronous construction. Physical Engram tree clock port/CTS instantiation is absent.',
            asynchronous_mailboxes_per_internal_hop=0,clock_phase_and_CTS_pin=None),
            dict(name='Home-to-consumer interdie PHY',clock_class='PLESIOCHRONOUS_UNBOUND_ENDPOINTS',
                rationale='rom_link_cdc explicitly assigns each package its own PLL/reference with clock offset. Same nominal1.2GHz does not imply shared phase.',
                actual_endpoint_PLL_phase_pins=None,actual_crossing_count=None,actual_capture_FF=None),
            dict(name='Streaming1.2GHz to serial SU/VM0.9GHz',clock_class='3_TO_4_RATE_CROSSING_PHASE_UNBOUND',
                rationale='Architecture assigns serial consumers to0.9GHz. Exact generated-clock relation/common reset and chosen Engram consumer instantiation absent.',
                related_clock_timing_proof=None,actual_crossing_count=None,actual_capture_FF=None)],
        constructive_synchronous_candidate=dict(status='INTEGER_CAUSAL_PIPELINE_ONLY_NOT_IMPLEMENTED',
            circuit='Source sender state holds REQ1 until observed ACK1, then holds REQ0 until observed ACK0. Receiver raises held ACK1 only on final word consumption and lowers it only after observing REQ0. Each selected same-clock hop registers REQ and ACK levels, preserving order without an event FIFO.',
            assumptions=['Exactly one immutable locked full identity per selected path.','REQ and ACK are sampled on the same clock with priced edge/route timing.','No independent reset or path/context reassignment during the lease.','ACK publication tied to actual receiver consumption; source observes transported registered level, never caller values.'],
            control_storage_reservation_per_paired_hop=2,
            recipe='One forward REQ-level register and one reverse ACK-level register per paired physical hop. Endpoint senderFSM/peerACK remain in prior6-bit control allocation; no subtraction from old allocations.',
            hops_per_home=24928,homes=192,conditional_extra_register_bits=2*24928*192,
            conditional_total_with_prior_E32_FF=4361491198+2*24928*192,
            architecture_minimum=None,actual_incremental_FF=None,
            new_clock_gating_credit=False,retained_tag_dedup_credit=False,
            tests=dict(cases=len(cases),H_range=[1,49],consumer_delay_cases=[0,1,17,37],all_consume_before_credit=True,all_level_pipelines_zero_before_reuse=True),
            calendars=cases,
            scope='Single selected same-clock path; ACK wait is a causal level handshake, not a two-entry event queue. Does not prove global tree drain, word reassembly timing, final row consumption, PHY transport or reset safety.'),
        mandatory_unpriced_inventory=['REQ branch/path enables derived from locked fullword27 plus shard; ACK reverse selection and fanout. Binary tree logical fanout<=2 does not bound physical buffer count or clock/control load.',
            'Per-hop level holding/forwarding mux or unconditional register implementation and reset. No generic mailbox replication or free ICG.',
            'Endpoint full word27,row29,shard,imageSHA,E32 identity lock/comparators, final row consumed and reverse rowACK state.',
            'Global all-hop/backend/queue/consumer drain and reset/epoch transition controller; selected-path zero levels alone are insufficient.',
            'Actual interdie and1.2/0.9 capture/holding/online/reset/CDC registers and synchronization timing.',
            'Mapped gates/clock buffers, finite pin capacitance, reset fanout, SS/FF and route constraints for every new control instance.'],
        prior_depth2_101FF_scope='Chosen reservation only; its power refusal does not reject this unpriced synchronous candidate or establish minimum.',
        actual_Engram_clockplan_binding=None,actual_drain_reset_provider=None,L1_generated_source=None,
        checkpoint_reads=0,RTL_or_PnR_runs=False,physical_admission=False)
    dest=Path('results/quality/w16_engram_rom_constructive_home_20261001/clock_boundary_capture.json')
    assert not dest.exists();dest.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps(dict(cases=len(cases),extra_bits=2*24928*192,sha256=hashlib.sha256(dest.read_bytes()).hexdigest())))
if __name__=='__main__':run()
