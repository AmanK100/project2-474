// Standalone 88-cell Reversi player. No trained data or evaluation weights.
#include <algorithm>
#include <array>
#include <chrono>
#include <cstdint>
#include <iostream>

namespace {
using Bits = __uint128_t;
using Clock = std::chrono::steady_clock;
constexpr std::array<int, 8> rows{8, 10, 12, 14, 14, 12, 10, 8};
constexpr int cellCount = 88;
constexpr int infinity = 2 * cellCount + 1;
constexpr auto timeBudget = std::chrono::milliseconds(2650);

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
Bits board;

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
void initBoard() {
    for (int row = 0; row < static_cast<int>(rows.size()); ++row) {
        int offset = (14 - rows[row]) / 2;
        for (int column = 0; column < rows[row]; ++column)
            board |= bit(16 * row + offset + column);
    }
}

int diskDifference(Position p) {
    return count(p.us) - count(p.them);
}

// A finished win outranks every unfinished estimate. Within the same
// outcome, prefer a larger final margin. The offset is the board size.
int terminalScore(Position p) {
    int margin = diskDifference(p);
    if (margin > 0) return cellCount + margin;
    if (margin < 0) return margin - cellCount;
    return 0;
}

enum class Bound : uint8_t { exact, lower, upper };
struct Entry {
    Position position;
    int16_t score;
    uint8_t depth, square;
    Bound bound;
};
constexpr unsigned cacheSize = 1u << 19;
std::array<Entry, cacheSize> cache{};

Entry& entryFor(Position p) {
    // Use the standard 64-bit FNV offset and prime to mix the four words.
    // The hash only chooses a slot. Both complete bitboards identify a hit.
    uint64_t hash = 14695981039346656037ULL;
    for (uint64_t word : {uint64_t(p.us), uint64_t(p.us >> 64),
                          uint64_t(p.them), uint64_t(p.them >> 64)}) {
        hash ^= word;
        hash *= 1099511628211ULL;
    }
    hash ^= hash >> 32;
    return cache[hash & (cacheSize - 1)];
}

struct Timeout {};
Clock::time_point deadline;
unsigned nodes;
struct Candidate {
    int square;
    Position child;
    Bits replies;
    int replyCount;
};

int minimax(Position p, Bits legal, int depth, int alpha, int beta, int& best) {
    if ((++nodes & 255) == 0 && Clock::now() >= deadline) throw Timeout{};
    if (!legal) {
        Position passed{p.them, p.us};
        Bits replies = moves(passed);
        if (!replies) return terminalScore(p);
        int ignored;
        return -minimax(passed, replies, depth, -beta, -alpha, ignored);
    }
    if (depth == 0) return diskDifference(p);

    Entry& entry = entryFor(p);
    int preferred = -1;
    if (entry.depth && entry.position.us == p.us && entry.position.them == p.them) {
        preferred = entry.square;
        if (entry.depth == depth &&
            (entry.bound == Bound::exact ||
             (entry.bound == Bound::lower && entry.score >= beta) ||
             (entry.bound == Bound::upper && entry.score <= alpha))) {
            best = preferred;
            return entry.score;
        }
    }

    int initialAlpha = alpha;
    int value = -infinity;
    auto examine = [&](int square, Position child, Bits replies) {
        int ignored;
        int score = -minimax(child, replies, depth - 1, -beta, -alpha, ignored);
        if (score > value) {
            value = score;
            best = square;
        }
        alpha = std::max(alpha, value);
    };

    // Move order affects how soon alpha-beta can cut off a branch.
    if (preferred >= 0) {
        Position child = play(p, bit(preferred));
        legal &= ~bit(preferred);
        examine(preferred, child, moves(child));
    }
    if (depth == 1) {
        for (; legal && alpha < beta; legal &= legal - 1) {
            int square = first(legal);
            Position child = play(p, bit(square));
            examine(square, child, moves(child));
        }
    } else if (legal && alpha < beta) {
        std::array<Candidate, cellCount> options;
        int size = 0;
        for (; legal; legal &= legal - 1) {
            int square = first(legal);
            Position child = play(p, bit(square));
            Bits replies = moves(child);
            options[size++] = {square, child, replies, count(replies)};
        }
        std::sort(options.begin(), options.begin() + size, [](const Candidate& a, const Candidate& b) {
            if (a.replyCount != b.replyCount) return a.replyCount < b.replyCount;
            return a.square < b.square;
        });
        for (int i = 0; i < size && alpha < beta; ++i)
            examine(options[i].square, options[i].child, options[i].replies);
    }
    Bound bound = Bound::exact;
    if (value <= initialAlpha) bound = Bound::upper;
    else if (value >= beta) bound = Bound::lower;
    entry = {p, static_cast<int16_t>(value), static_cast<uint8_t>(depth),
             static_cast<uint8_t>(best), bound};
    return value;
}
} // namespace

int main() {
    deadline = Clock::now() + timeBudget;
    initBoard();
    Position p{};
    for (Bits cells = board; cells; cells &= cells - 1) {
        int disk;
        if (!(std::cin >> disk) || disk < 0 || disk > 2) return 1;
        Bits square = bit(first(cells));
        if (disk == 1) p.us |= square;
        if (disk == 2) p.them |= square;
    }
    Bits legal = moves(p);
    if (!legal) {
        std::cout << "0 0\n";
        return 0;
    }
    int best = first(legal);
    if (legal & (legal - 1)) {
        int empty = cellCount - count(p.us | p.them);
        try {
            for (int depth = 1; depth <= empty; ++depth) {
                int candidate = best;
                minimax(p, legal, depth, -infinity, infinity, candidate);
                best = candidate;
            }
        } catch (const Timeout&) {
            // The last fully searched depth supplied best.
        }
    }
    int row = best / 16;
    std::cout << row + 1 << ' ' << best % 16 - (14 - rows[row]) / 2 + 1 << '\n';
    return 0;
}
