"""Small arithmetic/address/control tests; no checkpoint/model inference."""
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import hdc_golden as G
from qwen_rom_dspark_tp4 import MatrixTP4
from qwen_rom_dspark_transaction import MemoryOwner, Transaction


def test_raw_rank_fold_before_scale_and_row_geometry():
    rng = np.random.default_rng(101)
    w = SimpleNamespace(codes=rng.integers(-127, 128, (16, 64)).astype(np.float32),
                        scale=G.to_bf16(rng.random(16).astype(np.float32)), n=16)
    x = (rng.normal(size=64) * np.exp2(rng.integers(-8, 20, 64))).astype(np.float32)
    m = MatrixTP4(w, 'columns', groups=128)
    raw = [G.matvec(w.codes[:, r*16:(r+1)*16], x[r*16:(r+1)*16], m.split) for r in range(4)]
    want = G.mul(G.fold(raw), w.scale)
    assert np.array_equal(G.bits(m(x)), G.bits(want))
    # Mutation guard: scale-before-fold is a different numerical contract.
    assert np.any(G.bits(want) != G.bits(G.fold([G.mul(a, w.scale) for a in raw])))
    rows = MatrixTP4(w, 'rows', fused_rows=32, groups=128)
    assert rows.split == G.split_for(8, 64, 128)
    expected = np.concatenate([G.mul(G.matvec(w.codes[r*4:(r+1)*4], x, rows.split), w.scale[r*4:(r+1)*4]) for r in range(4)])
    assert np.array_equal(G.bits(rows(x)), G.bits(expected))


