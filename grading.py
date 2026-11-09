"""Explicit, configurable grading rules; no school-specific rules are assumed."""
from dataclasses import asdict, dataclass
from decimal import Decimal, ROUND_HALF_UP
import math
import unicodedata

CATEGORIES = ('Giỏi', 'Khá', 'Trung bình', 'Trung bình yếu', 'Kém', 'Chưa đủ điểm')
COLORS = ('#42bf35', '#b3f658', '#ffe35e', '#ff9c9f', '#ef7176', '#bbc3cc')


def rounded(value, digits):
    return float(Decimal(str(value)).quantize(Decimal(1).scaleb(-digits), rounding=ROUND_HALF_UP))


def search_key(text):
    text = str(text).casefold().replace('đ', 'd')
    return ''.join(c for c in unicodedata.normalize('NFD', text) if not unicodedata.combining(c))


@dataclass(frozen=True)
class GradePolicy:
    regular_weight: float = 1
    midterm_weight: float = 2
    final_weight: float = 3
    course_digits: int = 1
    average_digits: int = 1
    excellent: float = 8.5
    good: float = 7
    fair: float = 5.5
    average: float = 4
    credit_weighted: bool = False

    def __post_init__(self):
        weights = (self.regular_weight, self.midterm_weight, self.final_weight)
        if not all(math.isfinite(w) and w >= 0 for w in weights) or sum(weights) <= 0:
            raise ValueError('Hệ số điểm phải không âm và có tổng lớn hơn 0.')
        bounds = (self.excellent, self.good, self.fair, self.average)
        if not all(math.isfinite(v) and 0 <= v <= 10 for v in bounds) or not all(a > b for a, b in zip(bounds, bounds[1:])):
            raise ValueError('Ngưỡng xếp loại phải giảm dần, nằm trong khoảng 0–10.')
        if self.course_digits not in (0, 1, 2) or self.average_digits not in (0, 1, 2):
            raise ValueError('Số chữ số làm tròn phải từ 0 đến 2.')

    def course_score(self, regular, midterm, final):
        values = (regular, midterm, final)
        if any(v is None for v in values):
            return None
        if not all(math.isfinite(v) and 0 <= v <= 10 for v in values):
            raise ValueError('Điểm phải từ 0 đến 10.')
        weights = (self.regular_weight, self.midterm_weight, self.final_weight)
        value = sum(Decimal(str(v)) * Decimal(str(w)) for v, w in zip(values, weights)) / sum(Decimal(str(w)) for w in weights)
        return rounded(value, self.course_digits)

    def semester_score(self, scores_and_credits):
        if not scores_and_credits or any(score is None for score, _ in scores_and_credits):
            return None
        weights = [credits if self.credit_weighted else 1 for _, credits in scores_and_credits]
        denominator = sum(weights)
        if denominator <= 0:
            return None
        numerator = sum(Decimal(str(score)) * Decimal(str(weight)) for (score, _), weight in zip(scores_and_credits, weights))
        return rounded(numerator / Decimal(str(denominator)), self.average_digits)

    def classify(self, value):
        if value is None:
            return 'Chưa đủ điểm'
        for label, threshold in zip(CATEGORIES, (self.excellent, self.good, self.fair, self.average)):
            if value >= threshold:
                return label
        return 'Kém'

    def to_dict(self):
        return asdict(self)
