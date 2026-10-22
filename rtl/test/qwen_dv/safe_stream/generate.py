from pathlib import Path
r=Path(__file__).resolve().parents[4]
for src,name in [('qfd_dv_stream.sv','legacy'),('qfd_dv_stream_rsafe.sv','safe')]:
 text=(r/'rtl/qwen_dv'/src).read_text().replace('module qfd_dv_stream','module stream_'+name,1)
 (Path(__file__).parent/(name+'.sv')).write_text(text)
