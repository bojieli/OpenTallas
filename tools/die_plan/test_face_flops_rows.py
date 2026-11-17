"""Face pin mapping on a full macro-bearing vehicle's actual row coordinates."""
import pathlib, re, subprocess, unittest
P=pathlib.Path(__file__).with_name('face_flops.tcl')
class Rows(unittest.TestCase):
 def run_rows(self, rows, pins):
  s=P.read_text();m=re.search(r'proc ff_row_index \{row_ys pin_y\} \{\n(.*?)\n\}',s,re.S);self.assertIsNotNone(m)
  code=m.group(0)+'\nset rows {'+' '.join(map(str,rows))+'}\n'
  for y in pins:code+='puts [lindex $rows [ff_row_index $rows '+str(y)+']]\n'
  p=subprocess.run(['tclsh'],input=code,text=True,capture_output=True,check=True);return list(map(int,p.stdout.split()))
 def test_actual_coll_ucie_shifted_rows(self):
  rows=list(range(779760,1637010+1,270))
  self.assertEqual(len(rows),3176)
  self.assertEqual(self.run_rows(rows,[1214688,0,779760,1637280]),[1214460,779760,779760,1637010])
  # Old arithmetic incorrectly clamped this pin to y857250.
  self.assertGreater(abs(1214688-min(len(rows)-1,1214688//270)*270),350000)
 def test_dense_origin_zero_matches_old_mapping(self):
  rows=list(range(0,27001,270));pins=list(range(-100,27500,137))
  self.assertEqual(self.run_rows(rows,pins),[rows[max(0,min(len(rows)-1,y//270))]for y in pins])
 def test_missing_rows_are_not_invented(self):
  self.assertEqual(self.run_rows([100,370,1180,1450],[500,1179,1180,2000]),[370,370,1180,1450])
if __name__=='__main__':unittest.main()
