"""Compiler integration tests, not RTL/physical qualification."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from qwen_static_schedule.calendar import compile_calendar, sha, ScheduleError
from qwen_static_schedule.test_dvm_head_onward import receipt
from qwen_static_schedule.test_su_pinreg import CONTRACTS
from qwen_static_schedule import su_pinreg as S, dvm_head_onward as H


class CompilerFold(unittest.TestCase):
    def vehicle(self, root, pinreg=1):
        def write(name, obj):
            p = root/name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(obj))
        write(H.RECEIPT, receipt())
        write(S.DELTA, dict(schema=S.SCHEMA, master='qfd_sp_su64_sfu', su_op_latency_delta=0, contracts=CONTRACTS))
        write('graph.json', dict(buses=[['cp', 0, 56, [['tt', 'cp'], ['su', 'cp']]],
                                      ['active', 0, 1, [['su', 'cp_active'], ['tt', 'cp_active']]]]))
        write('stages.json', dict(cp=2, active=3))
        (root/'native.sv').write_text('module native; wire cp; endmodule\n')
        (root/'p.hex').write_text('1\n1\n')
        src={n:sha(root/n) for n in (H.RECEIPT,S.DELTA,'graph.json','stages.json','native.sv')}
        P=1000
        ev=[]
        for role,edge in [('read',1),('write',17),('done',21),('active_rise',1),('active_fall',21)]:
            ev.append(dict(id=role,kind='native_port',resource=role,offset_fs=edge*P,b2_copy_role=role))
        ev += [dict(id='cp',kind='copy_issue',resource='command',offset_fs=0,cp56_hex=f'{(4<<49)|1:014x}'),
               dict(id='word',kind='native_port',resource='word',offset_fs=50*P,produces=['word'])]
        for e in ev:
            e.update(rtl_source='native.sv',rtl_port='cp',rtl_module='native',rtl_instance='u_native')
        instructions=[]
        for pc in range(2):
            events=copy.deepcopy(ev)
            events[-1]['produces']=[f'word{pc}']
            instructions.append(dict(stage=0,pc=pc,word='1',unit=1,clock='core',rtl_instance='u_native',rtl_module='native',
                                     events=events,b2_head_event_ids=['word']))
        return dict(schema='opentallas.qwen-native-microcalendar.v1',source_sha256=src,
                    clocks={'core':dict(period_fs=P,phase_fs=0)},
                    resources={k:dict(capacity=1,clock='core') for k in ('read','write','done','active_rise','active_fall','command','word','copy_engine')},
                    instructions=instructions,deadline_fs=1000000,
                    b2_configuration=dict(base_onward=1,base_pinreg=0,onward=2,pinreg=pinreg,head_clock='core',
                      allocator_graph=dict(path='graph.json',sha256=src['graph.json']),
                      allocator_stage_of=dict(path='stages.json',sha256=src['stages.json']),
                      copy_command_bus='cp',copy_active_bus='active',copy_resource='copy_engine'))

    def test_real_compiler_reservations_and_ports_move(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            c=self.vehicle(root)
            a=compile_calendar([root/'p.hex'],c,root)
            base=copy.deepcopy(c);base['b2_configuration']['pinreg']=0;base['b2_configuration']['onward']=1
            b=compile_calendar([root/'p.hex'],base,root)
            self.assertEqual([i['time_fs']//1000 for i in a['issues']],[0,28])
            self.assertEqual([i['time_fs']//1000 for i in b['issues']],[0,26])
            e={e['id']:e['time_fs']//1000 for e in a['events'] if e['pc']==0}
            self.assertEqual({k:e[k] for k in ('read','write','done','active_rise','active_fall','word')},
                             dict(read=3,write=20,done=23,active_rise=2,active_fall=23,word=73))
            self.assertEqual(a['b2_timing_applied']['word_shift_edges'],23)
            # A fixed issue two edges too early cannot be silently retimed.
            c['instructions'][1]['issue_at_fs']=26000
            with self.assertRaises(ScheduleError):compile_calendar([root/'p.hex'],c,root)

    def test_missing_receipt_phase_and_unclassified_copy_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);c=self.vehicle(root)
            for change in ('receipt','stage','role','clock'):
                bad=copy.deepcopy(c)
                if change=='receipt':del bad['source_sha256'][S.DELTA]
                if change=='stage':bad['b2_configuration']['copy_command_bus']='missing'
                if change=='role':bad['instructions'][0]['events'][0].pop('b2_copy_role')
                if change=='clock':
                    bad['clocks']['su']=dict(period_fs=1111,phase_fs=0)
                    bad['resources']['copy_engine']['clock']='su'
                with self.subTest(change=change),self.assertRaises(ScheduleError):
                    compile_calendar([root/'p.hex'],bad,root)

if __name__=='__main__':unittest.main()
