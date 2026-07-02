"""FSRS-5 spaced-repetition scheduler + gradient-descent trainer.

Two pieces, both pure (no DB):
  1. the forward scheduler  -> given a card's (difficulty, stability) and your
     rating, returns the next (difficulty, stability, interval-in-days).
  2. optimize()             -> fits the 19 weights to YOUR review history by
     minimising recall log-loss (L-BFGS-B). Needs review logs; until you have
     them, the scheduler runs on DEFAULT_W just fine.

Model: DSR (Difficulty, Stability, Retrievability).
  Retrievability R(t) = (1 + FACTOR * t / S) ** DECAY   -> the forgetting curve.
  Schedule the next review at the day R falls to your target retention.

Rating: 1=Again(forgot) 2=Hard 3=Good 4=Easy.
"""

import math

# FSRS-5 published defaults (19 weights). Good enough until you train your own.
DEFAULT_W = [
    0.40255,
    1.18385,
    3.173,
    15.69105,
    7.1949,
    0.5345,
    1.4604,
    0.0046,
    1.54575,
    0.1192,
    1.01925,
    1.9395,
    0.11,
    0.29605,
    2.2698,
    0.2315,
    2.9898,
    0.51655,
    0.6621,
]

DECAY = -0.5
FACTOR = 0.9 ** (1 / DECAY) - 1  # so that R = 0.9 exactly when t == S
S_MIN, S_MAX = 0.01, 36500.0  # stability floor / 100-year ceiling

# scipy bounds per weight (FSRS-5). Keeps the fit numerically sane.
W_BOUNDS = [(0.001, 100)] * 4 + [
    (1, 10),
    (0.001, 4),
    (0.001, 4),
    (0.001, 0.75),
    (0, 4.5),
    (0, 0.8),
    (0.001, 3.5),
    (0.001, 5),
    (0.001, 0.25),
    (0.001, 0.9),
    (0, 4),
    (0, 1),
    (1, 6),
    (0, 2),
    (0, 2),
]


def _clamp(x, lo, hi):
    return max(lo, min(hi, x))


def retrievability(elapsed_days, stability):
    """Probability of recall after `elapsed_days` given memory `stability`."""
    return (1 + FACTOR * elapsed_days / stability) ** DECAY


def next_interval(stability, request_retention=0.9):
    """Days until R drops to request_retention. next_interval(S,0.9) ~= S."""
    ivl = stability / FACTOR * (request_retention ** (1 / DECAY) - 1)
    return int(max(1, round(ivl)))


def init_stability(w, rating):
    return _clamp(w[rating - 1], S_MIN, S_MAX)


def init_difficulty(w, rating):
    return _clamp(w[4] - math.exp(w[5] * (rating - 1)) + 1, 1, 10)


def next_difficulty(w, d, rating):
    delta = -w[6] * (rating - 3)
    d_new = d + delta * (10 - d) / 9  # linear damping
    return _clamp(
        w[7] * init_difficulty(w, 4) + (1 - w[7]) * d_new, 1, 10
    )  # mean reversion


def _stability_recall(w, d, s, r, rating):
    hard = w[15] if rating == 2 else 1.0
    easy = w[16] if rating == 4 else 1.0
    return s * (
        1
        + math.exp(w[8])
        * (11 - d)
        * (s ** -w[9])
        * (math.exp(w[10] * (1 - r)) - 1)
        * hard
        * easy
    )


def _stability_forget(w, d, s, r):
    new_s = w[11] * (d ** -w[12]) * (((s + 1) ** w[13]) - 1) * math.exp(w[14] * (1 - r))
    return min(new_s, s)  # a lapse never raises stability


def review(card, rating, elapsed_days, w=None, request_retention=0.9):
    """Advance one card by one review.

    card: dict-like with 'difficulty','stability','state' (state 0 or falsy = new).
    Returns dict: difficulty, stability, state, interval (days).
    state: 2=Review, 3=Relearning (0/1 collapse into first-review init).
    """
    w = w or DEFAULT_W
    s0, d0 = card.get("stability"), card.get("difficulty")
    if not s0 or not card.get("state"):  # first ever review
        s = init_stability(w, rating)
        d = init_difficulty(w, rating)
        state = 2
    else:
        r = retrievability(elapsed_days, s0)
        if rating == 1:
            s = _stability_forget(w, d0, s0, r)
            state = 3
        else:
            s = _stability_recall(w, d0, s0, r, rating)
            state = 2
        d = next_difficulty(w, d0, rating)
    s = _clamp(s, S_MIN, S_MAX)
    return {
        "difficulty": d,
        "stability": s,
        "state": state,
        "interval": next_interval(s, request_retention),
    }


