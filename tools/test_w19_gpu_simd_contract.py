import unittest

from w19_gpu_simd_contract import (admit_controller_request,build,chunk_program,
                                  controller_run,index_loop_descriptors,instruction,schedule_warps)


class GPUContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.c=build()

    def test_actual_tp96_source_order_and_coverage(self):
        self.assertEqual(len(self.c['graph']),2213)
        self.assertEqual(self.c['counts']['local'],800)
        self.assertEqual(self.c['counts']['mv'],1103)
        for i,node in enumerate(self.c['graph']):
            self.assertEqual(node['sequence'],i)
            self.assertEqual(node['predecessor'],i-1 if i else None)
            self.assertFalse(node['lowering']['connected_exactness'])

    def test_full_hc_no_precision_or_lane_credit(self):
        hc=self.c['hc']
        self.assertEqual(sum(w['chunks'] for w in hc['waves']),2560)
        self.assertEqual(sum(w['projection']['scalar_products'] for w in hc['waves'])*24,491520)
        self.assertEqual(hc['coefficient_hbm_bytes_operator'],24*20480*4)
        self.assertEqual(hc['explicit_divisions_operator'],649)
        self.assertFalse(self.c['ALU']['FMA'])
        self.assertEqual(self.c['organisation']['implemented_general_simd_lanes'],0)

    def test_rf_and_shared_capacity_and_ports(self):
        rf=self.c['register_file'];smem=self.c['shared_memory']
        self.assertEqual(rf['physical_capacity_bytes_die'],64*128*256//8*32)
        self.assertEqual(rf['read_bits_cycle_sm'],2*128*32)
        self.assertLessEqual(smem['hc_live_bytes'],smem['capacity_bytes_sm'])
        for wave in self.c['hc']['waves']:
            s=wave['projection']
            self.assertGreaterEqual(s['cycles'],s['shared_issue_cycles'])
            self.assertEqual(sum(s['rf_write_slots']),s['instructions']['LDS32']+s['instructions']['LDS_PACKED_BF16']+s['instructions']['BF16_WIDEN']+s['instructions']['FMUL']+s['instructions']['FADD']+s['instructions']['SHFL_PAIR'])

    def test_scoreboard_dependency_cost(self):
        independent=[instruction('LDS32','x',lat=2),instruction('FMUL','a',['x','x'],9),instruction('FMUL','b',['x','x'],9)]
        dependent=[instruction('LDS32','x',lat=2),instruction('FMUL','a',['x','x'],9),instruction('FMUL','b',['a','x'],9)]
        self.assertGreater(schedule_warps(dependent,1)['cycles'],schedule_warps(independent,1)['cycles'])
        with self.assertRaises(ValueError):schedule_warps([instruction('FADD','x',['missing'],9)],1)
        with self.assertRaises(ValueError):schedule_warps(chunk_program(),33)

    def test_canonical_zero_initial_add_and_constant_scoreboard(self):
        for norm in [False,True]:
            program=chunk_program(norm)
            adds=[op for op in program if op['op']=='FADD']
            self.assertEqual(adds[0]['src'],['@F32_POS_ZERO','p0'])
            for k in range(1,8):self.assertEqual(adds[k]['src'],['sum',f'p{k}'])
            schedule_warps(program,1)
        constants=self.c['numerical_contract']['constants']
        self.assertEqual(constants['@F32_POS_ZERO']['bits'],'0x00000000')
        bad=chunk_program();next(op for op in bad if op['op']=='FADD')['src']=['p0']
        with self.assertRaisesRegex(ValueError,'arity'):schedule_warps(bad,1)
        bad=chunk_program();next(op for op in bad if op['op']=='FADD')['src']=['@F32_NEG_ZERO','p0']
        with self.assertRaisesRegex(ValueError,'unknown constant'):schedule_warps(bad,1)
        with self.assertRaisesRegex(ValueError,'constant'):
            schedule_warps([instruction('LDS32','@F32_POS_ZERO',lat=2)],1)

    def test_tree_pairing_masks_and_bf16_halves(self):
        program=chunk_program()
        self.assertEqual([o['attributes']['half'] for o in program if o['op']=='BF16_WIDEN'],[0,1]*4)
        self.assertEqual([o['attributes']['offset'] for o in program if o['op']=='SHFL_PAIR'],[1,2,4,8,16])
        self.assertEqual(program[-1]['attributes']['predicate'],'lane == 0')

    def test_controller_lengths_and_aperture_controls(self):
        for bad in [0,17,31]:
            with self.assertRaises(ValueError):admit_controller_request(0,bad)
        with self.assertRaises(ValueError):admit_controller_request(0,2,write=True)
        with self.assertRaises(ValueError):admit_controller_request((1<<27)-1,2)
        admit_controller_request((1<<27)-16,16)
        commands=controller_run((1<<24)+1,65)
        self.assertEqual([c['sectors'] for c in commands],[16,16,16,16,1])
        self.assertEqual(sum(c['sectors'] for c in commands),65)
        with self.assertRaises(ValueError):admit_controller_request(1<<24,1,AW=24)

    def test_finite_index_loops_preserve_all_global_ids(self):
        for n in [769,524288,1048576,1048577]:
            total=0
            for rank in range(96):
                loops=index_loop_descriptors(n,rank)
                cursor=0
                for loop in loops:
                    self.assertEqual(loop['local_base'],cursor)
                    self.assertLessEqual(loop['count'],1024)
                    for i in [0,loop['count']-1]:
                        local=cursor+i;g=(local//8)*768+rank*8+local%8
                        self.assertLess(g,n);self.assertEqual((g//8)%96,rank)
                    cursor+=loop['count']
                total+=cursor
            self.assertEqual(total,n)

    def test_selection_format_and_no_false_freeze(self):
        self.assertEqual(self.c['selection']['score_bits'],32)
        self.assertEqual(self.c['selection']['id_bits'],32)
        self.assertIsNone(self.c['full_token_cycles'])
        self.assertFalse(self.c['full_token_qualified'])


if __name__=='__main__':unittest.main()
