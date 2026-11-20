// Middle phases refitted by fit_midgame.py using margin labels.
// Single-turn player for the 88-cell Reversi board.
#include <algorithm>
#include <array>
#include <chrono>
#include <cstdint>
#include <iostream>

namespace {
using Bits = __uint128_t;
using Clock = std::chrono::steady_clock;
constexpr int rows[] = {8, 10, 12, 14, 14, 12, 10, 8};
constexpr int infinity = 32000;
constexpr int win = 20000;

Bits bit(int square) { return Bits{1} << square; }
int count(Bits b) {
    return __builtin_popcountll(static_cast<uint64_t>(b)) +
           __builtin_popcountll(static_cast<uint64_t>(b >> 64));
}
int first(Bits b) { // b is nonzero
    uint64_t low = static_cast<uint64_t>(b);
    return low ? __builtin_ctzll(low) : 64 + __builtin_ctzll(static_cast<uint64_t>(b >> 64));
}

struct Position { Bits us, them; };
Bits board, anchors, flatEdges, slopingEdges;
std::array<int, 256> fixedOnRow{};

// Each row occupies 16 bits. Empty padding prevents rays wrapping across rows.
template<int d> Bits shift(Bits x) {
    if constexpr (d > 0) return x << d;
    else return x >> -d;
}

// Reach through contiguous enemy disks, doubling the covered distance each round.
template<int d> Bits run(Bits start, Bits enemy) {
    Bits reached = shift<d>(start) & enemy;
    reached |= shift<d>(reached) & enemy;
    Bits pairs = enemy & shift<d>(enemy);
    reached |= shift<2*d>(reached) & pairs;
    if constexpr (d == 1 || d == -1) {
        Bits fours = pairs & shift<2*d>(pairs);
        reached |= shift<4*d>(reached) & fours;
        reached |= shift<4*d>(reached) & fours;
    } else {
        // At most six opposing disks fit between endpoints on different rows.
        reached |= shift<2*d>(reached) & pairs;
    }
    return reached;
}
template<int d> Bits targets(Position p) { return shift<d>(run<d>(p.us, p.them)); }
Bits moves(Position p) {
    return board & ~(p.us | p.them) &
        (targets<1>(p) | targets<-1>(p) | targets<16>(p) | targets<-16>(p) |
         targets<15>(p) | targets<-15>(p) | targets<17>(p) | targets<-17>(p));
}
template<int d> Bits captures(Position p, Bits move) {
    Bits chain = run<d>(move, p.them);
    return (shift<d>(chain) & p.us) ? chain : 0;
}
Position play(Position p, Bits move) {
    Bits flipped = captures<1>(p, move) | captures<-1>(p, move) |
                   captures<16>(p, move) | captures<-16>(p, move) |
                   captures<15>(p, move) | captures<-15>(p, move) |
                   captures<17>(p, move) | captures<-17>(p, move);
    return {p.them ^ flipped, p.us | flipped | move};
}
Bits adjacent(Bits x) {
    return (x << 1) | (x >> 1) | (x << 16) | (x >> 16) |
           (x << 15) | (x >> 15) | (x << 17) | (x >> 17);
}
// Fitted on about 280,000 positions from 10,000 locally played games.
// Target: final disk margin, with large blowouts downweighted. Each phase
// has three four-cell patterns: the flat corner and its neighbors, the
// sloping edge, and half the flat edge. Each has 40 nonempty states up to
// color reversal. All weights are built into the tournament executable.
constexpr int patternFamilies = 3;
constexpr int8_t learnedPatterns[4][patternFamilies][40] = {{{2, -17, 8, 1, -6, -1, 10, -2, 14, 16, -16, -13, 20, 0, -11, 3, -6, -1, -6, -10, 11, -11, -8, 5, 0, -24, -18, -28, 12, -17, 0, -9, -4, -12, 16, 3, -1, -38, 21, 5},
    {19, -4, -31, 20, -8, -24, -9, -12, -18, -27, -3, -29, 4, 1, 1, 15, 2, 5, 9, 7, -14, 0, -5, -6, -20, -3, -7, -18, 0, -2, -13, 14, 16, 4, -1, 1, -13, 15, 15, 5},
    {15, -12, -2, 16, 9, -7, 34, 2, -4, 10, -2, -3, 14, 11, -4, -3, -2, 1, 8, 21, 5, 19, 8, 12, -8, -24, -3, -1, 0, -7, -11, 0, -6, 26, 14, -16, -2, 3, 19, -3}},
    {{-1, -19, 2, 2, -6, -4, 5, 3, 13, 13, -15, -8, 11, -15, -7, 0, -4, -12, -7, -12, 9, -13, -9, 6, 4, -23, -3, -36, 13, -12, 0, -11, -10, -19, 16, 16, 4, -39, 16, 11},
    {20, -2, -34, 19, -10, -24, -16, -4, -28, -27, -2, -29, 6, -1, -9, 0, -10, 12, -3, 27, -15, 8, -2, -7, -21, -10, -13, -15, 0, 7, -9, 25, 25, 7, 7, -25, -10, 20, 19, 6},
    {13, -8, -13, 19, -2, -17, 46, -16, 3, -17, 6, -12, 7, 6, -5, 1, -20, 10, 19, 24, 13, 16, 28, 18, -22, -9, -19, -32, 0, -27, -12, 10, -5, 15, 14, -9, -8, 22, 33, -7}},
    {{2, -25, 4, 13, -6, -5, 22, 7, 3, -3, -17, 1, 7, -7, -23, 19, -11, -11, 0, -18, 9, -11, -9, 17, 17, 1, -1, -18, 9, -6, 17, 11, -4, -17, 18, 14, -4, -12, 28, 21},
    {15, 4, -25, 20, 0, -26, 6, -2, -30, -21, 1, -3, 3, 3, -3, -10, 0, -1, 0, -5, 7, 21, 0, 0, -1, 5, -3, -2, 0, 27, -12, 14, 4, -6, 4, -8, 5, 3, 8, -7},
    {14, -6, -23, 11, -5, -27, 37, -30, -23, -27, 10, -5, 15, 5, -10, 5, -40, 11, -7, 21, 8, 7, 34, 27, -38, -6, -21, -35, 0, -34, -24, 23, -7, 15, 3, -18, -30, 38, 26, 4}},
    {{-3, -24, -15, 0, -4, -9, 15, -6, 9, -5, -13, -7, 4, -1, -25, 31, -27, -11, 6, -4, -6, -11, -8, 10, 2, 33, -7, -1, -3, -9, -1, 20, 6, -9, 5, -2, -5, -6, -2, 15},
    {11, 12, -20, 17, 16, -27, -5, -1, 2, 2, 1, 2, -7, 7, 0, 0, 2, 2, 0, 0, 2, 2, 0, 0, 2, -2, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 5, -2, 10},
    {5, -7, -24, 1, -2, -32, 30, -17, -18, -10, 22, -16, 15, 1, -2, -3, -18, 1, -4, 9, -12, -10, 17, 14, -31, -10, -6, -25, 0, -15, -19, 22, -3, 27, -11, -9, -15, 39, -11, 3}}};
int8_t patternValue[4][patternFamilies][256];
void initPatterns() {
    for (int phase = 0; phase < 4; ++phase) {
        for (int family = 0; family < patternFamilies; ++family) {
            int index = 0;
            for (int us = 0; us < 16; ++us) {
                for (int them = 0; them < us; ++them) {
                    if (us & them) continue;
                    int value = learnedPatterns[phase][family][index++];
                    patternValue[phase][family][us | (them << 4)] = value;
                    patternValue[phase][family][them | (us << 4)] = -value;
                }
            }
        }
    }
}

template<int A, int B, int C, int D> int fourCells(Bits b) {
    return int((b >> A) & 1) | (int((b >> B) & 1) << 1) |
           (int((b >> C) & 1) << 2) | (int((b >> D) & 1) << 3);
}
template<int A, int B, int C, int D> int patternIndex(Position p) {
    return fourCells<A,B,C,D>(p.us) | (fourCells<A,B,C,D>(p.them) << 4);
}
// Each group of four lines evaluates the same pattern at its four reflected
// locations. Constants use the padded board index (16*row + column).
int patternScore(Position p, int phase) {
    return patternValue[phase][0][patternIndex<3, 4, 18, 19>(p)] +
           patternValue[phase][0][patternIndex<10, 9, 27, 26>(p)] +
           patternValue[phase][0][patternIndex<115, 116, 98, 99>(p)] +
           patternValue[phase][0][patternIndex<122, 121, 107, 106>(p)] +
           patternValue[phase][1][patternIndex<3, 18, 33, 48>(p)] +
           patternValue[phase][1][patternIndex<10, 27, 44, 61>(p)] +
           patternValue[phase][1][patternIndex<115, 98, 81, 64>(p)] +
           patternValue[phase][1][patternIndex<122, 107, 92, 77>(p)] +
           patternValue[phase][2][patternIndex<3, 4, 5, 6>(p)] +
           patternValue[phase][2][patternIndex<10, 9, 8, 7>(p)] +
           patternValue[phase][2][patternIndex<115, 116, 117, 118>(p)] +
           patternValue[phase][2][patternIndex<122, 121, 120, 119>(p)];
}

void initBoard() {
    initPatterns();
    for (int r = 0; r < 8; ++r)
        for (int c = 0; c < rows[r]; ++c)
            board |= bit(16*r + (14-rows[r])/2 + c);

    for (Bits cells = board; cells; cells &= cells-1) {
        int s = first(cells);
        Bits b = bit(s);
        int axes = 0;
        for (int axis : {1, 15, 16, 17})
            axes += bool(board & (b << axis)) && bool(board & (b >> axis));
        if (axes == 0) anchors |= b;
        if (s / 16 == 0 || s / 16 == 7) flatEdges |= b;
        else if (axes == 1) slopingEdges |= b;
    }
    // On the top and bottom rows a same-color run joined to an endpoint is permanent.
    for (unsigned row = 0; row < 256; ++row) {
        unsigned fixed = 0;
        for (int i = 0; i < 8 && (row & (1u << i)); ++i) fixed |= 1u << i;
        for (int i = 7; i >= 0 && (row & (1u << i)); --i) fixed |= 1u << i;
        fixedOnRow[row] = __builtin_popcount(fixed & 126u); // endpoints are scored separately
    }
}

int difference(Bits mask, Position p) { return count(mask & p.us) - count(mask & p.them); }
struct EvalWeights {
    int mobility, frontier, anchorMoves, exposedEdge, exposedInterior, stableEdge;
    int flatAnchor, sideAnchor, flatEdge, slopingEdge, disks;
};

// Rows run from endgame to opening. Weights were fitted on games played on this board.
constexpr EvalWeights phaseWeights[] = {{5, -8, 7, 12, -4, 11, 17, 8, -4, 0, 3},
    {4, -4, 7, 4, -11, 21, 22, 12, -9, 3, 1},
    {2, -6, 11, 1, -40, 22, 39, 35, -13, 1, 0},
    {1, -5, 6, -12, -57, 21, 69, 22, -7, 3, 0}};

int fixedEdgeDisks(Bits disks) {
    return fixedOnRow[static_cast<unsigned>(disks >> 3) & 255] +
           fixedOnRow[static_cast<unsigned>(disks >> 115) & 255];
}
int evaluate(Position p, Bits legal, Bits replies, int empty) {
    int phase = std::min(3, empty / 21);
    const EvalWeights& w = phaseWeights[phase];
    Bits vacancies = board & ~(p.us | p.them);
    Bits exposed = adjacent(anchors & vacancies);
    Bits edge = flatEdges | slopingEdges | anchors;
    return patternScore(p, phase) + w.mobility * (count(legal) - count(replies)) +
           w.frontier * difference(adjacent(vacancies), p) +
           w.anchorMoves * (count(legal & anchors) - count(replies & anchors)) +
           w.exposedEdge * difference(exposed & edge, p) +
           w.exposedInterior * difference(exposed & ~edge, p) +
           w.stableEdge * (fixedEdgeDisks(p.us) - fixedEdgeDisks(p.them)) +
           w.flatAnchor * difference(flatEdges & anchors, p) +
           w.sideAnchor * difference(anchors & ~flatEdges, p) +
           w.flatEdge * difference(flatEdges & ~anchors, p) +
           w.slopingEdge * difference(slopingEdges, p) +
           w.disks * (count(p.us) - count(p.them));
}
// The shallow opponent model favors mobility and immediate anchor safety.
// It predicts rival replies only after the actual match outcome is solved.
int opponentEstimate(Position p, Bits legal, Bits replies, int empty) {
    Bits vacancies = board & ~(p.us | p.them);
    int mobility = count(legal) - count(replies);
    int frontier = difference(adjacent(vacancies), p);
    Bits exposed = adjacent(anchors & vacancies);
    int material = count(p.us) - count(p.them);
    return 105*difference(anchors, p) - 18*difference(exposed, p) +
           13*mobility - 5*frontier + (empty < 16 ? 4 : 0)*material;
}
int terminal(Position p) {
    int diff = count(p.us) - count(p.them);
    return diff > 0 ? win + diff : diff < 0 ? -win + diff : 0;
}

enum Bound : uint8_t { exact, lower, upper };
struct Entry {
    Position position;
    int16_t value;
    uint8_t depth, best, bound;
};
constexpr unsigned slots = 1u << 19;
Entry table[slots];
Entry& lookup(Position p) {
    uint64_t h = static_cast<uint64_t>(p.us) * 0x9e3779b185ebca87ULL ^
                 static_cast<uint64_t>(p.us >> 64) * 0xc2b2ae3d27d4eb4fULL ^
                 static_cast<uint64_t>(p.them) * 0x165667b19e3779f9ULL ^
                 static_cast<uint64_t>(p.them >> 64) * 0x85ebca77c2b2ae63ULL;
    h ^= h >> 33;
    return table[(h * 0xff51afd7ed558ccdULL) >> (64-19)];
}

struct Timeout {};
Clock::time_point deadline;
unsigned nodes;
struct Candidate { Position child; Bits replies; int square, priority; };

Candidate rankedMove(Position p, int square, int preferred) {
    Position child = play(p, bit(square));
    Bits replies = moves(child);
    int priority = (square == preferred ? 1000 : 0) + ((bit(square) & anchors) ? 200 : 0)
                   - count(replies) - 25*count(replies & anchors);
    return {child, replies, square, priority};
}
bool higherPriority(const Candidate& a, const Candidate& b) { return a.priority > b.priority; }

template<auto leafEstimate = evaluate>
int search(Position p, Bits legal, int depth, int empty, int alpha, int beta, int& best) {
    if ((++nodes & 255) == 0 && Clock::now() >= deadline) throw Timeout{};
    if (!legal) {
        Position other{p.them, p.us};
        Bits replies = moves(other);
        if (!replies) return terminal(p);
        int unused;
        return -search<leafEstimate>(other, replies, depth, empty, -beta, -alpha, unused);
    }
    if (empty == 1) {
        best = first(legal);
        return -terminal(play(p, legal));
    }
    if (!depth) return leafEstimate(p, legal, moves({p.them, p.us}), empty);
    Entry& e = lookup(p);
    int preferred = -1;
    if (e.position.us == p.us && e.position.them == p.them) {
        preferred = e.best;
        if (leafEstimate == evaluate && e.depth == depth && (e.bound == exact || (e.bound == lower && e.value >= beta) ||
                                  (e.bound == upper && e.value <= alpha))) {
            best = preferred;
            return e.value;
        }
    }

    std::array<Candidate, 88> options;
    int size = 0;
    Bits untried = legal;
    if (preferred >= 0) {
        options[size++] = rankedMove(p, preferred, preferred);
        untried ^= bit(preferred);
    }
    int initialAlpha = alpha, value = -infinity;
    for (int i = 0; i < size || untried; ++i) {
        // The cached move often causes a cutoff on its own. Generate and
        // sort alternatives only if the search actually reaches them.
        if (i == size) {
            if (depth == 1) {
                int square = first(untried);
                untried &= untried-1;
                Position child = play(p, bit(square));
                options[size++] = {child, moves(child), square, 0};
            } else {
                for (; untried; untried &= untried-1)
                    options[size++] = rankedMove(p, first(untried), -1);
                std::sort(options.begin()+i, options.begin()+size, higherPriority);
            }
        }
        const Candidate& m = options[i];
        int unused, score;
        if (i == 0 || depth <= 2) {
            score = -search<leafEstimate>(m.child, m.replies, depth-1, empty-1, -beta, -alpha, unused);
        } else {
            // Probe later moves one ply shallower. Verify challengers at
            // full depth, and keep all terminal-depth searches exhaustive.
            bool reduce = depth >= 4 && depth < empty && i >= 4 &&
                          m.replies && !(bit(m.square) & anchors);
            score = -search<leafEstimate>(m.child, m.replies, depth-1-reduce, empty-1, -alpha-1, -alpha, unused);
            if (reduce && score > alpha)
                score = -search<leafEstimate>(m.child, m.replies, depth-1, empty-1, -alpha-1, -alpha, unused);
            if (score > alpha && score < beta)
                score = -search<leafEstimate>(m.child, m.replies, depth-1, empty-1, -beta, -alpha, unused);
        }
        if (score > value) { value = score; best = m.square; }
        alpha = std::max(alpha, value);
        if (alpha >= beta) break;
    }
    Bound bound = value <= initialAlpha ? upper : value >= beta ? lower : exact;
    // Cache player scores only. The rival model can reuse the move order.
    if constexpr (leafEstimate == evaluate) {
        e = {p, static_cast<int16_t>(value), static_cast<uint8_t>(depth),
             static_cast<uint8_t>(best), bound};
    }
    return value;
}

// Search to the end, first asking whether the opponent can force a win,
// then whether they can force a draw. Keep each proof as soon as it finishes.
void findWinningMove(Position p, Bits legal, int empty, int& best) {
    const int heuristicBest = best;
    std::array<Candidate, 88> options;
    int size = 0;
    for (Bits rest = legal; rest; rest &= rest-1)
        options[size++] = rankedMove(p, first(rest), heuristicBest);
    std::sort(options.begin(), options.begin()+size, higherPriority);
    bool drawSecured = false;
    int remaining = empty-1;
    for (int i = 0; i < size; ++i) {
        const Candidate& m = options[i];
        int reply;
        if (!drawSecured) {
            // Earlier candidates have all been proved losing. If interrupted
            // while testing this one, keep it as the best remaining chance.
            best = m.square;
            int outcome = search(m.child, m.replies, remaining, remaining, 0, 1, reply);
            if (outcome > 0) continue;
            if (outcome < 0) return;
            drawSecured = true;
        }
        if (search(m.child, m.replies, remaining, remaining, -1, 0, reply) < 0) {
            best = m.square;
            return;
        }
    }
    if (!drawSecured) best = heuristicBest;
}

// Among replies tied for an opponent's preferred score, count the ones
// that give us a forced win.
struct ReplyChoices {
    int highest = -infinity, choices = 0, errors = 0;
    void add(int score, bool allowsWin) {
        if (score > highest) {
            highest = score;
            choices = errors = 0;
        }
        if (score == highest) {
            ++choices;
            errors += allowsWin;
        }
    }
    double winFraction() const { return choices ? double(errors)/choices : 0; }
};

// Keep the perfect-play outcome. Within a solved draw or loss, favor
// winning opportunities against greedy or shallow-search opponents.
void preferWinningChances(Position p, Bits legal, int empty, bool canDraw, int& best) {
    double bestChance = -1;
    int square = best;
    for (Bits remaining = legal; remaining;) {
        remaining ^= bit(square);
        Position opponent = play(p, bit(square));
        Bits replies = moves(opponent);
        ReplyChoices material, lookahead;
        bool preservesOutcome = true;
        int wins = 0;
        for (Bits rest = replies; rest; rest &= rest-1) {
            Position next = play(opponent, bit(first(rest)));
            Bits nextMoves = moves(next);
            int unused;
            int value = search(next, nextMoves, empty-2, empty-2, canDraw ? -1 : 0, 1, unused);
            if (canDraw && value < 0) {
                preservesOutcome = false;
                break;
            }
            int shallow = -search<opponentEstimate>(next, nextMoves, std::min(2, empty-2),
                                                    empty-2, -infinity, infinity, unused);
            material.add(count(next.them), value > 0);
            lookahead.add(shallow, value > 0);
            wins += value > 0;
        }
        // Give equal weight to most-flips play, a three-ply opponent, and
        // the share of all replies that allow a win. A pass is compulsory.
        double chance = replies ? (material.winFraction() + lookahead.winFraction() +
                                   double(wins)/count(replies)) : 0;
        if (preservesOutcome && chance > bestChance + 1e-9) {
            bestChance = chance;
            best = square;
        }
        if (remaining) square = first(remaining);
    }
}
} // namespace

