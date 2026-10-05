"""Layout helpers: paragraphs, line metrics, greedy word planner."""
from typing import Callable, List, Tuple


def split_paragraphs(text: str) -> List[str]:
    return (text or "").split("\n")


def line_height_for(size_px: int, factor: float = 1.9) -> int:
    return int(size_px * factor)


def plan_line(words: List[Tuple[str, int]], max_width: int,
              space_w: int) -> Tuple[list, list]:
    """Greedy: take leading words that fit. Returns (taken, rest)."""
    taken, w = [], 0
    for i, (word, ww) in enumerate(words):
        add = ww if not taken else space_w + ww
        if taken and w + add > max_width:
            return taken, words[i:]
        taken.append((word, ww))
        w += add
    return taken, []


def wrap_words(words: List[Tuple[str, int]], max_width: int,
               space_w: int) -> List[list]:
    lines = []
    rest = list(words)
    while rest:
        taken, rest = plan_line(rest, max_width, space_w)
        if not taken:  # single word wider than page: force it alone
            taken, rest = [rest[0]], rest[1:]
        lines.append(taken)
    return lines