def owners():
    # Same existing K-column / V-row layout, crossing a packed K word at pos15.
    class Layout:
        KV, HD = 2, 4
        def k_elem(self, layer, head, token, dim):
            return ((head * 2 + token // 16) * 4 + dim) * 16 + token % 16
        def v_elem(self, layer, head, token, dim):
            return 256 + (head * 32 + token) * 4 + dim
    return [MemoryOwner(r, l, np.arange(512, dtype=np.uint32) + 10000*r + 1000*l, Layout(), 32)
            for l in range(2) for r in range(4)]


@pytest.fixture(scope='module')
def accept_binary(tmp_path_factory):
    path = tmp_path_factory.mktemp('accept')
    tb = path / 'tb.sv'
    # Existing RTL leaf, Qwen token width (18), B4 NSLOT=4. No new engine RTL.
    tb.write_text('''module tb;
reg clk=0; always #5 clk=~clk;
reg rst_n=0,start_v=0,tokx_v=0,amax_v=0,acc_v=0;
reg [17:0] start_tok=0,tokx_tok=0,amax_tok=0;
reg [1:0]tokx_slot=0,amax_slot=0;
wire done;wire[1:0] a;wire[2:0] n;wire[17:0]bonus;
ot_hdc_accept #(.NSLOT(4),.NW(18)) dut(.clk(clk),.rst_n(rst_n),
.start_v(start_v),.start_tok(start_tok),.tokx_v(tokx_v),.tokx_slot(tokx_slot),.tokx_tok(tokx_tok),
.amax_v(amax_v),.amax_slot(amax_slot),.amax_tok(amax_tok),.acc_v(acc_v),.acc_g(2'd3),
.acc_done(done),.acc_a(a),.n_emit(n),.bonus(bonus));
integer count,i,j,trace;reg[17:0]s[0:3],t[0:3];
initial begin
if(!$value$plusargs("TRACE=%d",trace))$fatal;
repeat(2)@(negedge clk);rst_n=1;
for(count=0;count<4;count=count+1)begin
s[0]=151935;for(i=1;i<4;i=i+1)s[i]=120000+i+trace;
for(i=0;i<4;i=i+1)t[i]=(i<count)?s[i+1]:130000+i+trace;
start_v=1;start_tok=s[0];@(negedge clk);start_v=0;
for(i=1;i<4;i=i+1)begin tokx_v=1;tokx_slot=i;tokx_tok=s[i];@(negedge clk);end
tokx_v=0;
for(i=0;i<4;i=i+1)begin amax_v=1;amax_slot=i;amax_tok=t[i];@(negedge clk);end
amax_v=0;acc_v=1;@(negedge clk);acc_v=0;
if(!done||a!=count||n!=count+1||bonus!=t[count])$fatal(1,"leaf mismatch");
$display("ACCEPT %0d %0d %0d %0d",trace,a,n,bonus);
end
$finish;end
endmodule''')
    binary = path / 'accept.vvp'
    root = Path(__file__).resolve().parents[1]
    subprocess.run(['iverilog', '-g2012', '-s', 'tb', '-o', str(binary), str(tb), str(root / 'rtl/hdc/ot_hdc_accept.sv')], check=True, capture_output=True)
    return binary


@pytest.mark.parametrize('trace', [0, 17, 8191])
def test_actual_accept_leaf_drives_rollback_and_two_loop_steps(accept_binary, trace):
    p = subprocess.run(['vvp', str(accept_binary), f'+TRACE={trace}'], check=True, text=True, capture_output=True)
    receipts = [list(map(int, line.split()[1:])) for line in p.stdout.splitlines() if line.startswith('ACCEPT ')]
    assert len(receipts) == 4
    for _, accepted, n_emit, bonus in receipts:
        banks = owners()
        before = {o.key: o.words.copy() for o in banks}
        tx = Transaction(banks, enabled=True, layers=2)
        tx.begin(10, 15, 151935, [120001+trace, 120002+trace, 120003+trace])
        for o in banks:
            for j in range(4):
                o.words[o.addresses(15+j)] = 0xabc00000 + j
        for rank in range(4):
          for j in range(4):
            tx.target(10, rank, j, 120001+j+trace if j < accepted else 130000+j+trace)
        for o in banks[:-1]:
            tx.write_drain(10, o.key)
        with pytest.raises(ValueError, match='outstanding'):
            tx.commit(10, accepted=accepted, n_emit=n_emit, bonus=bonus)
        tx.write_drain(10, banks[-1].key)
        result = tx.commit(10, accepted=accepted, n_emit=n_emit, bonus=bonus)
        assert result['next_position'] == 15+n_emit and result['pending'] == bonus
        for o in banks:
            expected = before[o.key].copy()
            for j in range(n_emit):
                expected[o.addresses(15+j)] = 0xabc00000+j
            assert np.array_equal(o.words, expected)  # includes adjacent packed K rows
        with pytest.raises(ValueError, match='owned'):
            tx.begin(11, 19, bonus, [1, 2, 3])
        with pytest.raises(ValueError, match='real last-consumer'):
            tx.terminal(10, banks[0].key, consumer_done=True, reverse_done=False)
        for o in banks[:-1]:
            tx.terminal(10, o.key, consumer_done=True, reverse_done=True)
        with pytest.raises(ValueError, match='retained'):
            tx.release(10)
        tx.terminal(10, banks[-1].key, consumer_done=True, reverse_done=True)
        assert tx.release(10) == result
        tx.begin(11, result['next_position'], result['pending'], [1, 2, 3])
        with pytest.raises(ValueError, match='identity'):
            tx.write_drain(10, banks[0].key)
        # Next iteration rewrites every reused row; no rejected row survives.
        for o in banks:
            for j in range(4):
                o.words[o.addresses(result['next_position']+j)] = 0xde000000+j
            tx.write_drain(11, o.key)
        for rank in range(4):
          for j in range(4):
            tx.target(11, rank, j, 100+j)
        tx.commit(11, accepted=0, n_emit=1, bonus=100)
        for o in banks:
            assert np.all(o.words[o.addresses(result['next_position'])] == 0xde000000)
            tx.terminal(11, o.key, consumer_done=True, reverse_done=True)
        tx.release(11)


def test_default_off_cohort_and_bad_accept():
    with pytest.raises(ValueError, match='default-off'):
        Transaction(owners(), layers=2).begin(1, 15, 1, [2, 3, 4])
    with pytest.raises(ValueError, match='every layer'):
        Transaction(owners()[:-1], enabled=True, layers=2)
    tx = Transaction(owners(), enabled=True, layers=2)
    tx.begin(1, 15, 1, [2, 3, 4])
    for rank in range(4):
      for j in range(4):
        tx.target(1, rank, j, j+2)
    for o in tx.owners:
        tx.write_drain(1, o.key)
    with pytest.raises(ValueError, match='disagrees'):
        tx.commit(1, accepted=2, n_emit=3, bonus=4)
    assert tx.lease == 1


def test_serial_isa_has_explicit_norms_and_noncausal_block_counts():
    # Isolate import-time TP/stream geometry from the other test modules.
    root = Path(__file__).resolve().parents[1]
    env = dict(os.environ, QWEN_O4_TP='4', QWEN_O4_GROUPS='6144', HDC_SU_WIDTH='64')
    code = '''
import hdc_isa as I
import hdc_program as P
import hdc_qwen_fullshape_program_w12 as FP
from hdc_qwen_fullshape_placement_w12 import matrix
import qwen_rom_dspark_draft_isa as D
import qwen_rom_verify_program_w12 as V
rows=[matrix(0,n,r,k) for n,r,k in [('qkv',1536,4096),('o',4096,1024),('gu',6144,4096),('down',4096,3072)]]
lay=FP.LayerZero(None,0,rows);lay.norm_fold=False
for slots in (3,7):
 prog=D.layer_program(lay,slots,15,[200000,204096],enabled=True)
 w,desc=D.encode_layer(lay,slots,15,[200000,204096],enabled=True)
 assert len(w)==len(prog)
 assert [V.decode_descriptor(d)['words'] for d in desc[:-1]]==[slots*256]*2
 scores=[f for f in prog if f.get('me_wsrc') and f.get('me_mmode') and f['me_k']==128]
 assert len(scores)==slots and all(f['me_nout']==15+slots for f in scores)
 kvops=[i for i,f in enumerate(prog) if f.get('dst')==I.DST_KV]
 assert max(kvops)<min(i for i,f in enumerate(prog) if f in scores)
 for f in prog:
  assert f.get('barrier')==1 and not f.get('chase')
  assert all(v==0 for k,v in f.items() if k.startswith('me_d_') or k.endswith('_d') or k=='su_d_nin')
 assert any(f.get('c_base')==lay.cb[(0,'in')] and f.get('dst')==I.DST_VM for f in prog)
 print(slots,len(w),len(desc))
'''
    p = subprocess.run([sys.executable, '-c', code], env=dict(env, PYTHONPATH=str(root / 'tools')), text=True, capture_output=True)
    assert p.returncode == 0, p.stdout+p.stderr


def test_serial_loop_retains_frame_when_drafter_or_terminal_is_missing():
    from qwen_rom_dspark_transaction import serial_step
    tx = Transaction(owners(), enabled=True, layers=2)
    class FailedDraft:
        def draft(self, lease, start, pending):
            raise RuntimeError('actual drafter still pending')
    with pytest.raises(RuntimeError, match='still pending'):
        serial_step(tx, FailedDraft(), 71, 15, 5)
    assert tx.lease == 71 and tx.tokens[0] == 5
    with pytest.raises(ValueError, match='still owned'):
        serial_step(tx, FailedDraft(), 72, 15, 5)

    tx = Transaction(owners(), enabled=True, layers=2)
    class Backend:
        def draft(self, lease, start, pending):
            return {'lease': lease, 'tokens': [6, 7, 8]}
        def verify(self, lease, start, tokens):
            for owner in tx.owners:
                for j in range(4):
                    owner.words[owner.addresses(start+j)] = j+1
            return {'lease': lease, 'targets': {r: [6, 7, 99, 42] for r in range(4)},
                    'write_drained': [o.key for o in tx.owners]}
        def accept_leaf(self, lease, tokens, targets):
            return {'lease': lease, 'accepted': 2, 'n_emit': 3, 'bonus': 99}
        def emit(self, lease, tokens):
            assert tokens == (6, 7, 99)
        def terminal_receipts(self, lease):
            return [(lease, o.key, True, True) for o in tx.owners[:-1]]
    with pytest.raises(ValueError, match='retained'):
        serial_step(tx, Backend(), 73, 15, 5)
    assert tx.lease == 73 and tx.tokens == (5, 6, 7, 8)
    tx.terminal(73, tx.owners[-1].key, consumer_done=True, reverse_done=True)
    assert tx.release(73)['next_position'] == 18


def test_rank_disagreement_cannot_commit():
    tx = Transaction(owners(), enabled=True, layers=2)
    tx.begin(1, 15, 5, [6, 7, 8])
    for r in range(4):
        for j in range(4):
            tx.target(1, r, j, 6+j if (r, j) != (3, 0) else 99)
    for o in tx.owners:
        tx.write_drain(1, o.key)
    with pytest.raises(ValueError, match='replicas disagree'):
        tx.commit(1, accepted=3, n_emit=4, bonus=9)
    assert tx.lease == 1


def test_serial_loop_does_not_retag_stale_backend_receipts():
    from qwen_rom_dspark_transaction import serial_step
    tx = Transaction(owners(), enabled=True, layers=2)
    class Stale:
        def draft(self, lease, start, pending):
            return {'lease': lease, 'tokens': [1, 2, 3]}
        def verify(self, lease, start, tokens):
            return {'lease': lease-1, 'targets': {}, 'write_drained': []}
    with pytest.raises(ValueError, match='identity'):
        serial_step(tx, Stale(), 7, 15, 0)
    assert tx.lease == 7 and not tx.targets
