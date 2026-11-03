from backend.stages.stage6_score import step_score, parity_from_steps


def test_step_score_068():
    assert abs(step_score(1, 0, 1, 0.8) - 0.68) < 1e-9


def test_step_score_weights():
    assert step_score(1, 1, 1, 1) == 1.0
    assert step_score(0, 0, 0, 0) == 0.0
    assert step_score(1, 1, 1, 0.8) == 0.98


def test_parity_formula_and_pass():
    steps = [
        {"weight": 2, "s": 1.0},
        {"weight": 1, "s": 0.5},
    ]
    p, ok = parity_from_steps(steps)
    assert p == round(100 * (2 * 1.0 + 1 * 0.5) / 3, 2)
    assert ok is False  # 83.33 < 90
    steps2 = [{"weight": 1, "s": 1.0}, {"weight": 1, "s": 1.0}]
    p2, ok2 = parity_from_steps(steps2)
    assert p2 == 100.0 and ok2 is True


def test_w2_below_05_fails():
    steps = [{"weight": 2, "s": 0.49}, {"weight": 1, "s": 1.0},
             {"weight": 1, "s": 1.0}, {"weight": 1, "s": 1.0}]
    p, ok = parity_from_steps(steps)
    assert p >= 0
    assert ok is False