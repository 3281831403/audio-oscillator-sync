"""Core oscillator contracts for the audio-oscillator-sync exercise.

All phase values are normalized cycles in ``[0.0, 1.0)``.  Frequencies and
sample rates are in Hz and samples/second respectively.  Detuning is expressed
in cents.  Unless a function says otherwise, floating-point results are
compared with an absolute tolerance of ``1e-6``.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence


class OscError(Exception):
    """Raised when an oscillator parameter is invalid or inconsistent."""


_SHAPES = ("sine", "saw", "square", "triangle")


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _require_finite_positive(name: str, value: float) -> None:
    if not _is_number(value) or not math.isfinite(value) or value <= 0.0:
        raise OscError(f"{name} must be finite and greater than zero, got {value!r}")


def _require_finite(name: str, value: float) -> None:
    if not _is_number(value) or not math.isfinite(value):
        raise OscError(f"{name} must be finite, got {value!r}")


def phase_inc(freq: float, sample_rate: int) -> float:
    """Return the per-sample phase increment in normalized cycles.

    The result is ``freq / sample_rate`` reduced modulo ``1.0`` so phase
    arithmetic stays bounded for long renders and for frequencies at or above
    the sample rate.
    """
    _require_finite_positive("freq", freq)
    _require_finite_positive("sample_rate", sample_rate)
    return (freq / sample_rate) % 1.0


def waveform(phase: float, shape: str) -> float:
    """Evaluate a normalized oscillator waveform at ``phase``.

    ``phase`` is reduced modulo ``1.0`` before evaluation.  Unknown shapes
    raise :class:`OscError` instead of silently falling back to a sine.
    """
    _require_finite("phase", phase)
    if shape not in _SHAPES:
        raise OscError(f"unknown waveform shape: {shape!r}")
    t = phase % 1.0
    if shape == "sine":
        return math.sin(2.0 * math.pi * t)
    if shape == "saw":
        return 2.0 * t - 1.0
    if shape == "square":
        return 1.0 if t < 0.5 else -1.0
    # triangle: piecewise linear, -1 at 0, +1 at 0.5, -1 at 1
    return 1.0 - 4.0 * abs(t - 0.5)


def hard_sync(
    phase_a: float, phase_b: float, reset: bool
) -> tuple[float, float]:
    """Apply one hard-sync step to a master/slave oscillator pair.

    Both phases are wrapped into ``[0.0, 1.0)``.  When ``reset`` is true the
    slave phase is forced to exactly ``0.0`` so the sync seam is deterministic.
    """
    _require_finite("phase_a", phase_a)
    _require_finite("phase_b", phase_b)
    master = phase_a % 1.0
    slave = 0.0 if reset else phase_b % 1.0
    return master, slave


def detune(freq: float, cents: float) -> float:
    """Transpose ``freq`` by ``cents`` cents (1200 cents per octave)."""
    _require_finite_positive("freq", freq)
    _require_finite("cents", cents)
    return freq * 2.0 ** (cents / 1200.0)


def polyblep(t: float, dt: float) -> float:
    """Return the PolyBLEP correction at normalized phase ``t``.

    The correction is non-zero only within ``dt`` of the discontinuities at
    phase ``0``/``1`` and smoothly removes the hard edge of naive saw and
    square waves.
    """
    _require_finite("t", t)
    _require_finite("dt", dt)
    if not 0.0 <= t < 1.0:
        raise OscError(f"t must be in [0.0, 1.0), got {t!r}")
    if not 0.0 < dt < 0.5:
        raise OscError(f"dt must be in (0.0, 0.5), got {dt!r}")
    if t < dt:
        u = t / dt
        return u + u - u * u - 1.0
    if t > 1.0 - dt:
        u = (t - 1.0) / dt
        return u * u + 2.0 * u + 1.0
    return 0.0


def _sample_count(duration: float, sample_rate: float) -> int:
    """Half-up integer sample count, never less than one."""
    return max(1, math.floor(duration * sample_rate + 0.5))


def _render(shape: str, dt: float, phase0: float, count: int) -> list[float]:
    """Render ``count`` samples starting at ``phase0`` with increment ``dt``.

    Phase is recomputed from the sample index in double precision instead of
    being accumulated, so long low-frequency notes do not drift.  Saw and
    square are band-limited with PolyBLEP when the increment allows it.
    """
    band_limited = shape in ("saw", "square") and 0.0 < dt < 0.5
    samples: list[float] = []
    for i in range(count):
        t = (phase0 + i * dt) % 1.0
        if shape == "saw":
            value = 2.0 * t - 1.0
            if band_limited:
                value -= polyblep(t, dt)
        elif shape == "square":
            value = 1.0 if t < 0.5 else -1.0
            if band_limited:
                value += polyblep(t, dt)
                value -= polyblep((t + 0.5) % 1.0, dt)
        else:
            value = waveform(t, shape)
        samples.append(value)
    return samples


def render_note(
    freq: float, duration: float, sample_rate: int, shape: str
) -> list[float]:
    """Render one note as a list of floating-point samples.

    The length is the half-up integer sample count
    ``floor(duration * sample_rate + 0.5)`` and is never less than one.
    ``saw`` and ``square`` are band-limited with :func:`polyblep`.
    """
    _require_finite_positive("freq", freq)
    _require_finite_positive("duration", duration)
    _require_finite_positive("sample_rate", sample_rate)
    if shape not in _SHAPES:
        raise OscError(f"unknown waveform shape: {shape!r}")
    count = _sample_count(duration, sample_rate)
    dt = freq / sample_rate
    return _render(shape, dt, 0.0, count)


def validate_osc(config: Mapping[str, object]) -> list[str]:
    """Return a list of contract violations for an oscillator config.

    An empty list means the config is valid.
    """
    problems: list[str] = []

    if "freq" not in config:
        problems.append("missing required field: freq")
    else:
        freq = config["freq"]
        if not _is_number(freq) or not math.isfinite(freq) or freq <= 0.0:
            problems.append(f"freq must be finite and greater than zero, got {freq!r}")

    if "detune" in config:
        detune_value = config["detune"]
        if not _is_number(detune_value) or not math.isfinite(detune_value):
            problems.append(f"detune must be finite, got {detune_value!r}")

    if "phase" not in config:
        problems.append("missing required field: phase")
    else:
        phase = config["phase"]
        if not _is_number(phase) or not math.isfinite(phase) or not 0.0 <= phase < 1.0:
            problems.append(f"phase must be finite and in [0.0, 1.0), got {phase!r}")

    if "waveform" not in config:
        problems.append("missing required field: waveform")
    elif config["waveform"] not in _SHAPES:
        problems.append(f"waveform must be one of {_SHAPES}, got {config['waveform']!r}")

    return problems


def render_batch(
    notes: Sequence[Mapping[str, object]], sample_rate: int
) -> dict[int, list[float]]:
    """Render a sequence of oscillator configs, one cycle per note.

    All notes are validated before anything is rendered (all-or-nothing), and
    each note is rendered from its own independent phase state.
    """
    _require_finite_positive("sample_rate", sample_rate)

    errors: list[str] = []
    for index, config in enumerate(notes):
        for problem in validate_osc(config):
            errors.append(f"note {index}: {problem}")
    if errors:
        raise OscError("invalid oscillator config(s): " + "; ".join(errors))

    rendered: dict[int, list[float]] = {}
    for index, config in enumerate(notes):
        freq = float(config["freq"])  # type: ignore[arg-type]
        cents = float(config.get("detune", 0.0))  # type: ignore[arg-type]
        phase0 = float(config["phase"])  # type: ignore[arg-type]
        shape = config["waveform"]
        effective = detune(freq, cents)
        count = _sample_count(sample_rate / effective, 1.0)
        rendered[index] = _render(shape, effective / sample_rate, phase0, count)
    return rendered
