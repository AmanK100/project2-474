// Test-only access to the production move generator and search. Build this separately.
#define main projectPlayerMain
#include "../../reversi.cpp"
#undef main
#include <string_view>

int main(int argc, char** argv) {
    const auto start = Clock::now();
    const bool trace = argc == 2 && std::string_view(argv[1]) == "--depth";
    initBoard();
    while (std::cin >> std::ws && std::cin.peek() != EOF) {
        Position p{};
        for (Bits cells = board; cells; cells &= cells - 1) {
            int disk;
            if (!(std::cin >> disk) || disk < 0 || disk > 2) return 1;
            Bits square = bit(first(cells));
            if (disk == 1) p.us |= square;
            if (disk == 2) p.them |= square;
        }
        Bits legal = moves(p);
        if (trace) {
            deadline = start + timeBudget;
            int empty = cellCount - count(p.us | p.them);
            try {
                for (int depth = 1; depth <= empty; ++depth) {
                    int best = -1;
                    int value = minimax(p, legal, depth, -infinity, infinity, best);
                    auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(Clock::now() - start);
                    std::cout << depth << ' ' << best << ' ' << value << ' ' << nodes << ' ' << ms.count() << '\n';
                }
            } catch (const Timeout&) {}
            return 0;
        }
        for (Bits rest = legal; rest; rest &= rest - 1) {
            int square = first(rest);
            Position child = play(p, bit(square));
            std::cout << square << ' ' << uint64_t(child.us) << ' ' << uint64_t(child.us >> 64)
                      << ' ' << uint64_t(child.them) << ' ' << uint64_t(child.them >> 64) << ' ';
        }
        std::cout << '\n';
    }
}
