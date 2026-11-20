# Weight-free search experiments

## Implementation decision

The [project player](reversi.cpp) now uses untrained mobility at unfinished leaves with more than 22 vacancies and disk count in the endgame. It is the same source as the [validated mobility finalist](experiments/search-ab/phase.cpp). The [frozen disk-count player](experiments/search-ab/control.cpp) is available for comparison. The internal search budget remains 2.65 seconds per move.

The rebuilt project executable returned `4 6` on the assignment sample, `7 1` on the six-empty example and `0 0` on the pass check. It matched the independent exact margin on all 96 ordinary CLI regression endgames. The production search also passed the 76 fixed-depth regression checks using an AddressSanitizer/UndefinedBehaviorSanitizer probe. Its source SHA-256 is `a8c3ef0932d0e860da7c5a02c9bb5a479ac5ef5cc97d292214722dedb69c996b`. [CLI examples](experiments/search-ab/results/submission-cli.json) · [Regression log](experiments/search-ab/results/regression-submission.log) · [Sanitizer run](experiments/search-ab/results/regression-sanitized.log)

| Held-out comparison against disk-count control | Pairs | Wins | Draws | Losses | Candidate win advantage | Two-sided paired p |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Restricted mobility, decision sample | 30 | 44 | 1 | 15 | +29 | 0.000061 |
| PVS alone, first look | 30 | 29 | 1 | 30 | −1 | 1.000 |
| PVS alone, cumulative final look | 60 | 64 | 2 | 54 | +10 | 0.125 |

Mobility improved the match-win balance on 15 paired openings and tied on the other 15. None favored the control. Its net wins by starting range were **+18 early, +11 middle, and 0 late**. It made 1,418 turns in this sample, with a maximum elapsed time of 2.772 seconds and zero forfeits. The local opponents and opening distribution define the scope of these results. [First-look records and paired statistics](experiments/search-ab/results/first-look.json)

PVS finished ahead by ten wins across 120 games. Fifty of its 60 opening pairs contributed zero to that difference. The paired result (`p = 0.125`) did not meet the promotion threshold. The project keeps ordinary alpha–beta and the winning mobility evaluation. Across all comparisons, **200 completed games were replayed and verified with zero forfeits**. [Final paired results](experiments/search-ab/results/final-summary.json) · [PVS experimental source](experiments/search-ab/pvs.cpp)

## Standard opening and sparring partners

| Candidate | Standard vs. disk control | Standard vs. archived trained player | Seeded vs. greedy | Same seed vs. three-ply |
| --- | --- | --- | --- | --- |
| Restricted mobility | 2–0 | 0–2 | 2–0 | 1–1 |
| PVS alone | 1–1 | 0–2 | 2–0 | 0–2 |
| Disk control | — | 0–2 in the prior validation | 2–0 | 0–2 |

Each current entry is one color-swapped pair. The mobility player beat the disk control **75–13 and 72–15**. With 44 cells empty it had 16 legal moves to 3 as the first color and 18 to 2 as the second. Against the archived trained player it also had more legal moves at that checkpoint in both games, yet lost **13–75 and 2–85**. Having many legal moves helps in this comparison; it does not capture all differences in move quality. The independent solver checked all **83 playable finalist turns with at most 22 empty** in the eight current standard-opening games. Every selected move preserved the best available win/draw/loss outcome. [Recorded matches](experiments/search-ab/results) · [Independent late-turn audit](experiments/search-ab/results/standard-audit.jsonl)

## Match design

The frozen control is the disk-count player used in the [baseline validation](MINIMAX_VALIDATION.md). Two candidates change one decision each. Mobility ranks unfinished leaves by legal-move difference, breaking ties by disk difference. Principal variation search (PVS) uses disk-count evaluation, scouts later moves with a one-point window, and re-searches challengers.

Before opening the held-out results, check each candidate against exhaustive fixed-depth minimax, exact small endgames, and the ten saved winnable positions. If mobility at every cutoff loses known endgame wins, restrict the mobility experiment to unfinished leaves with more than 22 empty cells and recheck the fixtures. This cutoff comes from the previous validation's late-game audit.

