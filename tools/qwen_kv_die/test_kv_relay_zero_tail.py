"""KV-FUNC-OPENS: relay width-padding output contract admits only unread zero MSB tails over live lanes."""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import die_port_bind as P  # noqa: E402
import kv_relay_zero_tail as Z  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
# r0: 17-bit live lane in a 36-bit word through two stages (pin-repair-like full-width hop), tail to a private line net.
# r2: chain-head all-zero lane, consumer reads the low 20 bits.  r3: zero HOLE inside a live word (bit 5) -> refused.
DIE = '''module die(ck,a,c,y,z,h);
input wire ck;
input wire [16:0] a;
input wire [34:0] c;
output wire [16:0] y;
output wire [19:0] z;
output wire [29:0] h;
wire [35:0] mid;
wire [18:0] line_2;
wire [15:0] line_3;
wire [5:0] hole_o;
qkd_rlys_36 r_up(.ck(ck),.a({19'b0,a}),.b(mid));
qkd_rlys_36 r0(.ck(ck),.a(mid),.b({line_2,y}));
qkd_rlys_36 r2(.ck(ck),.a(36'b0),.b({line_3,z}));
qkd_rlys_36 r3(.ck(ck),.a({c[34:30],1'b0,c[29:0]}),.b({hole_o,h}));
endmodule
'''


def copy_root(tmp):
    root = Path(tmp) / 'root'
    for rel in Z.SOURCES:
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / rel, root / rel)
    return root


class RelayZeroTail(unittest.TestCase):
    def test_positive_tail_and_chain_head(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_root(tmp)
            die = Path(tmp) / 'die.v'
            die.write_text(DIE)
            doc = Z.derive(die, root)
            c = doc['relay_zero_tail_contract']
            self.assertEqual(P.pad_bits(doc['instances']['r0']['ports']['b'], 36), set(range(17, 36)))
            self.assertEqual(P.pad_bits(doc['instances']['r2']['ports']['b'], 36), set(range(20, 36)))
            self.assertNotIn('r3', doc['instances'])          # bit 30 is a zero hole below live bits
            self.assertNotIn('r_up', doc['instances'])        # its outputs are read by r0
            self.assertEqual(c['admitted_bits'], 19 + 16)
            self.assertEqual(c['refused_unread_candidates'], {'dynamic_or_nonzero_origin': 5, 'zero_not_msb_width_padding': 1})

    def test_dynamic_or_read_bits_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_root(tmp)
            die = Path(tmp) / 'die.v'
            die.write_text(DIE.replace("19'b0,a", "19'b1,a"))   # nonzero literal: no admission for r0 tail
            doc = Z.derive(die, root)
            self.assertNotIn('r0', doc['instances'])
            # a reader on the tail removes it from the candidates entirely
            die.write_text(DIE.replace('output wire [29:0] h;', 'output wire [29:0] h;\nwire [18:0] rd;\n'
                                       'qkd_rlys_36 r9(.ck(ck),.a({17\'b0,line_2}),.b({rd,y2}));')
                           .replace('wire [5:0] hole_o;', 'wire [5:0] hole_o;\nwire [16:0] y2;'))
            doc = Z.derive(die, root)
            self.assertNotIn('b', doc['instances'].get('r0', {}).get('ports', {}))

    def test_source_change_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_root(tmp)
            die = Path(tmp) / 'die.v'
            die.write_text(DIE)
            p = root / 'rtl/qwen_sys/kv_rly_std_20261016/qkd_rlys.sv'
            p.write_text(p.read_text() + '\n// edited\n')
            with self.assertRaisesRegex(ValueError, 'relay source changed'):
                Z.derive(die, root)


if __name__ == '__main__':
    unittest.main()
