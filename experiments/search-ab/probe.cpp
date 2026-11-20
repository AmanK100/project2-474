// Test driver. Compile with -DPLAYER='"control.cpp"', '"pvs.cpp"' or '"mobility.cpp"'.
#define main playerMain
#include PLAYER
#undef main
#include <string_view>

int main(int argc, char** argv) {
    auto start = Clock::now();
    bool timed = argc == 2 && std::string_view(argv[1]) == "--timed";
    initBoard();
    deadline = timed ? start + timeBudget : Clock::time_point::max();
    int depth;
    while (std::cin >> depth) {
        Position p{};
        for (Bits cells = board; cells; cells &= cells - 1) {
            int disk;
            if (!(std::cin >> disk) || disk < 0 || disk > 2) return 1;
            if (disk == 1) p.us |= bit(first(cells));
            if (disk == 2) p.them |= bit(first(cells));
        }
        int best = -1;
        nodes = 0;
        try {
            for (int d = timed ? 1 : depth; d <= depth; ++d) {
                int value = minimax(p, moves(p), d, -infinity, infinity, best);
                std::cout << value << ' ' << best << ' ' << d << ' ' << nodes << '\n';
            }
        } catch (const Timeout&) {}
        if (timed) break;
    }
}
