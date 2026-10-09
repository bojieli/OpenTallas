"""Boot serializer must preserve released codes/scales and RAW atom addressing."""
import io
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import engram_boot_image as B


def test_crc_known_vector_and_payload_preservation():
    assert B.crc32_msb(b"123456789") == 0x0376e6e7
    row = bytes(range(256)) + b"\x7f" + b"padding"
    packed = B.packed_row(row)
    assert len(packed) == 264
    assert packed[:257] == row[:257]
    assert int.from_bytes(packed[257:261], "little") == B.crc32_msb(row[:257])
    assert packed[261:] == bytes(3)


def test_raw_walk_across_unaligned_rows_and_columns(monkeypatch):
    # Exercise a descriptor boundary inside a 264-byte row, as happens at
    # production nb limits, and column starts at offsets 0/8/16/24 in atoms.
    monkeypatch.setattr(B, "MAX_SEGMENT_BYTES", 256)
    rows = [bytes([n]) * 257 + bytes(7) for n in range(1, 8)]
    columns = [rows[:3], rows[3:]]
    stream = B.host_records((io.BytesIO(b"".join(col)), len(col)) for col in columns)
    image, completions = {}, []
    remaining, atom, tag = 0, 0, 0
    for cls, data in stream:
        if cls == 1:
            assert remaining == 0
            desc = int.from_bytes(data, "little")
            assert desc & 0xff == 0x80  # RAW, fenced
            addr = (desc >> 16) & 0xffffffff
            assert addr >> 30 == 3
            atom = addr & ~B.BOOT_ATOM
            remaining = (desc >> 144) & 0xffffff
            tag = (desc >> 8) & 255
        elif cls == 2:
            assert cls == 2 and remaining
            for start in (0, 32):
                if remaining:
                    assert atom not in image
                    image[atom] = data[start:start + 32]
                    atom += 1
                    remaining -= 1
            if not remaining:
                completions.append(tag)
        else:
            assert cls == 0 and not remaining
            csr = int.from_bytes(data, "little")
            assert csr & 255 == 2
            assert (csr >> 128) & 3 == 3
            assert (csr >> 64) & 0xffffffff == len(image)
            expected_xor = 0
            for address, sector in image.items():
                expected_xor ^= address
                for start in range(0, 32, 4):
                    expected_xor ^= int.from_bytes(sector[start:start + 4], "little")
            assert (csr >> 96) & 0xffffffff == expected_xor
    actual = b"".join(image[n] for n in range(len(image)))
    expected = b"".join(b"".join(B.packed_row(row) for row in col).ljust(
        (len(col) * 264 + 31) // 32 * 32, b"\0") for col in columns)
    assert actual == expected
    assert completions == list(range(len(completions)))
    assert B.column_bases([3, 4]) == [0, 800]


def test_reject_truncation_trailing_data_and_address_overflow():
    with pytest.raises(ValueError, match="truncated"):
        list(B.column_chunks(io.BytesIO(bytes(263)), 1))
    with pytest.raises(ValueError, match="trailing"):
        list(B.column_chunks(io.BytesIO(bytes(265)), 1))
    with pytest.raises(ValueError, match="overflow"):
        B.raw_descriptor(B.REGION_ATOMS - 1, 64, 0)


def test_rowstripe_payload_pc_identity_and_capacity():
    # Evaluate the actual unified-model function in isolation; the minimum
    # component does not need unrelated rack history or whole-model inputs.
    import ast
    from types import SimpleNamespace
    source=Path(__file__).resolve().parents[1]/'tools/uarch_model.py'
    tree=ast.parse(source.read_text())
    fn=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='dsrom_engram_rowstripe_model')
    namespace={}
    exec(compile(ast.Module(body=[fn],type_ignores=[]),str(source),'exec'),namespace)
    M=SimpleNamespace(dsrom_engram_rowstripe_model=namespace['dsrom_engram_rowstripe_model'])
    counts=[65,67,69,71,73,75]  # cross both stack and all32PC boundaries
    rows=[bytes([(i+j)%256 for j in range(256)])+bytes([127])+bytes(7)
          for i in range(sum(counts))]
    chunks=[];start=0
    for count in counts:
        chunks.extend(B.column_chunks(io.BytesIO(b''.join(rows[start:start+count])),count,True))
        start+=count
    image=b''.join(chunks)
    assert len(image)==sum(counts)*288
    bases=B.column_bases(counts,True)
    assert bases==[sum(counts[:i])*288 for i in range(6)]
    pc_image={}
    for atom in range(len(image)//32):
        row,index=divmod(atom,9)
        stack,pc,local=row%2,(row//2)%32,(row//64)*9+index
        key=(stack,pc,local)
        assert key not in pc_image
        pc_image[key]=image[atom*32:(atom+1)*32]
    for row,payload in enumerate(rows):
        actual=b''.join(pc_image[(row%2,(row//2)%32,(row//64)*9+i)] for i in range(9))
        assert actual[:264]==B.packed_row(payload)
        assert actual[264:]==bytes(24)
    model=M.dsrom_engram_rowstripe_model()
    assert model['matched_context_capacity_pass']
    assert model['total_bytes']>model['historical_total_bytes']
    assert model['table_increase_percent']==pytest.approx(100/11)
    assert not M.dsrom_engram_rowstripe_model(users=1000)['matched_context_capacity_pass']
