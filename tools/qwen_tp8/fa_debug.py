# usage (repo root): OT_FA_DBG=<bus prefix> python3 tools/qwen_tp8/fa_debug.py  -> FA_DBG/FA_C/FA_V/FA_X field-allocator choices for that bus (full tp8b build, ~5 min)
import sys, time
sys.path.insert(0,'tools')
import die_top_lint as D
D.QWEN_RECIPE='tp8b'; D._QW.clear(); D.QSRC=None
m=D.load_qwen()[1]