int main() {
    const auto start = Clock::now();
    const auto budget = std::chrono::milliseconds(2650); // Reserve 350 ms of the per-move limit.
    deadline = start + budget;
    initBoard();
    Position p{};
    for (Bits cells = board; cells; cells &= cells-1) {
        int v;
        if (!(std::cin >> v) || v < 0 || v > 2) return 1;
        Bits square = bit(first(cells));
        if (v == 1) p.us |= square;
        if (v == 2) p.them |= square;
    }
    Bits legal = moves(p);
    if (!legal) {
        std::cout << "0 0\n"; // Out-of-board pass sentinel; assignment leaves this unspecified.
        return 0;
    }
    int best = first(legal);
    int empty = 88 - count(p.us | p.them);
    if (legal & (legal-1)) {
        try {
            for (int d = 1; d < empty; ++d) {
                int candidate = best;
                search(p, legal, d, empty, -infinity, infinity, candidate);
                best = candidate;
                // On larger endgames, first spend part of the budget comparing
                // root moves. A proof may cost the rest of the turn.
                if (empty >= 8 && empty <= 22 && d >= std::clamp(empty-7, 5, 11) &&
                    (empty <= 18 || Clock::now() >= start + budget/5 || d >= empty-2)) {
                    findWinningMove(p, legal, empty, best);
                    break;
                }
            }
            int exactMove = best;
            int value = search(p, legal, empty, empty, -infinity, infinity, exactMove);
            best = exactMove;
            if (value <= 0) preferWinningChances(p, legal, empty, value == 0, best);
        } catch (const Timeout&) { /* best already holds a legal move. */ }
    }
    int row = best / 16;
    std::cout << row+1 << ' ' << best%16 - (14-rows[row])/2 + 1 << '\n';
    return 0;
}
