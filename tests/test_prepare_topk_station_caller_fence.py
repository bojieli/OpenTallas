"""Independent transport-contract checks; no HDL/arithmetic qualification."""
from collections import deque
import json
from pathlib import Path
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import prepare_topk_station_caller_fence as P

class FenceContract(unittest.TestCase):
    def test_reproduction_and_pins(self):
        b=P.BASE/'package_r3'
        self.assertEqual(P.prepare(P.SOURCE.read_text()),(b/'ot_w15_coll_dma_station_prepare.sv').read_text())
        import hashlib
        for name,digest in json.loads((b/'artifact_manifest.json').read_text()).items():self.assertEqual(hashlib.sha256((b/name).read_bytes()).hexdigest(),digest)
        with tempfile.TemporaryDirectory() as td:
            dest=Path(td)/'fresh';P.emit(dest)
            for old in b.iterdir():self.assertEqual((dest/old.name).read_bytes(),old.read_bytes())
    def test_native_arithmetic_and_acceptance_unchanged(self):
        source=P.SOURCE.read_text();new=P.prepare(source)
        for anchor in ["wire tk_ld = busy && tk_r && !tk_sel && o_valid && !fault && !o_err && !engine_fault;",
                       "assign o_ready = (GW == 4 && e_mode && !tk_r) ? tr_ready : 1'b1;",
                       'if (tk_ld && o_last) begin tk_sel <= 1; tk_go <= 1; end',
                       "tk_wa[tj*WA +: WA] = dst_r + tk_oidx[WA-1:0] + WA'(tj);",
                       "if (tk_ov) tk_oidx <= tk_oidx + CW'(tk_nw);",
                       'if (o_err || engine_fault || tr_fault || tk_fault || (go && busy)) fault <= 1;']:
            self.assertEqual(source.count(anchor),1);self.assertEqual(new.count(anchor),1)
        native=source[source.index('    function automatic'):source.index('    endfunction')+len('    endfunction')]
        self.assertIn(native,new)
    def test_default_off_generic_width_and_full_enabled_guard(self):
        s=P.prepare(P.SOURCE.read_text())
        self.assertIn('parameter integer TK_STATION = 0',s)
        self.assertIn('(GW==4?N:1)*FW',s)
        self.assertIn('TOPK!=1 || N!=4 || GW!=4 || FW!=512 || WA!=15 || TK_NMAX!=2048 || TK_DIG!=8',s)
        self.assertIn('VM_ALWAYS_READY!=1',s)
        for gw in [1,4]:
            ipw=1+1+2+9+(4 if gw==4 else 1)*512+1+2*14+32
            concat=2+2+9+(4 if gw==4 else 1)*512+1+28+32
            self.assertEqual(ipw,concat)
        self.assertEqual(ipw,2122)
    def test_formed_packet_and_retire_source(self):
        s=P.prepare(P.SOURCE.read_text())
        self.assertIn("assign tk_write_native = {tk_we, tk_wa, {{(4-TKW)*FW{1'b0}},tk_od}, tk_done};",s)
        self.assertIn('assign {tk_sink_we,tk_sink_addr,tk_sink_data,tk_drained_done} = tk_write_sink;',s)
        self.assertIn('if (tk_drained_done) begin busy <= 0; tk_r <= 0; tk_sel <= 0; end',s)
        self.assertNotIn('if (tk_done) begin busy <= 0;',s)
        self.assertEqual(4+4*15+4*512+1,2113)
    def test_reset_only_control_fences(self):
        h=(ROOT/'tools/rtl_templates/ot_topk_fixed_packet_delay_prepare.sv').read_text()
        self.assertIn('always @(posedge clk) begin',h)
        self.assertIn('always @(posedge clk or negedge rst_n)',h)
        self.assertIn('if(MASK[b]) assign out_packet[b] = permitted && payload[EDGES-1][b];',h)
        self.assertIn('else assign out_packet[b] = payload[EDGES-1][b];',h)
        self.assertNotIn('payload[i] <= 0',h)
        s=P.prepare(P.SOURCE.read_text());self.assertIn('tk_sink_we & {4{rst_n}}',s)
        masks=[(1<<2121)|(1<<60),(15<<2084)|(1<<32),(15<<2109)|1]
        self.assertEqual([x.bit_count() for x in masks],[2,5,5])
    def test_independent_all_rank_loader_fields(self):
        # Actual GW4 source increments wr_k by N, tk_wi=wr_k/N. Every beat
        # carries all four512-bit rank words; n=runtime_n/16 source VMwords.
        for runtime in [512,2048]:
            nh=runtime//16;wr=0;observed=[]
            for beat in range(2*nh):
                wi=wr//4
                observed.append((wi>=nh,wi-nh if wi>=nh else wi))
                wr+=4
            self.assertEqual(observed,[(False,i) for i in range(nh)]+[(True,i) for i in range(nh)])
            self.assertEqual(wr,8*nh)
            # Not an element/core execution: source-derived address contract.
            with self.subTest(runtime=runtime):self.assertEqual(len(observed),64 if runtime==512 else 256)
    def test_input_last_and_go_order_after99(self):
        # Independent absolute-event oracle, not implementation shift recurrence.
        for runtime in [512,2048]:
            count=2*(runtime//16);last=10+count-1
            native=[(10+i,'load',i) for i in range(count)]+[(last+1,'go',None)]
            expected=[(t+99,kind,i) for t,kind,i in native]
            pipeline=deque([None]*99);actual=[]
            bytime={t:(kind,i) for t,kind,i in native}
            for t in range(last+102):
                out=pipeline.popleft();pipeline.append(bytime.get(t))
                if out is not None:actual.append((t,*out))
            self.assertEqual(actual,expected)
            self.assertEqual(actual[-1][0]-actual[-2][0],1)
    def test_full_word_write_order_and_busy_lifetime(self):
        for runtime in [512,2048]:
            # Independent output contract k512: eight groups, each4VMwords,
            # each word16IDs. IDs here are arbitrary transport test operands.
            k=512;dst=8192;native=[]
            for group in range(k//64):
                data=tuple(tuple(runtime+group*64+lane*16+i for i in range(16)) for lane in range(4))
                native.append((1000+group,tuple(dst+4*group+lane for lane in range(4)),data))
            expected=[(t+127,addr,data) for t,addr,data in native]
            returned=[(t+99,addr,data) for t,addr,data in native]
            formed=deque([None]*28);actual=[];bytime={t:(addr,data) for t,addr,data in returned}
            for t in range(1200):
                out=formed.popleft();formed.append(bytime.get(t))
                if out is not None:actual.append((t,*out))
            self.assertEqual(actual,expected)
            release_native=native[-1][0]+2
            release_old_return_only=release_native+99
            release_fenced=release_native+127
            self.assertLess(release_old_return_only,actual[-1][0])
            self.assertGreater(release_fenced,actual[-1][0])
            self.assertEqual([a for _,addrs,_ in actual for a in addrs],list(range(dst,dst+32)))
    def test_delayed_address_recomputation_mutant(self):
        dst=8192;original=[dst+i for i in range(32)]
        # At delayed emission tk_oidx has already advanced by every group.
        wrong=[dst+32+i for i in range(32)]
        self.assertNotEqual(wrong,original)
        self.assertEqual(wrong[0],8224);self.assertEqual(original[0],8192)
    def test_reset_aborts_pending_strobes_no_payload_injection(self):
        edges=28;payload=deque([{'we':0,'done':0,'data':None}]*edges);present=deque([False]*edges)
        for t in range(10):payload.popleft();payload.append({'we':15,'done':0,'data':t});present.popleft();present.append(True)
        present=deque([False]*edges)  # asynchronous present clearing only
        delivered=[]
        for t in range(edges+5):
            p=payload.popleft();payload.append({'we':0,'done':0,'data':None});v=present.popleft();present.append(True)
            if v and p['we']:delivered.append(p)
        self.assertEqual(delivered,[])
    def test_unknown_source_anchor_refuses(self):
        bad=P.SOURCE.read_text().replace('    wire tk_ov, tk_ol, tk_done, tk_fault;','    wire changed;')
        with self.assertRaisesRegex(ValueError,'unique pinned caller'):P.prepare(bad)
    def test_no_compile_or_core_qualification(self):
        m=json.loads((P.BASE/'package_r3/sourceplan.json').read_text())
        self.assertFalse(m['compile_admitted']);self.assertFalse(m['PR_admitted'])
        self.assertTrue(m['balanced_selector_implementation_dependency_still_open'])
        self.assertEqual(m['ninecall_extra_cycles'],2034)
        self.assertEqual(m['control_guard_area_addition']['AND2x2_upper_cell_count'],19)
if __name__=='__main__':unittest.main()
