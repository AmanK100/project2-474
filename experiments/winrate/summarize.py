"""Replay completed games and summarize wins, draws, losses, and candidate timing."""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "tests"))
from audit_games import audit


def main():
    print("suite,games,wins,draws,losses,slowest_candidate_seconds")
    for path in sorted((HERE / "records").glob("*.jsonl")):
        wins = draws = losses = 0
        peak = 0
        for line in path.read_text().splitlines():
            game = json.loads(line)
            if "moves" not in game or "failure" in game:
                continue
            # Replay and validate the final score without invoking the solver.
            audit(game, None, 0, 0, None)
            margin = game["candidate_disks"] - game["reference_disks"]
            wins += margin > 0
            draws += margin == 0
            losses += margin < 0
            for move in game["moves"]:
                if move["side"] == game["candidate_side"]:
                    peak = max(peak, move["seconds"])
        games = wins + draws + losses
        if games:
            print(f"{path.stem},{games},{wins},{draws},{losses},{peak:.6f}")


if __name__ == "__main__":
    main()