# ponytail: same-day "short-term" learning steps (w17,w18) skipped — a daily
# vocab app rarely re-reviews within a day. Add if you introduce learning steps.


# ---------------------------------------------------------------------------
# Trainer: fit weights to review history by gradient descent (L-BFGS-B).
# A "sequence" is one card's reviews in order: [(rating, elapsed_days), ...].
# The first review only seeds S0/D0 (no prediction); every later review
# predicts R from the prior state and is scored against the actual outcome.
# ---------------------------------------------------------------------------
def replay_loss(w, sequences):
    """Mean binary cross-entropy of predicted recall vs actual outcome."""
    total, n = 0.0, 0
    for seq in sequences:
        d = s = None
        for rating, elapsed in seq:
            if s is None:
                s, d = init_stability(w, rating), init_difficulty(w, rating)
                continue
            r = _clamp(retrievability(elapsed, s), 1e-6, 1 - 1e-6)
            y = 1.0 if rating != 1 else 0.0
            total += -(y * math.log(r) + (1 - y) * math.log(1 - r))
            n += 1
            if rating == 1:
                s = _clamp(_stability_forget(w, d, s, r), S_MIN, S_MAX)
            else:
                s = _clamp(_stability_recall(w, d, s, r, rating), S_MIN, S_MAX)
            d = next_difficulty(w, d, rating)
    return total / max(n, 1)


def optimize(sequences, init=None):
    """Return (fitted_weights list, final_loss). Needs real review sequences."""
    import numpy as np
    from scipy.optimize import minimize

    x0 = np.array(init or DEFAULT_W, dtype=float)
    res = minimize(
        replay_loss, x0, args=(sequences,), method="L-BFGS-B", bounds=W_BOUNDS
    )
    return res.x.tolist(), float(res.fun)
    # ponytail: scipy numerical gradient over 19 params. Fine to ~10k reviews;
    # swap in torch autograd if training gets slow past that.


def simulate_history(n_cards, max_reviews, w=DEFAULT_W, seed=0):
    """Generate synthetic review sequences from a known model (for testing/demo).

    Simulates a learner who rates Good when they recall, Again when they don't,
    with recall sampled ~ Bernoulli(R). Returns list of sequences.
    """
    import random

    rng = random.Random(seed)
    seqs = []
    for _ in range(n_cards):
        seq = [(3, 0)]  # first review: Good
        s = init_stability(w, 3)
        d = init_difficulty(w, 3)
        for _ in range(max_reviews - 1):
            elapsed = max(1, int(next_interval(s) * rng.uniform(0.7, 1.3)))
            r = retrievability(elapsed, s)
            recalled = rng.random() < r
            rating = 3 if recalled else 1
            seq.append((rating, elapsed))
            if recalled:
                s = _clamp(
                    _stability_recall(w, d, s, retrievability(elapsed, s), rating),
                    S_MIN,
                    S_MAX,
                )
            else:
                s = _clamp(
                    _stability_forget(w, d, s, retrievability(elapsed, s)), S_MIN, S_MAX
                )
            d = next_difficulty(w, d, rating)
        seqs.append(seq)
    return seqs


def _demo():
    # --- scheduler sanity ---
    assert abs(retrievability(0, 5) - 1.0) < 1e-9
    assert abs(retrievability(5, 5) - 0.9) < 1e-6  # R == 0.9 at t == S
    assert retrievability(20, 5) < retrievability(5, 5)  # decays with time
    assert next_interval(50) > next_interval(5)  # more stable -> later
    assert init_difficulty(DEFAULT_W, 1) > init_difficulty(
        DEFAULT_W, 4
    )  # Again harder than Easy

    new = review({}, 3, 0)  # brand-new card, Good
    assert new["state"] == 2 and new["interval"] >= 1
    again = review({"difficulty": 5, "stability": 20, "state": 2}, 1, 20)
    good = review({"difficulty": 5, "stability": 20, "state": 2}, 3, 20)
    assert again["stability"] < good["stability"]  # forgetting shortens memory
    assert again["interval"] < good["interval"]

    # --- trainer actually reduces loss via gradient descent ---
    truth = list(DEFAULT_W)
    seqs = simulate_history(120, 8, w=truth, seed=1)
    wrong = [x * 1.6 for x in truth]  # start from bad weights
    fitted, loss = optimize(seqs, init=wrong)
    assert loss < replay_loss(wrong, seqs)  # descent helped
    assert loss <= replay_loss(truth, seqs) + 0.02  # ~recovered the true fit
    print(
        f"OK  scheduler + trainer.  wrong_loss={replay_loss(wrong, seqs):.4f}"
        f"  fitted_loss={loss:.4f}  truth_loss={replay_loss(truth, seqs):.4f}"
    )


if __name__ == "__main__":
    _demo()
