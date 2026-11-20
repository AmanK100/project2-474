// Test-only access to a fixed-depth search. The project executable still takes one board.
#define main projectPlayerMain
#include "../reversi.cpp"
#undef main

int main() {
    initBoard();
    deadline = Clock::time_point::max();
    int depth;
    while (std::cin >> depth) {
        Position position{};
        for (Bits cells = board; cells; cells &= cells - 1) {
            int disk;
            if (!(std::cin >> disk) || disk < 0 || disk > 2) return 1;
            if (disk == 1) position.us |= bit(first(cells));
            if (disk == 2) position.them |= bit(first(cells));
        }
        int square = -1;
        int score = minimax(position, moves(position), depth, -infinity, infinity, square);
        std::cout << score << ' ' << square << '\n';
    }
}
