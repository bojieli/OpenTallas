#pragma once
#include <cstdint>
// Default-off hooks for the copied host. Unknown scopes fall through to the
// host's original pair/HEAD bindings. No second ROM ABI or word conversion.
bool dsrom_s81_qe_register_rom(const char* instance);
bool dsrom_s81_qe_register_cfg();
bool dsrom_s81_qe_rom_read(int logical_address,std::uint32_t* native274);
bool dsrom_s81_qe_cfg_read(int address,long long& native48);
