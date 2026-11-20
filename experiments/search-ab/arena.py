"""Run replayable, color-swapped matches with the assignment referee and per-turn limit."""
import argparse
import concurrent.futures
import hashlib
import json
import random
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'tests'))
import match


def board_for(index, stage):
    if stage == 'holdout':
        seed=9360701+index
        plies=(16,38,58)[index%3]+2*((index//3)%4)
    elif stage == 'standard':
        seed,plies=0,0
    else:
        seed,plies=857192+index,24
    rng=random.Random(seed)
    while True:
        pos=match.opening(rng,plies)
        if pos and len(match.legal_moves(*pos))>=2:
            return seed,plies,*pos


def executable(name):
    if name in ('greedy','shallow','baseline'):
        return ROOT/'experiments/winrate/bin'/name
    return HERE/'bin'/name


def play_pair(job, directory):
    candidate,reference,stage,index=job
    path=directory/f'{stage}-{candidate}-{reference}-{index:02}.jsonl'
    binary,other=map(executable,(candidate,reference))
    hashes=[hashlib.sha256(p.read_bytes()).hexdigest() for p in (binary,other)]
    seed,plies,board,side=board_for(index,stage)
    start=list(map(int,match.board_input(board,1).split()))
    games=[json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []
    assert all(g['board']==start and g['binaries']==hashes for g in games)
    colors=(1,2) if index%2==0 else (2,1)
    for color in colors:
        if any(g['candidate_side']==color for g in games):
            continue
        history=[]
        record=dict(candidate=candidate,reference=reference,binaries=hashes,stage=stage,index=index,seed=seed,
                    opening_plies=plies,starting_side=side,candidate_side=color,board=start,moves=history)
        try:
            ours,theirs,peak=match.game(board,side,color,binary,other,history)
            record.update(candidate_disks=ours,reference_disks=theirs,peak_candidate_s=peak,
                          result=(ours>theirs)-(ours<theirs))
        except match.TurnFailure as exc:
            record.update(forfeit_side=exc.side,reason=str(exc),result=-1 if exc.side==color else 1)
        with path.open('a') as f:
            print(json.dumps(record,separators=(',',':')),file=f,flush=True)
        games.append(record)
    return f'{stage} {candidate}/{reference} pair {index}: '+str([g['result'] for g in games])


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('candidates',nargs='+')
    parser.add_argument('--stage',choices=['holdout','standard','styles'],required=True)
    parser.add_argument('--start',type=int,default=0)
    parser.add_argument('--count',type=int,default=1)
    parser.add_argument('--jobs',type=int,default=3)
    parser.add_argument('--opponents', nargs='+', choices=['control','greedy','shallow','baseline'])
    parser.add_argument('--output', type=Path, default=HERE/'results',
                        help="directory for new or resumable game records")
    args=parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    refs=args.opponents or (['control'] if args.stage in ('holdout','standard') else ['greedy','shallow'])
    jobs=[(c,r,args.stage,i) for i in range(args.start,args.start+args.count)
          for r in refs for c in args.candidates]
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        for future in concurrent.futures.as_completed([pool.submit(play_pair,j,args.output) for j in jobs]):
            print(future.result(),flush=True)


if __name__=='__main__':
    main()
