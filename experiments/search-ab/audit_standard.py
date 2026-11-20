"""Use the independent solver to check actual late moves in standard-opening games."""
import json
from arena import HERE, ROOT
from audit_games import audit

for path in sorted((HERE/'results').glob('standard-*-*-[0-9][0-9].jsonl')):
    for game in map(json.loads,path.read_text().splitlines()):
        if 'forfeit_side' in game:
            continue
        checks=audit(game, ROOT/'experiments/minimax-validation/bin/verify', 2, 22, game['candidate_side'])
        print(json.dumps(dict(file=path.name,color=game['candidate_side'],checks=checks)),flush=True)
