# CMSC 474 Project 2 — 88-cell Reversi

The server starts the player once per turn. The player reads the current board, chooses a legal placement, prints its coordinates, and exits. When neither side can move, the side with more disks wins, even if some cells are empty. The development player is a single C++17 source file. It builds with the standard library and a compiler supporting 128-bit integers. [Development player](reversi.cpp) · [Assignment and board diagrams](project2_fall2026.pdf)

## Build and run one turn

Use a C++17 compiler with 128-bit integer support, such as GCC or Clang. From the project root, compile and feed one board to the executable.

```sh
c++ -std=c++17 -O2 reversi.cpp -o reversi
./reversi < tests/assignment.board
```

Standard input contains 88 whitespace-separated integers. The eight row widths are **8, 10, 12, 14, 14, 12, 10, 8**. A `0` is empty, a `1` is ours, and a `2` is the opponent's. Standard output is one line containing the **one-based row and column within that row**. The assignment illustrates one of six legal placements with `7 6` in Figure 3. For a root position with no legal move, the player emits `0 0`. The assignment leaves the pass encoding unspecified. [Assignment sample input](tests/assignment.board)

To try a position with a known best move, save these eight lines as `position.txt` and run `./reversi < position.txt`.

```text
0 1 2 1 1 1 1 0
0 1 2 2 0 2 1 1 1 0
1 1 2 2 2 2 2 2 2 2 2 2
2 2 2 2 1 2 1 1 1 1 1 2 2 1
1 2 1 1 2 2 1 1 2 2 2 2 2 2
1 2 1 1 2 1 2 2 2 1 1 2
0 2 1 1 2 2 2 1 1 2
1 1 1 1 2 2 2 1
```

**Expected output is `7 1`.** Six cells are empty. This move flips two disks and forces a win by 14 under perfect play. The greedy move `2 5` flips six immediately and loses by 18 against the best reply. The independent solvers below can reproduce both results.

## How minimax chooses a move

The player searches both sides' legal moves. Each side maximizes its own score under the assumption that the opponent will choose their best reply. The code implements this as **negamax**, returning the negative of the opponent's score after a placement. A forced pass changes whose turn it is and keeps the same number of placements left to search. [Search implementation](reversi.cpp)

At an unfinished leaf, the number of empty cells determines how the player compares positions. **With more than 22 empty cells, it first prefers more legal moves for us relative to the opponent. If the mobility differences tie, it prefers the larger disk lead. With 22 or fewer empty cells, it uses disk difference alone.** The switch preserved a forced win that the all-mobility version missed in testing. [Search experiments](SEARCH_EXPERIMENTS.md)

| Leaf | Score from the side to move |
| --- | --- |
| Unfinished, more than 22 empty | `177 × (our legal moves − their legal moves) + our disk margin` |
| Unfinished, 22 or fewer empty | Our disk margin |
| Finished win | `15,664 + our disk margin` |
| Finished draw | 0 |
| Finished loss | `our negative disk margin − 15,664` |

These constants encode the order of comparison. Disk margins range from −88 to +88, so a difference of one legal move takes priority when multiplied by `2 × 88 + 1 = 177`. For example, two more legal moves and six fewer disks score `2 × 177 − 6 = 348`. The maximum possible magnitude of an unfinished estimate is bounded by `88 × 177 + 88 = 15,664`. Offsetting the terminal score by that amount puts any known win above an unfinished estimate and any known loss below it. The player needs only the board, its dimensions, and the 22-cell cutoff; all search and evaluation code is in [reversi.cpp](reversi.cpp).

**Alpha–beta pruning** skips replies after a bound proves they cannot affect the current decision. A transposition table stores the two bitboards, depth, score bound, and move. Score reuse requires the same complete position and depth. The search tries the cached move first, then orders alternatives with fewer opponent replies first at depths above one. These choices speed up the same minimax calculation.

**Iterative deepening** searches one placement ahead, then two, and so on up to the number of empty cells. After each complete depth the player saves its best move. If time expires, it returns the last saved move. Until the first depth completes, it has the first legal move as a fallback. The result is exact for the completed depth. A search that reaches the end of the game guarantees the optimal outcome and final margin under perfect play.

