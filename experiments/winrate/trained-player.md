# Frozen trained player

## How the player chooses a move

The player stores each side's disks in a 128-bit **bitboard**. It centers the eight rows in a grid with a 16-bit row stride. Padding keeps horizontal and diagonal scans from wrapping into another row. A legal placement brackets at least one uninterrupted run of opposing disks with a friendly disk. The player collects the captures in all eight directions and flips them together.

The search uses **minimax in negamax form**. Both sides try to maximize their own score. For each legal move, the player searches the resulting position from the opponent's perspective, negates that score, and keeps the largest value. A forced pass changes the side to move without consuming a placement.

- **Alpha–beta pruning** skips branches once a reply proves that a candidate cannot improve the current choice. For example, if one move guarantees a draw and the opponent can force a win against another, further replies to the second move cannot make it preferable. This pruning preserves the minimax value of the tree being searched.
- **Iterative deepening** searches one placement ahead, then two, and continues while time permits. A fixed-size transposition table caches previously searched positions, depths, score bounds, and moves. The search tries the cached move first. Later candidates get a narrow score window to see whether they can improve the result before spending time on a wider search.
- **Depth-limited play** uses the evaluation below when the search reaches an unfinished position. Some late-ordered moves get a one-ply reduction and a full-depth recheck if they look competitive. Opening and midgame choices are therefore estimates. A forced win is certain once a search to terminal positions proves it against every reply.

### Time, memory, and the endgame

The assignment gives the player 3 seconds and 500 MB. Each invocation uses one CPU thread and sets a **2.65-second search deadline** on a monotonic clock at program entry. This reserves 350 ms for startup, scheduling delays, and output. The search checks the clock every 256 nodes. It saves a legal fallback before searching and updates its choice after completed iterations or endgame proofs. Its main cache has `2^19` fixed slots and lasts for that invocation.

With 8–22 empty cells, the player can switch from comparing moves at increasing depths to attempting a **win/draw/loss proof**. Smaller endings can reach terminal depth directly. Full-depth searches disable late-move reductions and score terminal boards by actual disk counts. Wins score `20000 + margin`, draws score zero, and losses score `-20000 + margin`, where `margin` is our disk count minus theirs. The clock determines which proofs finish.

If time allows, the player then solves for exact disk margin. In a solved draw or loss, it can favor a move that gives an imperfect opponent more ways to hand us a win while preserving our perfect-play outcome. It considers replies favored by immediate flips, replies favored by a separate three-ply opponent model, and the share of all replies that allow a forced win.

## What the weights mean

The weights are **evaluation points**. The board features and pattern shapes were chosen during development. Their numerical weights were fitted offline on about **280,000 positions from 10,000 self-play games**. Each sampled position was labeled with the eventual disk margin from the side-to-move's perspective. A regularized least-squares regression fitted the feature and pattern contributions together. Its target, `24 × tanh(margin / 24)`, gives large blowouts less influence. The fitted coefficients were multiplied by 12, rounded to integers, and embedded in the source. During a match, the program reads these constants and searches the board it receives. [Evaluation tables and scoring function](baseline.cpp)

**`phaseWeights` contains feature multipliers.** Each feature measures our count minus the opponent's count. The number of empty cells selects the column.

| Feature | 0–20 empty | 21–41 | 42–62 | 63+ |
| --- | ---: | ---: | ---: | ---: |
| Mobility (legal placements) | 5 | 4 | 3 | 1 |
| Frontier disks (touch an empty cell) | −8 | −5 | −4 | −5 |
| Legal moves onto anchors | 7 | 7 | 14 | 6 |
| Edge disks beside an empty anchor | 12 | 4 | −4 | −12 |
| Interior disks beside an empty anchor | −4 | −12 | −45 | −57 |
| Stable non-anchor disks along the flat edges | 11 | 17 | 18 | 21 |
| Occupied flat-edge anchors | 17 | 28 | 50 | 69 |
| Occupied side anchors | 8 | 12 | 43 | 22 |
| Other flat-edge disks | −4 | −7 | −8 | −7 |
| Non-anchor sloping-edge disks | 0 | 4 | 2 | 3 |
| Total disks | 3 | 1 | 0 | 0 |

An **anchor** is a square where the board geometry prevents a disk from ever being sandwiched. A same-color run along the top or bottom row connected to an occupied endpoint is also stable. As a scoring example, with 18 empty cells, seven legal moves for us and four for the opponent contribute `5 × (7 − 4) = +15` mobility points.

**`learnedPatterns` scores local arrangements.** Each phase has three four-cell patterns covering a flat corner and its neighbors, a sloping edge, and half a flat edge. The evaluator applies each pattern at four reflected locations. Four cells admit `3^4 = 81` arrangements. The empty arrangement scores zero, and exchanging the colors negates the score. That leaves 40 stored values per pattern, or **480 learned pattern weights** in total.

The first three entries, `2, -17, 8`, illustrate the encoding. In the late-game corner pattern, consider the first two input cells of each of the top two rows. A lone friendly disk in the top-left cell contributes **+2** pattern points. A lone friendly disk immediately to its right contributes **−17**. If the opponent occupies the top-left cell and our disk is immediately to its right, the pattern contributes **+8**. In each example the other two cells are empty. The evaluator adds these points to the feature scores and the contributions from the other patterns.

