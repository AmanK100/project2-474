"""Select three small decision problems by their exact values before asking the player."""

import json
import random
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "tests"))
import match
from audit_games import coordinates
from check_minimax import plain_minimax


def main():
    rng = random.Random(851177)
    remaining = {"only-draw", "greedy-loses", "best-losing-margin"}
    for index in range(1, 1501):
        position = match.opening(rng, rng.choice((76, 77, 78)))
        if not position:
            continue
        board, side = position
        choices = match.legal_moves(board, side)
        if len(choices) < 2:
            continue
        data = match.board_input(board, side)
        run = subprocess.run([HERE / "bin/truth"], input=data, text=True, capture_output=True, check=True)
        values = list(map(int, run.stdout.split()))
        margins = {divmod(sq, 16): v for sq, v in zip(values[::4], values[1::4], strict=True)}
        best = max(margins.values())
        if list(margins.values()).count(best) != 1:
            continue
        most = max(map(len, choices.values()))
        greedy = [margins[sq] for sq, flips in choices.items() if len(flips) == most]
        if best == 0:
            kind = "only-draw"
        elif best > 0 and max(greedy) < 0:
            kind = "greedy-loses"
        elif best < 0:
            kind = "best-losing-margin"
        else:
            continue
        if kind not in remaining:
            continue
        remaining.remove(kind)
        sq, wall = match.ask_player(HERE / "bin/player", board, side, choices)
        depths = [4, 5, 6, 4]
        run = subprocess.run([HERE / "bin/probe"], input="".join(f"{d}\n{data}" for d in depths),
                             text=True, capture_output=True, check=True)
        for d, line in zip(depths, run.stdout.splitlines(), strict=True):
            score, allowed = plain_minimax(board, side, d)
            observed, move = map(int, line.split())
            assert observed == score and move in allowed
        print(json.dumps(dict(case=kind, seed_index=index, board=data, move=coordinates(sq),
                              chosen_margin=margins[sq], best_margin=best, max_flips_margins=greedy,
                              alternatives=[[*coordinates(key), val] for key, val in margins.items()],
                              wall_s=wall, checked_depths=depths)), flush=True)
        if not remaining:
            return
    raise RuntimeError(f"missing examples: {remaining}")


if __name__ == "__main__":
    main()
