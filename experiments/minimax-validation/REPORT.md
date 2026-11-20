# Weight-free Reversi player — test report

**November 19, 2026.** The player matched the independent solver's optimal final margin on all 108 small endgames. The trained opponent won both games from the standard opening. In both, the player led on disks while its legal moves dwindled. The first proposed experiment compares disk count with an untrained mobility evaluation.

## Scope

We tested the [single-file player](../../reversi.cpp) with its 2.65-second internal deadline and a three-second external limit on each match turn. The release build used Apple Clang 21.0.0, C++17, and `-O2 -Wall -Wextra -Wpedantic` on Darwin arm64. It compiled without diagnostics. The tested source SHA-256 is `8df9c38c9dac848c57fccbe86ba45c4705996e119bc5705cf4245feb4ca88530`. The [starting manifest](results/original-checksums.json) covers all 109 pre-existing project files.

## Correctness and protocol

| Case | Expected behavior | Observed |
| --- | --- | --- |
| Assignment example | Print one of the six legal row/column pairs | `3 5` in all five runs, including input with tabs and newlines. The illustrated `7 6` was also legal. |
| Boundary and flip rules | Match the independent Python ray scanner on every move and both resulting disk sets | All 18,221 successors matched on 2,204 boards. Cases included 496 edge-terminated rays in eight directions, a simultaneous eight-direction capture, and all visited states in 20 seeded legal games. |
| Memory and undefined behavior | Re-run the rule comparison with AddressSanitizer and UndefinedBehaviorSanitizer | Same results, no sanitizer diagnostics during this suite. |
| Forced moves and passes | Select the sole legal endpoint on long rows. Print `0 0` on a forced pass, a full draw, or an early double pass | All passed. Short input, empty input, a non-integer, and a value outside 0–2 produced exit code 1 and empty stdout. |
| Fixed-depth minimax | Match the root score and an optimal move from exhaustive Python minimax | All 76 existing checks passed. Another 12 checks on three tactical boards passed at depths 4, 5, 6, and then 4 again with a populated cache. |
| Exact final disk margin | Choose a move with the best achievable final margin under perfect play | 96/96 positions with 5–10 empty cells and 12/12 new positions with 11–13 empty cells. |

[CLI observations](results/cli.jsonl) · [Rule comparisons](results/rules.json) · [Sanitizer run](results/sanitizers.json) · [Existing regression suite](results/regression.log) · [New endgames](results/endgames.jsonl)

### Positions where the choice mattered

All coordinates use the assignment's one-based, row-relative format.

| Board | Exact expectation | Player's choice |
| --- | --- | --- |
| One move saves a draw | `5 4` draws. Each of the six other moves loses by 2–10 disks. | `5 4` |
| Immediate flips are misleading | Taking the most flips loses by 10. The best final margin is +26. | `2 10`, +26 |
| Every move loses | The best defense loses by 6. Other moves lose by 8–22. | `7 10`, −6 |
| Archived 21-empty puzzle | Only `1 5` forces a win. The archived trained player chose a draw. | `1 5` |

