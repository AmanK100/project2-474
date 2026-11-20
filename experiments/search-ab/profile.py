"""Measure fixed-depth equivalence and nodes, then depth under a normal search clock."""
import json
import random
import subprocess
from pathlib import Path
from check import HERE, ROOT, PREV, records, board_from
import match


def probe(name, depth, board, timed=False):
    b=HERE/'bin'/f'{name}-probe'
    run=subprocess.run([b, *(['--timed'] if timed else [])],input=f'{depth}\n'+board,
                       text=True,capture_output=True,check=True,timeout=3 if timed else 60)
    score,square,d,nodes=map(int,run.stdout.splitlines()[-1].split())
    return dict(score=score,square=square,depth=d,nodes=nodes)


rng=random.Random(276010)
cases=[(v['case'],v['board']) for v in records(PREV/'profiles.jsonl')]
for n in range(16):
    pos=None
    while pos is None or len(match.legal_moves(*pos))<2:
        pos=match.opening(rng,(12,32,52,64)[n%4])
    cases.append((f'fresh-{n}',match.board_input(*pos)))
for label,data in cases:
    board=board_from(data)
    depth=min(list(board.values()).count(0), 9)
    answers={name:probe(name,depth,data) for name in ('control','pvs')}
    assert answers['control']['score']==answers['pvs']['score']
    for m in set(v['square'] for v in answers.values()):
        sq=divmod(m,16)
        choices=match.legal_moves(board,1)
        child=board.copy()
        match.place(child,1,sq,choices[sq])
        child_score=probe('control',depth-1,match.board_input(child,2))['score']
        assert -child_score==answers['control']['score']
    print(json.dumps(dict(kind='fixed',case=label,**answers)),flush=True)
for label,data in cases[:4]:
    depth=data.split().count('0')
    answers={name:probe(name,depth,data,True) for name in ('control','pvs','phase')}
    print(json.dumps(dict(kind='timed',case=label,**answers)),flush=True)