## Time, memory, and board representation

The assignment allows three seconds and 500 MB per invocation. A single thread uses a monotonic 2.65-second internal deadline, reserving the remaining time for startup, scheduling and output. Search checks the clock every 256 nodes. The fixed-size cache holds at most 524,288 entries. The cache hash constants only choose a storage slot.

Two 128-bit integers represent the disks. The eight rows are centered in a grid with a 16-bit stride. Shifts by 1, 15, 16, and 17 step along rows, columns, and diagonals. Padding prevents row wraparound. A move flips each uninterrupted ray of opposing disks bracketed by the placed disk and a friendly disk.

## Testing results

The current player won **44 of 60 games (73.3%)** against the previous disk-count player on 30 fresh openings, playing each opening once per color. It earned 18 more wins than the control from early starts, 11 more from middle starts, and the same number from late starts. Win rate below means wins divided by all games, with draws included in the denominator. [Paired match results](experiments/search-ab/results/final-summary.json)

| Opponent and starting position | Wins | Draws | Losses | Win rate |
| --- | ---: | ---: | ---: | ---: |
| Disk-count player, 30 held-out opening pairs | 44 | 1 | 15 | 73.3% |
| Disk-count player, standard opening | 2 | 0 | 0 | 100% |
| Greedy player, one seeded opening | 2 | 0 | 0 | 100% |
| Three-ply player, same seeded opening | 1 | 0 | 1 | 50% |
| Archived trained player, standard opening | 0 | 0 | 2 | 0% |
| **All games played by the current version** | **49** | **1** | **18** | **72.1%** |

The disk-count player was the opponent in 62 of the 68 games. Each two-game comparison used one opening with colors swapped. The class tournament win rate is still unknown. [Match design and opponent descriptions](SEARCH_EXPERIMENTS.md)

- **Search correctness.** The current version matched exhaustive minimax on 112 fixed-depth checks, selected the best achievable final disk margin on 108/108 small endgames, and preserved 10/10 independently proved wins. The earlier version of the same move generator matched the independent rules checker on all 18,221 legal successors tested. [Current checks](experiments/search-ab/results/check-phase.jsonl) · [Move-generator validation](MINIMAX_VALIDATION.md)
- **Protocol and resources.** The program returned `4 6` on the assignment example and `0 0` on the pass check. All 21 command-line and resource checks passed. Peak measured memory was 25.55 MiB, and the current player's slowest recorded turn across its 68 games took 2.825 seconds. The referee recorded zero forfeits across all 200 games in the search experiment. [Example outputs](experiments/search-ab/results/submission-cli.json) · [Resource checks](experiments/search-ab/results/resources-phase.jsonl) · [Match records and timings](experiments/search-ab/results/final-summary.json)
- **Alternatives already tested.** Using mobility at every depth cutoff turned one saved forced win into a draw. Disk-count minimax with principal variation search (PVS) visited 26.9% fewer nodes at fixed depth, but its 64–2–54 record across 60 pairs fell short of the win-rate threshold for adoption. [Search experiments](SEARCH_EXPERIMENTS.md)

## Next experiments to improve win rate

**First test whether the opponent can take a permanently unflippable square on its next move.** This board has eight such squares, called *anchors*. The trained opponent finished with seven in each standard-opening game, winning 75–13 and 85–2. In the second game, with 55 cells empty, our player chose `7 8` and the opponent took the anchor at `8 8`. Another legal move, `2 9`, allowed no immediate anchor reply. Whether that alternative improves the eventual result is a question for testing. [Both game replays](experiments/search-ab/results/standard-phase-baseline-00.jsonl)