Each eligible candidate plays the frozen control twice from each of 30 fresh openings, once per color. There are ten openings in each of three starting ranges: 16–22, 38–44, and 58–64 placements after the central four disks. The standard start and greedy and three-ply opponents are separate diagnostics. Each tournament executable is single-threaded with its normal 2.65-second deadline. The match referee launches a fresh process per turn, validates the move and enforces three seconds. An illegal move, process failure or timeout forfeits the game.

The primary result is the candidate's wins minus the control's wins per opening pair. A tied game contributes zero to either win count. Use a two-sided paired sign-flip test of the win difference, with a 0.0125 threshold to allow for two candidates and two planned looks. If the 30-pair result is inconclusive for an eligible candidate, run 30 more disjoint pairs and evaluate all 60. Prefer a candidate only if it improves wins, passes the correctness and resource checks, and shows no candidate forfeits in the promotion sample. If both qualify, favor the larger paired improvement. Combining the two changes would require its own test.

## Correctness and search cost

| Candidate | Exhaustive fixed-depth checks | Exact final margin, 5–13 empty | Saved forced wins | CLI and resource checks |
| --- | ---: | ---: | ---: | ---: |
| Mobility at every unfinished leaf | 112/112 | 108/108 | 9/10 | Screen ended at tactical regression |
| Mobility above 22 vacancies; disk count thereafter | 112/112 | 108/108 | 10/10 | 21/21 |
| PVS, disk count throughout | 112/112 | 108/108 | 10/10 | 21/21 |

The all-phase mobility player chose `6 2` on the saved 21-empty position. It guarantees a draw, while `1 5` forces a win. The restricted mobility player and PVS both selected `1 5`. The restriction is on empty cells at the search leaf. Passes consume no placements. Every scheduled depth therefore has a consistent evaluation across its unfinished leaves. [Mobility results](experiments/search-ab/results/check-mobility.jsonl) · [Restricted mobility results](experiments/search-ab/results/check-phase.jsonl) · [PVS results](experiments/search-ab/results/check-pvs.jsonl)

For an early or midgame leaf, mobility is our legal-move count minus theirs. The integer score is `177 × mobility + disk difference`. The factor is derived directly from the 88-cell board: disk differences span at most 176 points, so one additional legal move always wins the comparison. Terminal wins and losses outrank all unfinished estimates. All candidates use the same perfect-play final outcome and disk-margin ordering. The two finalists' peak resident memory in the CLI suite was under 26 MiB each. [Mobility measurements](experiments/search-ab/results/resources-phase.jsonl) · [PVS measurements](experiments/search-ab/results/resources-pvs.jsonl)

PVS returned the full-window score on **20/20 boards at depth nine**. Each returned move was also checked by independently searching its child with the full-window control. PVS visited **25,838,099 nodes**, compared with **35,356,493** for the control, a **26.9% reduction**. It used fewer nodes on each board. With the tournament clock, PVS completed one additional placement on the saved 21-empty puzzle (16 vs. 15). The other three traced boards reached the same depth as the control. [Fixed-depth and timed traces](experiments/search-ab/results/profile.jsonl)

## Reproduction

From the project root, compile each standalone source in `experiments/search-ab` with `c++ -std=c++17 -O2`. The [referee driver](experiments/search-ab/arena.py) records every turn, binary hash, final disk counts or forfeit, seed, and starting board. The two colors share the same starting board. Separate games can run concurrently. The [summary tool](experiments/search-ab/summarize.py) checks the seeds and replays the games with the independent Python rules before aggregating complete pairs. The [opening manifest](experiments/search-ab/results/openings.jsonl) records 60 distinct positions, each different from the stored screening positions.

The following commands rebuild the finalists and write a separate set of match records. The archived opponent and oracle build instructions are in the [trained-player report](TRAINED_PLAYER_EXPERIMENTS.md) and the [control validation](MINIMAX_VALIDATION.md).

```sh
D=experiments/search-ab
for player in control pvs mobility phase; do
    c++ -std=c++17 -O2 "$D/$player.cpp" -o "$D/bin/$player"
    c++ -std=c++17 -O2 "-DPLAYER=\"$player.cpp\"" "$D/probe.cpp" -o "$D/bin/$player-probe"
done
python3 -B "$D/check.py" phase
python3 -B "$D/check.py" pvs
python3 -B "$D/profile.py"
python3 -B "$D/arena.py" phase pvs --stage holdout --count 30 --jobs 3 --output "$D/repeat"
python3 -B "$D/summarize.py" --input "$D/repeat" --replay
```
