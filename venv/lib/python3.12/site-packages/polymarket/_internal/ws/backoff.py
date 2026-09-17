import random

DEFAULT_BASE_DELAY_S = 0.250
DEFAULT_MAX_DELAY_S = 30.0


def jittered_backoff(
    attempt: int,
    *,
    base_s: float = DEFAULT_BASE_DELAY_S,
    max_s: float = DEFAULT_MAX_DELAY_S,
    rng: random.Random | None = None,
) -> float:
    if attempt < 0:
        raise ValueError("attempt must be non-negative")
    if base_s <= 0:
        raise ValueError("base_s must be positive")
    if max_s < base_s:
        raise ValueError("max_s must be >= base_s")
    # cap the exponebt so base_s * 2**attempt cannot overflow to inf for
    # large attempt counts before min(..., max_s) gets a chance to clamp.
    bounded_attempt = min(attempt, 64)
    cap = min(base_s * (2**bounded_attempt), max_s)
    draw = rng.random() if rng is not None else random.random()
    return draw * cap
