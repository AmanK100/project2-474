// Generate original games and sample middle-game positions for both training targets.
#define main frozenPlayerMain
#include "baseline.cpp"
#undef main
#include <random>
#include <vector>

namespace {
enum Style { learnedTwo, learnedThree, shallow, greedy };
struct Sample {
    Position position;
    bool firstSide;
    int empty;
};

int choose(Position p, Bits legal, int empty, Style style, bool randomMove, std::mt19937& rng) {
    if (randomMove) {
        std::uniform_int_distribution<int> index(0, count(legal) - 1);
        for (int n = index(rng); n > 0; --n) legal &= legal - 1;
        return first(legal);
    }
    int best = first(legal);
    if (style == greedy) {
        int most = -1;
        for (Bits rest = legal; rest; rest &= rest - 1) {
            int square = first(rest);
            int disks = count(play(p, bit(square)).them);
            if (disks > most) {
                best = square;
                most = disks;
            }
        }
    } else if (style == shallow) {
        search<opponentEstimate>(p, legal, std::min(3, empty), empty, -infinity, infinity, best);
    } else {
        int depth = style == learnedTwo ? 2 : 3;
        search(p, legal, std::min(depth, empty), empty, -infinity, infinity, best);
    }
    return best;
}

void printSample(int game, int margin, const Sample& sample) {
    auto [p, firstSide, empty] = sample;
    Bits legal = moves(p), replies = moves({p.them, p.us});
    std::cout << game << ',' << empty << ',' << (firstSide ? margin : -margin)
              << ',' << uint64_t(p.us) << ',' << uint64_t(p.us >> 64)
              << ',' << uint64_t(p.them) << ',' << uint64_t(p.them >> 64)
              << ',' << count(legal) - count(replies)
              << ',' << count(legal & anchors) - count(replies & anchors)
              << ',' << evaluate(p, legal, replies, empty) << '\n';
}
}

int main(int argc, char** argv) {
    if (argc != 2) return 1;
    int games = std::stoi(argv[1]);
    initBoard();
    deadline = Clock::time_point::max();
    std::mt19937 rng(371491);
    std::uniform_int_distribution<int> openingLength(4, 16), percent(0, 99);
    const Style opponents[] = {learnedTwo, learnedThree, shallow, greedy};
    for (int game = 0; game < games; ++game) {
        Style a = (game % 2) ? learnedTwo : learnedThree;
        Style b = opponents[(game / 2) % 4];
        if ((game / 8) % 2) std::swap(a, b);
        Position p{bit(54) | bit(71), bit(55) | bit(70)};
        bool firstSide = true;
        int empty = 84, opening = openingLength(rng);
        std::vector<Sample> samples;
        for (;;) {
            Bits legal = moves(p);
            if (!legal) {
                std::swap(p.us, p.them);
                firstSide = !firstSide;
                legal = moves(p);
                if (!legal) break;
            }
            if (empty >= 21 && empty <= 62 && empty % 3 == game % 3)
                samples.push_back({p, firstSide, empty});
            bool randomMove = 84 - empty < opening || (empty > 18 && percent(rng) < 4);
            p = play(p, bit(choose(p, legal, empty, firstSide ? a : b, randomMove, rng)));
            --empty;
            firstSide = !firstSide;
        }
        int margin = count(p.us) - count(p.them);
        for (const Sample& sample : samples) printSample(game, firstSide ? margin : -margin, sample);
    }
}
