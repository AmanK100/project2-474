"""Replay the raw records, summarize completed pairs and compute the exact paired test."""
from collections import Counter, defaultdict
import argparse
import hashlib
import json
from functools import lru_cache
from pathlib import Path
from arena import HERE, board_for, executable, match


def paired_p(scores):
    totals=Counter({0:1})
    k=0
    for d in scores:
        if d==0:
            continue
        k+=1
        nxt=Counter()
        for n,ways in totals.items():
            nxt[n+d]+=ways
            nxt[n-d]+=ways
        totals=nxt
    threshold=abs(sum(scores))
    return sum(ways for n,ways in totals.items() if abs(n)>=threshold)/(2**k)


def replay(g):
    cells=[s for r in match.ROWS for s in r]
    board=dict(zip(cells,g['board'],strict=True))
    side=g['starting_side']
    for log in g['moves']:
        legal=match.legal_moves(board,side)
        if not legal:
            side=3-side
            legal=match.legal_moves(board,side)
        assert side==log['side'] and log['seconds']<=3
        sq=match.ROWS[log['row']-1][log['column']-1]
        match.place(board,side,sq,legal[sq])
        side=3-side
    if 'forfeit_side' in g:
        if not match.legal_moves(board,side):
            side=3-side
        assert side==g['forfeit_side'] and match.legal_moves(board,side)
        assert g['result']==(-1 if side==g['candidate_side'] else 1)
    else:
        assert not match.legal_moves(board,1) and not match.legal_moves(board,2)
        disks=list(board.values())
        a=disks.count(g['candidate_side'])
        b=disks.count(3-g['candidate_side'])
        assert (a,b)==(g['candidate_disks'],g['reference_disks']) and g['result']==(a>b)-(a<b)


@lru_cache
def digest(name):
    return hashlib.sha256(executable(name).read_bytes()).hexdigest()


def tally(pairs):
    counts=Counter()
    scores=[]
    phase={}
    forfeits=[]
    peak=0
    moves=0
    for a,b in pairs:
        assert a['board']==b['board'] and a['candidate_side']!=b['candidate_side']
        d=a['result']+b['result']
        scores.append(d)
        phase.setdefault(('early','middle','late')[a['index']%3],[]).append(d)
        for g in (a,b):
            counts[g['result']]+=1
            if 'forfeit_side' in g:
                forfeits.append(dict(index=g['index'],candidate=g['forfeit_side']==g['candidate_side'],reason=g['reason']))
            times=[m['seconds'] for m in g['moves'] if m['side']==g['candidate_side']]
            peak=max([peak]+times)
            moves+=len(times)
    return dict(pairs=len(pairs),wins=counts[1],draws=counts[0],losses=counts[-1],
                paired_advantage=sum(scores),pair_scores=dict(sorted(Counter(scores).items())),
                p=paired_p(scores),bracket_net_wins={k:sum(v) for k,v in phase.items()},
                forfeits=forfeits,peak_s=peak,candidate_turns=moves)


def collect(recheck=False, directory=HERE/'results'):
    groups=defaultdict(list)
    for file in sorted(directory.glob('*.jsonl')):
        parts = file.stem.split('-')
        if (len(parts) != 4 or parts[0] not in ('holdout', 'styles', 'standard')
                or not parts[-1].isdigit()):
            continue
        games=[json.loads(l) for l in file.read_text().splitlines()]
        if recheck:
            for g in games:
                assert g['binaries']==[digest(g['candidate']),digest(g['reference'])]
                seed,plies,board,side=board_for(g['index'],g['stage'])
                assert (seed,plies,side)==(g['seed'],g['opening_plies'],g['starting_side'])
                assert g['board']==list(map(int,match.board_input(board,1).split()))
                replay(g)
        if len(games)==2:
            groups[file.stem.rsplit('-',1)[0]].append(games)
        else:
            assert len(games)<=1
    return {k:tally(v) for k,v in groups.items()}


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--replay',action='store_true')
    parser.add_argument('--input', type=Path, default=HERE/'results')
    args=parser.parse_args()
    print(json.dumps(collect(args.replay, args.input),indent=2))
