from __future__ import annotations

from dataclasses import replace
import struct
import zlib

import pytest

from compiler.tensor_accelerator import production_command as command_abi
from compiler.tensor_accelerator.production_command import (
    Engine,
    LEGACY_ABI_MINOR,
    MATMUL_FINAL,
    MATMUL_INIT,
    Opcode,
    ProductionCommand,
    ProductionCommandError,
    command_abi as read_command_abi,
    decode,
    disassemble,
    encode,
)


def _commands() -> tuple[ProductionCommand, ...]:
    return (
        ProductionCommand(
            index=0,
            opcode=Opcode.DMA_HBM_TO_SRAM,
            engine=Engine.DMA,
            kernel_index=7,
            source0=0x1000,
            destination=0x2000,
            size0=32768,
        ),
        ProductionCommand(
            index=1,
            opcode=Opcode.MATMUL_BF16_TILE,
            engine=Engine.TENSOR,
            flags=MATMUL_INIT | MATMUL_FINAL,
            kernel_index=7,
            source0=0x0000,
            source1=0x2000,
            destination=0x8000,
            auxiliary=0xC000,
            size0=1,
            size1=64,
            size2=256,
        ),
        ProductionCommand(
            index=2,
            opcode=Opcode.COMPLETE,
            engine=Engine.CONTROL,
        ),
    )


def _repair_crcs(payload: bytearray, command_index: int) -> None:
    offset = command_abi.HEADER.size + command_index * command_abi.COMMAND_WITH_CRC.size
    prefix = payload[offset : offset + command_abi.COMMAND_PREFIX.size]
    struct.pack_into("<I", payload, offset + len(prefix), zlib.crc32(prefix) & 0xFFFFFFFF)
    body = payload[command_abi.HEADER.size :]
    struct.pack_into("<I", payload, 16, zlib.crc32(body) & 0xFFFFFFFF)


def test_v21_command_stream_has_frozen_widths_and_exact_round_trip() -> None:
    commands = _commands()
    payload = encode(commands)
    assert command_abi.HEADER.size == 32
    assert command_abi.COMMAND_WITH_CRC.size == 64
    assert len(payload) == 32 + 3 * 64
    assert decode(payload) == commands
    assert encode(decode(payload)) == payload
    assert disassemble(commands).splitlines() == [
        "OTTA-ISA 2.1",
        "# index opcode engine flags kernel src0 src1 dst aux size0 size1 size2 size3",
        "00000 DMA_HBM_TO_SRAM DMA 0x0000 7 0x0000000000001000 "
        "0x0000000000000000 0x0000000000002000 0x0000000000000000 "
        "32768 0 0 0",
        "00001 MATMUL_BF16_TILE TENSOR 0x0003 7 0x0000000000000000 "
        "0x0000000000002000 0x0000000000008000 0x000000000000c000 "
        "1 64 256 0",
        "00002 COMPLETE CONTROL 0x0000 4294967295 0x0000000000000000 "
        "0x0000000000000000 0x0000000000000000 0x0000000000000000 "
        "0 0 0 0",
    ]


def test_v21_adds_bounded_indexed_dma_and_rmsnorm_without_breaking_v20() -> None:
    commands = (
        ProductionCommand(
            index=0,
            opcode=Opcode.DMA_HBM_INDEXED_TO_SRAM,
            engine=Engine.DMA,
            kernel_index=0,
            source0=0x1000,
            source1=0x2000,
            destination=0x3000,
            size0=8192,
            size1=8192,
            size2=151936,
            size3=4,
        ),
        ProductionCommand(
            index=1,
            opcode=Opcode.RMSNORM_BF16,
            engine=Engine.VECTOR,
            kernel_index=1,
            source0=0x3000,
            source1=0x4000,
            destination=0x5000,
            size0=1,
            size1=4096,
            size2=0x358637BD,
        ),
        ProductionCommand(
            index=2,
            opcode=Opcode.COMPLETE,
            engine=Engine.CONTROL,
        ),
    )
    payload = encode(commands)
    assert read_command_abi(payload) == (2, 1)
    assert decode(payload) == commands
    with pytest.raises(ProductionCommandError, match="requires ABI 2.1"):
        encode(commands, abi_minor=LEGACY_ABI_MINOR)

    legacy = encode(_commands(), abi_minor=LEGACY_ABI_MINOR)
    assert read_command_abi(legacy) == (2, 0)
    assert decode(legacy) == _commands()
    assert disassemble(_commands(), abi_minor=LEGACY_ABI_MINOR).startswith(
        "OTTA-ISA 2.0\n"
    )


