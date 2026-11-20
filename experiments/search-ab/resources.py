"""Exercise CLI protocol and measure resident memory with a fresh worker per run."""
import json
from pathlib import Path
import resource
import subprocess
import sys
import time
from arena import HERE,ROOT
sys.path.insert(0,str(ROOT/'experiments/minimax-validation'))
from check_cli import cases

if len(sys.argv)==3:
    data=sys.stdin.read()
    start=time.monotonic()
    try:
        result=subprocess.run([HERE/'bin'/sys.argv[1]],input=data,text=True,capture_output=True,timeout=3)
        code,output,err=result.returncode,result.stdout,result.stderr
    except subprocess.TimeoutExpired:
        code,output,err=None,'','timeout'
    elapsed=time.monotonic()-start
    rss=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    print(json.dumps([code,output,err,elapsed,rss if sys.platform=='darwin' else rss*1024]))
else:
    for name,data,moves in cases():
        run=subprocess.run([sys.executable,'-B',__file__,sys.argv[1],'--child'],input=data,
                           text=True,capture_output=True,check=True)
        code,output,err,elapsed,rss=json.loads(run.stdout)
        if moves is None:
            passed=code==1 and output==''
        else:
            from match import OFFSETS
            allowed=[f'{r+1} {c-OFFSETS[r]+1}\n' for r,c in moves] or ['0 0\n']
            passed=code==0 and output in allowed
        print(json.dumps(dict(case=name,passed=passed and not err and elapsed<=3 and rss<500_000_000,
                              move=output.strip(),wall_s=elapsed,rss_bytes=rss)),flush=True)
