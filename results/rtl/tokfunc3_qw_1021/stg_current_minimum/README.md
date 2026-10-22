# Current flat-slice minimum functional rerun

Five cases were rerun on the retained source-bound STG4 positive binary, SHA256 recorded in result.json. All28 nonbench inputs match current Qwen source revisions2eaaa79c7 and4a1cdc7c7 byte-for-byte, so recompilation would repeat identical source/parameters. Real layer0 QK/RoPE and output projection/ARF pass; LM head and embedding component cases pass; the RoPE-late causal negative produces the required numerical/fault failure. Raw bench outputs and the replay adapter are retained. The fleet unit3963631 on EP7 exits0 only after all five expected explicit verdicts.

The first portable attempt omitted compiler model JSON files and exited before any RTL replay. Those exact existing6.2MB dependencies were staged, and this retry used a fresh output directory; the setup failure remains on the fleet. No progressing compile was cancelled. Earlier client1351234 was still unadmitted when replaced with this portable same-binary run.

These are minimal current-source flat-slice component results. LM and embedding here use the existing component operands; this does not claim those are the real token's full checkpoint data. The physical S8 parent/tail1 SCALE_LAT7 result age, actual HP13 crossing, corrected73-record programme, and complete current-die token remain separate obligations.
