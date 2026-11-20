"""Compare a candidate's moves with exhaustive minimax and certified endgame outcomes."""
import argparse
import json
import random
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PREV = ROOT / "experiments/minimax-validation/results"
sys.path.insert(0, str(ROOT / "tests"))
import match
from audit_games import coordinates, verify
from check_minimax import plain_minimax


def records(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def board_from(text):
    return dict(zip((sq for row in match.ROWS for sq in row), map(int, text.split()), strict=True))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("model")
    model = parser.parse_args().model
    rng = random.Random(851701)
    checks = []
    for i in range(32):
        position = None
        while position is None:
            position = match.opening(rng, (0, 24, 50, 61, 62, 63, 72, 80)[i % 8])
        checks.extend([(*position, d) for d in (1, 2, 3)])
    for row in records(PREV/'tactics.jsonl'):
        checks.extend((board_from(row['board']), 1, d) for d in (4, 5, 6, 4))
    terminal = {sq: 1 for row in match.ROWS for sq in row}
    checks.extend([(terminal, 1, 0), (terminal, 2, 3)])
    while True:
        pos = match.opening(rng, 82)
        if pos and not match.legal_moves(*pos):
            checks.extend([(*pos,0), (*pos,2)])
            break
    stream = ''.join(f'{d}\n'+match.board_input(b,s) for b,s,d in checks)
    run = subprocess.run([HERE/'bin'/f'{model}-probe'], input=stream,text=True,capture_output=True,check=True)
    for (b,s,d), line in zip(checks,run.stdout.splitlines(),strict=True):
        evaluation = "disk" if model in ("control", "pvs") else model
        ref, options = plain_minimax(b, s, d, evaluation)
        v,m,_,_ = map(int,line.split())
        assert ref == v and (m in options if options else m == -1), (model,d,ref,v,m,options)
    print(json.dumps(dict(kind="fixed_depth", passed=len(checks))),flush=True)
    binary = HERE/'bin'/model
    truth = ROOT/'experiments/minimax-validation/bin/truth'
    batch = []
    for i in range(96):
        while True:
            pos = match.opening(rng,84-(5+i%6))
            if pos and len(match.legal_moves(*pos)) >= 2:
                break
        batch.append(pos)
    for row in records(PREV/'endgames.jsonl'):
        if "margin" in row:
            batch.append((board_from(row['board']),1))
    stream = ''.join(match.board_input(b,s) for b,s in batch)
    output = subprocess.run([truth],input=stream,text=True,capture_output=True,check=True).stdout.splitlines()
    for (b,s),line in zip(batch,output,strict=True):
        vals=list(map(int,line.split()))
        margins=dict(zip(vals[::4],vals[1::4],strict=True))
        sq,_=match.ask_player(binary,b,s,match.legal_moves(b,s))
        assert margins[16*sq[0]+sq[1]]==max(margins.values())
    print(json.dumps(dict(kind="exact_margin",passed=len(batch))),flush=True)
    for row in records(PREV/'endgames.jsonl'):
        if row['case'].startswith('fresh-'):
            continue
        b=board_from(row['board'])
        sq,wall=match.ask_player(binary,b,1,match.legal_moves(b,1))
        move=list(coordinates(sq))
        if move==row['move']:
            value=row['chosen']
        elif row['case']=='set-14':
            values={}
            for v in records(ROOT/'experiments/winrate/records/missed-win-moves.jsonl'):
                for key in ('first','second'):
                    values[tuple(v[key])]=v[key+'_value']
            value=values[tuple(move)]
        else:
            ref=ROOT/'experiments/minimax-validation/bin/verify'
            for seconds in (4,15,45):
                value,_,_=verify(ref,seconds,b,1,sq,sq)
                if value!=-9: break
        print(json.dumps(dict(kind="winning_fixture",case=row['case'],move=move,value=value,wall_s=wall)),flush=True)


if __name__ == "__main__":
    main()
