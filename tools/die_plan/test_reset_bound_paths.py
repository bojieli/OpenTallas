import unittest
from reset_tree import _core_instance_match,project_core_paths,ResetError

class ResetBoundPaths(unittest.TestCase):
    def test_exact_projection_keeps_tree_and_is_idempotent(self):
        prefix='rtr_place rst_root_n {*u_rst_in[./]*} 1736.16 1315.936 rst_entry\n'
        match=_core_instance_match(['u_xc_Q2'])
        old=prefix+'# Equal-depth reset target for hard core u_xc_Q2.rst_n\n'+f'foreach i [$ff_blk getInsts] {{ set n [$i getName]; if {{{match}}} {{ lappend rtr_ci $i }} }}\n'
        rows=[dict(inst='u_xc_Q2',physical_inst='u_bound.u_u_xc_Q2')]
        new=project_core_paths(old,rows)
        self.assertTrue(new.startswith(prefix))
        self.assertIn('{u_bound.u_u_xc_Q2}',new)
        self.assertEqual(project_core_paths(new,rows),new)
        wrong=old.replace(match,_core_instance_match(['u_xc_Q2','other']))
        with self.assertRaises(ResetError):project_core_paths(wrong,rows)

if __name__=='__main__':unittest.main()
