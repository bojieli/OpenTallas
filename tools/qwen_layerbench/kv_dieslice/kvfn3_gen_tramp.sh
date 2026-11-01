#!/bin/bash
# gen_tramp.sh EXE OBJ -> tramp.S : one trampoline per model symbol OBJ needs (Vtb_kvslice / VerilatedContext / Verilated).
set -euo pipefail
EXE=$1; OBJ=$2
nm --defined-only $EXE > exe.nm
{
echo '.text'
syms=$(nm -u $OBJ | awk '{print $2}' | grep -E '^_ZN(11Vtb_kvslice|16VerilatedContext|9Verilated)')
for s in $syms; do
  off=$(awk -v s=$s '$3==s && ($2=="T"||$2=="t"||$2=="W") {print $1; exit}' exe.nm); test -n "$off" || { echo "missing $s" >&2; exit 1; }
  echo ".globl $s"; echo ".type $s,@function"; echo "$s: jmp *p_$s(%rip)"
done
echo '.globl kvfn3_tramp_init'; echo '.type kvfn3_tramp_init,@function'; echo 'kvfn3_tramp_init:'
for s in $syms; do
  off=$(awk -v s=$s '$3==s && ($2=="T"||$2=="t"||$2=="W") {print $1; exit}' exe.nm)
  echo "  movabs \$0x$off, %rax"; echo "  add %rdi, %rax"; echo "  mov %rax, p_$s(%rip)"
done
echo '  ret'
moff=$(awk '$3=="main" && $2=="T" {print $1; exit}' exe.nm)
echo '.section .rodata'; echo '.globl kvfn3_exe_main_off'; echo "kvfn3_exe_main_off: .quad 0x$moff"
echo '.data'
for s in $syms; do echo "p_$s: .quad 0"; done
echo '.section .note.GNU-stack,"",@progbits'
} > tramp.S
echo "TRAMP $(echo $syms | wc -w) symbols, exe main 0x$moff"
