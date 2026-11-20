// Report each legal move's independent score at several shallow depths.
#define main frozenPlayerMain
#include "baseline.cpp"
#undef main

int main() {
    initBoard();
    Position p{};
    for (Bits cells = board; cells; cells &= cells - 1) {
        int value;
        if (!(std::cin >> value)) return 1;
        if (value == 1) p.us |= bit(first(cells));
        if (value == 2) p.them |= bit(first(cells));
    }
    deadline = Clock::time_point::max();
    int empty = 88 - count(p.us | p.them);
    for (Bits rest = moves(p); rest; rest &= rest - 1) {
        int square = first(rest), unused;
        auto child = rankedMove(p, square, -1);
        std::cout << square / 16 + 1 << ' ' << square % 16 - (14 - rows[square / 16]) / 2 + 1;
        for (int d : {3, 5, 7, 9, 11}) {
            int value = -search(child.child, child.replies, std::min(empty, d) - 1,
                                empty - 1, -infinity, infinity, unused);
            std::cout << ' ' << value;
        }
        std::cout << '\n';
    }
}