The three small boards were selected using the exact solver before asking the player. We also tested four orientations of both the unique draw and the 21-empty win, twice per orientation. All 16 calls selected the transformed optimal move. These are eight distinct board orientations across two underlying puzzles. [Tactical boards and every move's margin](results/tactics.jsonl) · [Reflection results](results/symmetry.jsonl) · [Independent proof for the 21-empty board](../winrate/records/missed-win-moves.jsonl)

### What the clock allowed

In a separate diagnostic executable calling the same search, the deepest completed iteration was 11 placements on the assignment example, 12 on the 44-empty match position, 15 on the 21-empty puzzle, and all 11 on an 11-empty position. On the puzzle, depth 10 preferred `4 11`, a proven loss. Depths 11–15 preferred the winning `1 5`. The independent solver established its outcome. A deeper search can therefore change an actual loss into a win even with the same evaluation. Depth and elapsed time can vary across runs. [Per-depth moves, scores, cumulative nodes, and times](results/profiles.jsonl)

Across 21 direct CLI checks, the longest wall time was **2.656 s** and the highest child peak resident memory was **25.52 MiB**. Each check launched the actual executable from a fresh measuring process. Across 296 candidate turns in the matches below, the slowest took **2.918 s**, about 82 ms inside the external limit. No match invocation timed out or returned an illegal move. These are measurements on this machine. The timing results give little reason to raise the internal deadline. [CLI measurements](results/cli.jsonl) · [Match totals and timing](results/summary.json)

## Playing strength

| Opponent | Starting positions, both colors | Wins | Draws | Losses |
| --- | --- | ---: | ---: | ---: |
| Greedy, most flips | 44 and 26 empty | 4 | 0 | 0 |
| Three-ply mobility and anchor player | Same two boards | 2 | 0 | 2 |
| Archived trained player | Same two boards | 2 | 0 | 2 |
| Archived trained player | Standard four-disk opening | 0 | 0 | 2 |

Across these games the player recorded **8 wins, 0 draws, and 6 losses**. The same two seeded boards were reused across opponents to make the pairs comparable. The 14 games cover three starting boards and three local opponent styles, so the aggregate has limited value as an estimate of class tournament win rate. [Move-by-move records and final scores](results)

From the standard opening, the trained player won **79–9** and **87–1**. In the first game our player led **29–15** with 44 cells empty, yet had only **2** legal placements available to the opponent's **20**. In the return game it still led **42–16** with 30 empty, when its legal-move count was **0** and the opponent's was **15**. Mobility here means the number of placements each color could make on the same board. Both games demonstrate the limits of using a disk lead to judge an unfinished position. An A/B experiment is needed to establish whether changing the evaluation improves wins. [Standard-opening games](results/baseline-standard.jsonl) · [Disk and mobility counts by turn](results/summary.json)

The independent solver checked **all 152 candidate turns with at most 22 empty cells** from these matches. Every chosen move preserved the best achievable win/draw/loss result. Some positions were already lost under perfect play, so optimal play in this metric can still end in a loss. In the 44-empty start, the side-two losses were provably forced by 37 empty against the three-ply player and by 35 empty against the trained player. Earlier queries reached the verifier's time limit, so they do not identify the first avoidable mistake. [Endgame audit](results/match-audit.jsonl) · [Earlier queries](results/first-turns.jsonl)

On a separate positional test, the player preserved the optimal outcome on **16/16 fresh boards with 14–20 empty cells** and converted **10/10 archived forced wins with 20–22 empty**. The latter set was selected for winnability and measures conversion. [Boards, moves, timings, and proof sources](results/endgames.jsonl)

A further **12 fresh positions had 21–24 empty cells**. The verifier certified the player's choice on 11, including eight forced wins. On case `fresh-23-2`, both the current and trained players chose `1 1`. A 45-second offline query proved that move loses. The verifier left the best achievable result unresolved, including after additional checks of all twelve legal alternatives. We cannot tell whether the player threw away a draw or win on that board. [Stress cases](results/stress.jsonl) · [Longer proof](results/extended-stress.jsonl) · [Alternative moves](results/stress-alternatives.jsonl)

## Improvement plan

1. **Test mobility as an untrained midgame evaluation.** Save the current player as the control for a future experiment. Compare disk differential with a simple alternative that prefers a larger difference in legal moves at unfinished leaves and uses disk differential to break ties. Keep terminal outcomes and the time budget identical. The current player already uses opponent reply count to order branches. This experiment would test whether mobility helps *score* positions. Compare wins from the standard opening and from early openings with each color.
2. **Test principal variation search separately.** Keep the current disk-only evaluation for this experiment. After searching the cached first move, try a narrow alpha–beta window for other moves and re-search a challenger when needed. Check values and optimal-move membership against full-window minimax. Measure nodes at the same depth, the last completed depth under the real clock, and outcomes on the known-win fixtures. The 21-empty puzzle provides a concrete depth-sensitive test.
3. **Choose by wins on fresh paired openings.** Screen changes on the saved puzzles and replays, then use a disjoint seed set for the promotion decision. Start with 30 color-swapped opening pairs against the frozen player, alongside the greedy and three-ply opponents. Record the win difference per opening pair, draws, and timeout forfeits. Extend the sample if the difference remains within paired sampling uncertainty. Require legal output, preserved exact endgame results, and compliance with the time and memory limits before promoting a change.

## Reproduction

Run from the project root. These commands build separate executables in this report's directory.

```sh
V=experiments/minimax-validation
c++ -std=c++17 -O2 -Wall -Wextra -Wpedantic reversi.cpp -o "$V/bin/player"
c++ -std=c++17 -O2 tests/minimax_probe.cpp -o "$V/bin/probe"
c++ -std=c++17 -O2 tests/truth.cpp -o "$V/bin/truth"
c++ -std=c++17 -O2 tests/verify.cpp -o "$V/bin/verify"
c++ -std=c++17 -O2 "$V/inspect.cpp" -o "$V/bin/inspect"
c++ -std=c++17 -O1 -g -fsanitize=address,undefined -fno-sanitize-recover=all "$V/inspect.cpp" -o "$V/bin/inspect-sanitized"
python3 -B tests/check_minimax.py "$V/bin/player" "$V/bin/probe" "$V/bin/truth"
python3 -B "$V/check_rules.py"
python3 -B "$V/check_rules.py" inspect-sanitized
python3 -B "$V/check_cli.py"
python3 -B "$V/check_tactics.py"
python3 -B "$V/check_endgames.py"
python3 -B "$V/check_endgames.py" --stress
python3 -B "$V/check_symmetry.py"
"$V/bin/inspect" --depth < tests/assignment.board
python3 -B "$V/summarize.py"
```

The recorded matches used the [existing match runner](../../tests/match.py) and [archived opponents](../winrate/README.md). For each opponent run one color-swapped pair with `--opening-plies 40 --seed 714031` and one with `--opening-plies 58 --seed 714058`. The trained opponent also played a pair with `--opening-plies 0 --seed 714000`. For example, the following command replays the 44-empty match against the three-ply opponent and prints the score.

```sh
python3 -B tests/match.py "$V/bin/player" experiments/winrate/bin/shallow --pairs 1 --opening-plies 40 --seed 714031
```
