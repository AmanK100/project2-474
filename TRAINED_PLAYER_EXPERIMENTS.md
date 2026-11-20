# Win-rate experiments

The [frozen trained baseline](experiments/winrate/baseline.cpp) has SHA-256 `94eda0d9652cdfe05af43667d691089ecd1b037be5b964e1c335ff38240807d3`. All experimental executables are in `bin/`. Collaborators can build the [weight-free development player](reversi.cpp) independently. [Frozen player's search and weights](experiments/winrate/trained-player.md)

## Midgame and development-player results

| Player vs. frozen trained baseline | Clock and openings | Wins | Draws | Losses |
| --- | --- | ---: | ---: | ---: |
| Refit on disk margin | 20 ms, 24 opening pairs | 22 | 3 | 23 |
| Refit on win/draw/loss | 20 ms, same 24 pairs | 24 | 1 | 23 |
| Refit on disk margin | Tournament clock, three fresh pairs with 40 or 58 empty | 3 | 0 | 3 |
| Refit on win/draw/loss | Tournament clock, same three pairs | 3 | 0 | 3 |
| Weight-free development player | Tournament clock, two fresh pairs with 26 empty | 2 | 0 | 2 |

The first tournament-clock attempt for each refit stopped on a three-second process timeout while other benchmark suites were active. The completed full-clock counts above use the separately recorded retries and the earlier-starting pair. These small samples did not establish a win-rate gain from either refit. [Margin timing attempt](experiments/winrate/records/margin-full.log) · [Outcome timing attempt](experiments/winrate/records/outcome-full.log) · [Margin retries](experiments/winrate/records/margin-full-retry.log) · [Outcome retries](experiments/winrate/records/outcome-full-retry.log) · [Weight-free games](experiments/winrate/records/minimax-vs-trained.log)

## Endgame results

| Candidate and opponent | Starting positions | Wins | Draws | Losses |
| --- | --- | ---: | ---: | ---: |
| Early proof vs. frozen | Six random openings with 22 empty | 6 | 0 | 6 |
| Early proof vs. frozen | Eight openings restricted to 2–8 choices, with 21 or 22 empty | 8 | 0 | 8 |
| Early proof vs. frozen | One opening after 12 random placements | 1 | 1 | 0 |
| Frozen vs. greedy | Two openings with 34 empty | 4 | 0 | 0 |
| Frozen vs. three-ply | Same two openings with 34 empty | 2 | 1 | 1 |

All rows use tournament timing. In the pair starting after 12 random placements, the games first diverged with **41 empty cells**. The scheduling change first applies at 22 empty, so this pair cannot isolate its effect. Both schedules preserved all six independently established wins in the additional winning-position test. On the sample of 18 eligible positions drawn without an outcome filter, the independent solver eventually resolved all 18. Four were winnable. Both players converted three and selected the drawing move `1 1` on the fourth, with 21 empty cells. The other 14 positions were forced losses. [Game records](experiments/winrate/records) · [18-position sample](experiments/winrate/records/proofs.jsonl) · [Extended verification](experiments/winrate/records/long-proofs.jsonl) · [45-second proofs](experiments/winrate/records/deep-proofs.jsonl) · [Six known wins](experiments/winrate/records/winning-proofs.jsonl) · [Missed-win board](experiments/winrate/records/missed-win.board)

On the missed-win board, **`1 5` is the only winning move**. Both schedules first disproved their heuristic favorite `4 11`, then used the rest of the turn on `1 1`. The baseline began the proof at depth 16 and the early version at depth 7. A [follow-up prototype](experiments/winrate/ranked-proof.cpp) used eleven-ply estimates to rank alternative root moves. It chose `8 1`, also a draw. This diagnostic used the known board and does not establish a head-to-head result for the prototype. [Values of all eight moves](experiments/winrate/records/missed-win-moves.jsonl) · [Search trace](experiments/winrate/records/missed-win-trace.log) · [Root scores at depths 3, 5, 7, 9, 11](experiments/winrate/records/missed-win-order.txt)

The baseline's loss to the three-ply opponent was already forced **before the baseline made its first move**. The match began with 34 empty cells and the opponent moved first. A 45-second allowance let the independent solver resolve the resulting position with 33 empty. A separate control replay of the six-empty README position detected the greedy move `2 5` taking a forced win to a forced loss. [Baseline loss audit](experiments/winrate/records/shallow-first-loss.json) · [First-turn proof](experiments/winrate/records/shallow-first-turn.json) · [Control replay](experiments/winrate/records/known-miss-audit.jsonl)

## Players and measurements

- The [early-proof player](experiments/winrate/early-proof.cpp) starts its exact win/draw/loss search after seven completed placements of lookahead when 20–22 cells are empty and at most eight choices are legal. The baseline normally waits until depth 11 and checks elapsed time. Both builds use the same weights and 2.65-second clock.
- The [greedy and shallow opponents](experiments/winrate/opponent.cpp) choose the most immediate flips or search three placements ahead with a mobility and anchor evaluator. They break ties deterministically.
- The [margin](experiments/winrate/midgame-margin.cpp) and [outcome](experiments/winrate/midgame-outcome.cpp) players change only the coefficients for 21–62 empty cells. Both start from the frozen player. [The game generator](experiments/winrate/training_games.cpp) ran 3,200 games using randomized openings and a mix of learned two-ply, learned three-ply, greedy and shallow play. There were 44,634 samples from the 3,194 games that reached a sampled position.
- [The fitter](experiments/winrate/fit_midgame.py) checks every feature vector against the frozen C++ evaluator. It fits 35,716 positions from 2,556 games and reserves 8,918 positions from the other 638 games for validation. Each target uses the same training rows, ridge penalty of 32, and 40% of the estimated adjustment. One target is `288 × tanh(margin / 24)`. The other uses the sign of the final margin, scaled to the same training root-mean-square magnitude within each phase. [Training data](experiments/winrate/records/training.csv) · [Validation accuracy](experiments/winrate/records/fit.log)
- The match runner uses a new process per turn, a three-second external timeout, and both colors from each opening. A pair consists of two games. The 20 ms screening builds have a separate filename. The tournament-clock builds use a 2.65-second internal budget.

## Reproducing the trials

From the project root, compile the local players and independent solver.

```sh
cd experiments/winrate
python3 build.py baseline early-proof midgame-margin midgame-outcome
python3 build.py baseline midgame-margin midgame-outcome --milliseconds 20
c++ -std=c++17 -O2 ../../tests/verify.cpp -o bin/verify
c++ -std=c++17 -O2 -DGREEDY opponent.cpp -o bin/greedy
c++ -std=c++17 -O2 opponent.cpp -o bin/shallow
```

Run these commands from `experiments/winrate`. Supply a fresh match filename for each run. The recorder creates it exclusively to preserve prior results.

```sh
python3 ../../tests/match.py bin/early-proof bin/baseline --pairs 6 --opening-plies 62 --seed 820341 --record records/replay-22.jsonl
python3 ../../tests/audit_games.py bin/verify records/replay-22.jsonl --max-empty 22 --seconds 2
python3 compare_positions.py
python3 compare_positions.py --winning
```

To reproduce the missed win, run `bin/baseline < records/missed-win.board`. To verify the two relevant moves from the same board, run the independent solver as follows. The recorded result was `0 1 1`, giving the outcome of `1 1`, the outcome of `1 5`, and the root outcome. [Fixture](experiments/winrate/records/missed-win.board)

```sh
{ printf '45 1 1 1 5\n'; cat records/missed-win.board; } | bin/verify
python3 trace_proof.py
```

[The position comparison](experiments/winrate/compare_positions.py) alternates process launch order and records the board in side-to-move format. The seeded sample contains 18 positions with 20–22 empty cells and two to eight legal moves. The second sample deliberately selects six positions from a separate seed for which the independent solver can prove a win before either player moves. In proof records, the values `1`, `0`, and `−1` mean win, draw, and loss under perfect play. `−9` means the verifier reached its time limit. The [earlier pilot boards](experiments/winrate/pilot) use the input format of `verify`.

Run `python3 summarize.py` to replay every completed match and report each suite's win/draw/loss counts and slowest candidate turn. A failed invocation stops its suite. The recorder saves the starting board, completed moves and the failing side, so the input can be reconstructed.

To regenerate the fitted C++ sources, compile the original game generator and run the fitter with Python and NumPy. The CSV fields are game number, vacancies, final margin from the mover's perspective, low and high 64-bit words for each side, mobility difference, legal-anchor difference, and baseline evaluation.

```sh
c++ -std=c++17 -O2 training_games.cpp -o bin/training-games
bin/training-games 3200 > records/training.csv
python3 fit_midgame.py
```
