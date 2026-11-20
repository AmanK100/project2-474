"""Compare every legal successor to the independent Python rules implementation."""

import json
import random
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "tests"))
import match

CELLS = [sq for row in match.ROWS for sq in row]


def ray_fixtures():
    for target in CELLS:
        for dr, dc in match.DIRECTIONS:
            board = dict.fromkeys(CELLS, 0)
            r, c = target
            ray = []
            while (r + dr, c + dc) in board:
                r += dr
                c += dc
                ray.append((r, c))
            if len(ray) < 2:
                continue
            for sq in ray[:-1]:
                board[sq] = 2
            board[ray[-1]] = 1
            assert list(match.legal_moves(board, 1)) == [target]
            yield board, 1


def reachable():
    rng = random.Random(610048)
    for _ in range(20):
        board, side = match.opening(rng, 0)
        while True:
            yield board.copy(), side
            choices = match.legal_moves(board, side)
            if not choices:
                side = 3 - side
                choices = match.legal_moves(board, side)
                if not choices:
                    break
                yield board.copy(), side
            move = rng.choice(list(choices))
            match.place(board, side, move, choices[move])
            side = 3 - side


def main():
    rays, games = list(ray_fixtures()), list(reachable())
    center = (3, 6)
    ring = dict.fromkeys(CELLS, 1)
    ring[center] = 0
    for dr, dc in match.DIRECTIONS:
        ring[center[0] + dr, center[1] + dc] = 2
    assert len(match.legal_moves(ring, 1)[center]) == 8
    positions = rays + games + [(ring, 1)]
    binary = HERE / "bin" / (sys.argv[1] if len(sys.argv) > 1 else "inspect")
    stream = "".join(match.board_input(board, side) for board, side in positions)
    run = subprocess.run([binary], input=stream, capture_output=True, text=True, check=True)
    assert not run.stderr, run.stderr
    successors = passes = 0
    for (board, side), line in zip(positions, run.stdout.splitlines(), strict=True):
        numbers = list(map(int, line.split()))
        children = {sq: (lo | hi << 64, other_lo | other_hi << 64)
                    for sq, lo, hi, other_lo, other_hi in zip(*[iter(numbers)] * 5, strict=True)}
        moves = match.legal_moves(board, side)
        assert len(children) == len(moves)
        passes += not moves
        for (r, c), flips in moves.items():
            child = board.copy()
            match.place(child, side, (r, c), flips)
            masks = tuple(sum(1 << (16 * y + x) for (y, x), disk in child.items() if disk == player)
                          for player in (3 - side, side))
            assert children[16 * r + c] == masks, (r, c)
            successors += 1
    print(json.dumps(dict(binary=binary.name, ray_positions=len(rays), reachable_positions=len(games),
                          eight_direction_positions=1, positions=len(positions),
                          replies_with_no_move=passes, checked_successors=successors)))


if __name__ == "__main__":
    main()