def test_encoder_rejects_nonterminal_duplicate_and_malformed_commands() -> None:
    dma, matmul, complete = _commands()
    with pytest.raises(ProductionCommandError, match="nonempty"):
        encode(())
    with pytest.raises(ProductionCommandError, match="exactly once"):
        encode((dma, replace(matmul, index=1)))
    with pytest.raises(ProductionCommandError, match="exactly once"):
        encode((replace(complete, index=0), replace(complete, index=1)))
    with pytest.raises(ProductionCommandError, match="contiguous"):
        encode((replace(dma, index=1), replace(complete, index=1)))
    with pytest.raises(ProductionCommandError, match="engine differs"):
        encode((replace(dma, engine=Engine.TENSOR), replace(complete, index=1)))
    with pytest.raises(ProductionCommandError, match="illegal DMA"):
        encode((replace(dma, size1=1), replace(complete, index=1)))
    with pytest.raises(ProductionCommandError, match="illegal BF16 MATMUL"):
        encode((dma, replace(matmul, flags=4), complete))
    indexed = ProductionCommand(
        index=0,
        opcode=Opcode.DMA_HBM_INDEXED_TO_SRAM,
        engine=Engine.DMA,
        kernel_index=0,
        size0=2,
        size1=2,
        size2=1,
        size3=4,
    )
    with pytest.raises(ProductionCommandError, match="illegal indexed DMA"):
        encode((replace(indexed, size3=8), replace(complete, index=1)))
    rmsnorm = ProductionCommand(
        index=0,
        opcode=Opcode.RMSNORM_BF16,
        engine=Engine.VECTOR,
        kernel_index=0,
        size0=1,
        size1=4096,
        size2=0x358637BD,
    )
    with pytest.raises(ProductionCommandError, match="illegal BF16 RMSNorm"):
        encode((replace(rmsnorm, size2=0), replace(complete, index=1)))
    with pytest.raises(ProductionCommandError, match="outside its ABI width"):
        encode((replace(dma, size0=1 << 32), replace(complete, index=1)))
    with pytest.raises(ProductionCommandError, match="outside its ABI width"):
        encode((replace(dma, source0=True), replace(complete, index=1)))
    with pytest.raises(ProductionCommandError, match="ABI enums"):
        encode((replace(dma, opcode=1), replace(complete, index=1)))  # type: ignore[arg-type]


def test_decoder_rejects_header_payload_record_and_opcode_corruption() -> None:
    payload = encode(_commands())
    with pytest.raises(ProductionCommandError, match="immutable bytes"):
        decode(bytearray(payload))  # type: ignore[arg-type]

    bad_header = bytearray(payload)
    bad_header[0] ^= 1
    with pytest.raises(ProductionCommandError, match="magic or ABI"):
        decode(bytes(bad_header))

    bad_payload_crc = bytearray(payload)
    bad_payload_crc[command_abi.HEADER.size + 8] ^= 1
    with pytest.raises(ProductionCommandError, match="payload CRC32"):
        decode(bytes(bad_payload_crc))

    bad_record_crc = bytearray(payload)
    record_crc_offset = command_abi.HEADER.size + command_abi.COMMAND_PREFIX.size
    bad_record_crc[record_crc_offset] ^= 1
    body = bad_record_crc[command_abi.HEADER.size :]
    struct.pack_into("<I", bad_record_crc, 16, zlib.crc32(body) & 0xFFFFFFFF)
    with pytest.raises(ProductionCommandError, match="command 0 CRC32"):
        decode(bytes(bad_record_crc))

    unknown_opcode = bytearray(payload)
    unknown_opcode[command_abi.HEADER.size] = 0x7E
    _repair_crcs(unknown_opcode, 0)
    with pytest.raises(ProductionCommandError, match="unknown opcode or engine"):
        decode(bytes(unknown_opcode))

    no_terminal = bytearray(payload)
    last = command_abi.HEADER.size + 2 * command_abi.COMMAND_WITH_CRC.size
    no_terminal[last] = int(Opcode.DMA_HBM_TO_SRAM)
    no_terminal[last + 1] = int(Engine.DMA)
    struct.pack_into("<I", no_terminal, last + 8, 0)
    struct.pack_into("<I", no_terminal, last + 4, 2)
    struct.pack_into("<Q", no_terminal, last + 12, 0)
    struct.pack_into("<Q", no_terminal, last + 28, 0)
    struct.pack_into("<I", no_terminal, last + 44, 1)
    _repair_crcs(no_terminal, 2)
    with pytest.raises(ProductionCommandError, match="exactly once"):
        decode(bytes(no_terminal))
