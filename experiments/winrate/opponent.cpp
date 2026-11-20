// Local sparring partners. Reuse the board geometry and the three-ply reply
// model from the frozen player so all three executables read the same format.
#define main frozenPlayerMain
#include "baseline.cpp"
#undef main

int main() {
    initBoard();
    Position p{};
    for (Bits cells = board; cells; cells &= cells - 1) {
        int value;
        if (!(std::cin >> value) || value < 0 || value > 2) return 1;
        Bits square = bit(first(cells));
        if (value == 1) p.us |= square;
        if (value == 2) p.them |= square;
    }
    Bits legal = moves(p);
    if (!legal) {
        std::cout << "0 0\n";
        return 0;
    }
    int best = first(legal);
#ifdef GREEDY
    int most = -1;
    for (Bits rest = legal; rest; rest &= rest - 1) {
        int square = first(rest);
        int disks = count(play(p, bit(square)).them);
        if (disks > most) {
            best = square;
            most = disks;
        }
    }
#else
    deadline = Clock::time_point::max();
    int empty = 88 - count(p.us | p.them);
    search<opponentEstimate>(p, legal, std::min(3, empty), empty, -infinity, infinity, best);
#endif
    int row = best / 16;
    std::cout << row + 1 << ' ' << best % 16 - (14 - rows[row]) / 2 + 1 << '\n';
    return 0;
}