| Priority | Proposed experiment | How to judge it |
| --- | --- | --- |
| 1. Measure the weakness | Replay fresh color-swapped openings against the trained player. Count turns where our move offered an immediate anchor and another legal move denied all such replies. | Report how often this occurs in wins and losses. Save the first such position in each game so collaborators can reproduce it. |
| 2. Test anchor access as a tie-break | In a separate candidate, keep mobility first at unfinished leaves above 22 vacancies. When mobility ties, compare our legal anchor moves minus theirs, then compare disk margin. This needs no fitted weights. | Track anchor concessions and use paired wins against the current player and the trained opponent to judge whether the change helps. |
| 3. Test PVS with the current evaluation | In a second, separate candidate, apply the already-tested PVS implementation to today's mobility evaluator. The previous PVS trial used disk count throughout. | Verify the same fixed-depth scores and optimal moves as today's player, then measure completed depth and wins at the real clock. |

For each candidate, freeze today's player as the control. Use the saved positions for development and reserve fresh openings for the decision. Start with 30 color-swapped pairs against the control, report wins by opening and opponent, and extend to 60 pairs if the paired result is inconclusive. Require a reliable win advantage, all 108 exact-margin checks and 10 forced wins preserved, and zero candidate forfeits under the three-second limit. [Existing evaluation protocol](SEARCH_EXPERIMENTS.md)

## Test a move or compare two players

Run these commands from the project root with the six-empty example in `position.txt`.

```sh
c++ -std=c++17 -O2 tests/verify.cpp -o verify
c++ -std=c++17 -O2 tests/truth.cpp -o truth
printf '5 7 1 2 5\n' | cat - position.txt | ./verify
./truth < position.txt
```

- **`verify`** takes a time allowance in seconds and two legal row/column pairs before the board. It prints the outcomes of move A, move B, and best play from the original position. The example prints `1 -1 1`, meaning A wins, B loses, and the position is winnable. A draw is `0` and an unresolved query is `-9`. [Outcome verifier](tests/verify.cpp)
- **`truth`** solves small endgames to completion. For each legal move it prints four integers giving the padded square index, guaranteed disk margin, number of opponent replies permitting a forced win for us, and total legal replies. In the example, `98 14 4 4` describes `7 1`. The index is `16 × zero_based_row + row_offset + zero_based_column`, with `row_offset = (14 − row_width) / 2`. [Exact margin solver](tests/truth.cpp)

The following regression suite compares alpha–beta with an independent Python minimax that visits every branch. It also sends 96 boards with 5–10 empty cells to the normal player and checks each chosen move against the independent C++ solver. It uses Python 3.10 or later and the standard library. [Regression suite](tests/check_minimax.py)

```sh
c++ -std=c++17 -O2 tests/minimax_probe.cpp -o minimax-probe
python3 tests/check_minimax.py ./reversi ./minimax-probe ./truth
```

The checker defaults to the project's mobility and endgame rule. When testing the archived disk-count player or the PVS-only candidate, compile the probe against that same source and use `--evaluation disk`.

To measure playing strength, compile a reference version as `reversi-baseline` and the version under test as `reversi`. The match runner starts a fresh process on each playable turn, checks its output and elapsed time, and replays each opening with colors swapped. Four pairs give eight games. [Paired match runner](tests/match.py)

```sh
python3 tests/match.py ./reversi ./reversi-baseline --pairs 4 --opening-plies 12 --seed 474
```

Add `--record matches.jsonl` to save each starting board, both sides' moves, timings, and final score. To inspect the earliest provable mistake in each loss, replay the file with the independent verifier. The audit checks the losing side's moves from 22 empty cells onward by default. A value of `-9` means the verifier ran out of time. [Replay and audit](tests/audit_games.py)

```sh
python3 tests/audit_games.py ./verify matches.jsonl --max-empty 22 --seconds 2
```

The earlier trained tournament player and its training data are archived under the experiments directory. The development player builds from `reversi.cpp` alone. [Frozen trained source](experiments/winrate/baseline.cpp) · [How the trained version worked](experiments/winrate/trained-player.md)

## Project reports

- [Search experiments](SEARCH_EXPERIMENTS.md) compares mobility evaluation and principal variation search with the frozen disk-count player.
- [Disk-count player validation](MINIMAX_VALIDATION.md) documents the assignment example, game rules, exact endgames, timing and original matches.
- [Trained-player experiments](TRAINED_PLAYER_EXPERIMENTS.md) records the earlier evaluation and proof-schedule trials.
