"""Physical-pin binding controls; these snapshots are not RTL qualification."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from tools.gpu_sys.canonical_qwen_sector_authority import (
    FIELDS, PhysicalSectorAuthority, SectorBoundPayload, source_identity, unpack_identity)
from tools.gpu_sys.canonical_qwen_sector_authority_model import model, compose_commit
from tools.gpu_sys.test_canonical_qwen_payload_w2 import (
    ControllerPins, W2Pins, CallerAuthority)
from tools.gpu_sys.canonical_qwen_transport import TransportError, W2PrimaryPort


def packed(fields):
    bits = 0
    for name, width in FIELDS:
        bits = (bits << width) | fields[name]
    return bits


class OwnerPins:
    def __init__(self):
        self.values = dict(fault=0, por_n=1, local_reset=0, grant_live=0,
                          grant_identity=0, grant_phase=0, grant_rmw=1,
                          release_ready=0, release_valid=0)
        self.writes = []

    def parameter(self, name):
        return dict(ENABLE=1, IDENTW=207)[name]

    def get(self, name):
        return self.values.get(name, 0)

    def set(self, name, value):
        self.values[name] = value
        self.writes.append((name, value))

    def settle(self):
        pass


class PhysicalAuthorityTest(unittest.TestCase):
    def setUp(self):
        self.c, self.w, self.o = ControllerPins(), W2Pins(), OwnerPins()
        self.caller = CallerAuthority()
        self.port = W2PrimaryPort(self.w, self.caller)
        self.a = PhysicalSectorAuthority(self.o, {7:self.port}, enabled=True)
        self.offer = dict(identity=0xfedcba9876543210, key=0xe2345, sector=191,
                          source_addr=0x300000020, rmw=1, rmw_last=0, write=0, data=0)
        self.fields = dict(self.offer, address=0x200000020, PC=7, client=5,
                           tag=0xfedcba98, generation=14)

    def actual_grant(self):
        # Set saved actual-pin observations. This test does NOT run an allocator.
        self.o.values.update(grant_live=1, grant_phase=1, grant_identity=packed(self.fields))
        return self.a.acquire_payload_sector(self.offer)

    def test_no_grant_from_python_or_map_presence(self):
        self.o.values.update(map_valid=1, map_sector_clear=0)
        self.assertIsNone(self.a.acquire_payload_sector(self.offer))
        self.assertIsNone(self.a.snapshot)
        self.assertEqual(self.o.get('alloc_source'), source_identity(self.offer))
        self.assertEqual(self.o.get('alloc_valid'), 1)
        self.assertEqual([n for n,_ in self.o.writes], ['alloc_source','alloc_rmw','alloc_valid'])

    def test_full_original_physical_identity_in_hardware_snapshot(self):
        route = self.actual_grant()
        self.assertEqual((route.client,route.address,route.tag,route.generation),
                         (5,0x200000020,0xfedcba98,14))
        self.assertEqual(unpack_identity(route.grant.identity),
                         {n:self.fields[n] for n,_ in FIELDS})
        self.assertEqual(self.o.get('alloc_valid'), 0)

    def test_reverse_only_after_actual_matching_hardware_phase(self):
        route = self.actual_grant()
        for phase in (1,2,3):
            self.o.values['grant_phase'] = phase
            self.assertFalse(self.port.authority.reverse_validated(5,0xfedcba98,14,False))
        self.o.values['grant_phase'] = 4
        self.assertTrue(self.port.authority.reverse_validated(5,0xfedcba98,14,False))
        self.assertFalse(self.port.authority.reverse_validated(5,0xfedcba98,14,True))
        self.o.values['grant_phase'] = 7
        self.assertTrue(self.port.authority.reverse_validated(5,0xfedcba98,14,True))
        new = dict(self.offer, write=1,rmw_last=1)
        self.o.values['grant_phase'] = 3
        self.assertIsNone(self.a.continue_payload_rmw(route.grant,new))
        self.o.values['grant_phase'] = 4
        self.assertIs(self.a.continue_payload_rmw(route.grant,new).grant,route.grant)

    def test_nonpayload_callers_retain_original_real_reverse_authority(self):
        self.actual_grant()
        self.caller.reverse = True
        self.assertTrue(self.port.authority.reverse_validated(3,0x12345678,2,True))
        self.assertEqual(self.caller.observed[-1],(3,0x12345678,2,True))

    def test_hardware_grant_change_or_disappearance_is_refused(self):
        for vanished in (False,True):
            with self.subTest(vanished=vanished):
                self.setUp();self.actual_grant()
                if vanished:
                    self.o.values['grant_live'] = 0
                else:
                    self.o.values['grant_identity'] ^= 1
                with self.assertRaisesRegex(TransportError,'disappeared|identity changed'):
                    self.a.acquire_payload_sector(self.offer)
                self.assertIsNotNone(self.a.snapshot)

    def test_release_requires_actual_ready_and_accepted_edge(self):
        route = self.actual_grant()
        new = dict(self.offer,write=1,rmw_last=1)
        self.o.values['grant_phase'] = 7
        self.assertFalse(self.a.release_payload_sector(route.grant,new))
        self.a.after_edge()
        self.assertIsNotNone(self.a.snapshot)
        self.o.values['release_ready'] = 1
        self.assertTrue(self.a.release_payload_sector(route.grant,new))
        self.o.values['grant_live'] = 0 # saved accepted release observation
        self.a.after_edge()
        self.assertIsNone(self.a.snapshot)
        self.assertEqual(self.o.get('release_valid'),0)

    def test_por_during_release_cannot_be_misread_as_retirement(self):
        route=self.actual_grant()
        self.o.values.update(grant_phase=7,release_ready=1)
        self.a.release_payload_sector(route.grant,dict(self.offer,write=1,rmw_last=1))
        self.o.values.update(grant_live=0,por_n=0)
        with self.assertRaisesRegex(TransportError,'without actual release'):
            self.a.after_edge()
        self.assertIsNotNone(self.a.snapshot)

    def test_reset_fault_or_stale_source_retains_snapshot(self):
        route=self.actual_grant()
        with self.assertRaisesRegex(TransportError,'retained source mismatch'):
            self.a.continue_payload_rmw(route.grant,dict(self.offer,write=1,rmw_last=1,key=1))
        self.o.values['local_reset']=1
        with self.assertRaisesRegex(TransportError,'fault/reset'):
            self.a.acquire_payload_sector(self.offer)
        self.assertIsNotNone(self.a.snapshot)

    def test_default_off_and_wrong_pc_binding_refused(self):
        with self.assertRaisesRegex(TransportError,'default off'):
            PhysicalSectorAuthority(self.o,{7:self.port})
        with self.assertRaisesRegex(TransportError,'PC binding'):
            PhysicalSectorAuthority(self.o,{0:self.port},enabled=True)

    def test_existing_payload_adapter_registration_drives_hardware_alloc_only(self):
        # Fresh port: constructor explicitly enrolls shared authority.
        port=W2PrimaryPort(self.w,self.caller)
        joined=SectorBoundPayload(self.c,self.o,{7:port},enabled=True)
        joined.before_edge()
        self.assertEqual(self.o.get('alloc_valid'),1)
        self.assertEqual(joined.payload.accepted,0)
        joined.after_edge()
        self.assertEqual(self.o.get('alloc_valid'),1) # no real grant yet
        self.o.values.update(grant_live=1,grant_identity=packed(self.fields),grant_phase=1)
        self.w.values['c_req_rdy']=1<<5
        joined.before_edge()
        self.assertEqual(joined.payload.event,'REQUEST')
        self.o.values['grant_phase']=2 # actual matched issue handshake observation
        joined.after_edge()
        self.assertEqual(joined.payload.accepted,1)

    def test_unwired_physical_issue_event_cannot_advance_payload(self):
        port=W2PrimaryPort(self.w,self.caller)
        joined=SectorBoundPayload(self.c,self.o,{7:port},enabled=True)
        self.o.values.update(grant_live=1,grant_identity=packed(self.fields),grant_phase=1)
        self.w.values['c_req_rdy']=1<<5
        joined.before_edge()
        with self.assertRaisesRegex(TransportError,'event not accepted'):
            joined.after_edge()
        self.assertEqual(joined.payload.accepted,0)
        self.assertIsNotNone(joined.payload.route.grant)

    def test_model_census_and_nonduplicated_commit_latency(self):
        m=model()
        self.assertEqual(m['raw_control_bits'],212)
        self.assertEqual(m['added_SRAM_bytes'],0)
        self.assertEqual(m['routing_tracks_per_unshared_boundary'],208)
        self.assertEqual(compose_commit(1000,3),1000+272*5)
        self.assertFalse(m['physical_qualified'])
        self.assertIsNone(m['routing_capacity'])

    @unittest.skipUnless(shutil.which('iverilog') and shutil.which('vvp'), 'Icarus unavailable')
    def test_actual_rtl_root_lifetime_guard_and_reset_retention(self):
        # Tiny ROOT unit, not a W2/controller/connected fixture or token run.
        # Checks actual flip-flop state, not a Python grant implementation.
        bench=r'''
module tb;
reg clk=0,por_n=0,run_enable=1,local_reset=0;
reg alloc_valid=0,alloc_rmw=1,map_valid=1,map_sector_clear=0;
wire alloc_ready,grant_live,grant_rmw,fault;
reg [126:0] alloc_source={64'hfedcba9876543210,20'he2345,9'd191,34'h300000020};
reg [33:0] map_addr=34'h200000020;
reg [6:0] map_PC=7;
reg [2:0] map_client=5;
reg [31:0] map_tag=32'hfedcba98;
reg [3:0] map_gen=14;
wire [206:0] grant_identity;
wire [2:0] grant_phase;
reg [203:0] guard_addr=0;
reg [275:0] guard_owner=0;
reg [5:0] guard_write=0;
wire [5:0] guard_permit;
reg issue_valid=0,capture_valid=0,reverse_valid=0,release_valid=0;
wire issue_ready,capture_ready,reverse_ready,release_ready;
reg [206:0] issue_identity=0,capture_identity=0,reverse_identity=0,release_identity=0;
reg issue_write=0,capture_write=0,reverse_write=0;
reg [206:0] saved;
ot_gpu_qwen_payload_sector_authority #(.ENABLE(1)) dut(.*);
task tick;begin #1;clk=1;#1;clk=0;#1;end endtask
initial begin
 #1;por_n=1;alloc_valid=1;tick;
 if(alloc_ready||grant_live) $fatal(1,"grant without actual prior-sector drain");
 map_sector_clear=1;tick;alloc_valid=0;saved=grant_identity;
 if(!grant_live||grant_phase!=1) $fatal(1,"actual allocation missing");
 guard_addr[5*34+:34]=map_addr;guard_owner[5*46+:46]=saved[45:0];
 guard_addr[4*34+:34]=map_addr;guard_owner[4*46+:46]={7'd7,3'd4,32'd1,4'd1};#1;
 if(!guard_permit[5]||guard_permit[4]||!guard_permit[3]) $fatal(1,"sector guards");
 issue_identity=saved;issue_valid=1;tick;issue_valid=0;
 if(grant_phase!=2||guard_permit[5]) $fatal(1,"issue ownership");
 capture_identity=saved;capture_valid=1;tick;capture_valid=0;
 if(grant_phase!=3) $fatal(1,"actual capture missing");
 reverse_identity=saved;reverse_valid=1;tick;reverse_valid=0;
 if(grant_phase!=4||!grant_live||grant_identity!=saved) $fatal(1,"OLD reverse released RMW");
 issue_write=1;issue_valid=1;tick;issue_valid=0;
 capture_write=1;capture_valid=1;tick;capture_valid=0;
 reverse_write=1;reverse_valid=1;tick;reverse_valid=0;
 if(grant_phase!=7||!grant_live) $fatal(1,"NEW reverse erased grant");
 release_identity=saved;release_valid=1;#1;
 if(!release_ready) $fatal(1,"actual release not ready");
 tick;release_valid=0;
 if(grant_live||fault) $fatal(1,"release failed");
 alloc_valid=1;tick;alloc_valid=0;saved=grant_identity;
 // A reverse before an issued/captured operation is refused and retained.
 reverse_identity=saved;reverse_write=0;reverse_valid=1;tick;reverse_valid=0;
 if(!fault||!grant_live||grant_identity!=saved) $fatal(1,"early reverse erased grant");
 local_reset=1;tick;
 if(!fault||!grant_live||grant_identity!=saved) $fatal(1,"local reset erased external debt");
 $display("PASS_FINITE_AUTHORITY_ROOT_UNIT");$finish;
end
endmodule
'''
        root=Path(__file__).resolve().parents[2]
        rtl=root/'rtl/model/qwen_payload_sector_authority_20261003/ot_gpu_qwen_payload_sector_authority.sv'
        with tempfile.TemporaryDirectory() as tmp:
            tb=Path(tmp)/'tb.sv';tb.write_text(bench)
            binary=Path(tmp)/'root.vvp'
            compile=subprocess.run(['iverilog','-g2012','-s','tb','-o',str(binary),str(rtl),str(tb)],
                                   text=True,capture_output=True)
            self.assertEqual(compile.returncode,0,compile.stderr)
            run=subprocess.run(['vvp',str(binary)],text=True,capture_output=True)
            self.assertEqual(run.returncode,0,run.stdout+run.stderr)
            self.assertIn('PASS_FINITE_AUTHORITY_ROOT_UNIT',run.stdout)


if __name__=='__main__':
    unittest.main()
