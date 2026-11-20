"""Core oscillator contracts for the audio-oscillator-sync exercise.

All phase values are normalized cycles in ``[0.0, 1.0)``.  Frequencies and
sample rates are in Hz and samples/second respectively.  Detuning is expressed
in cents.  Unless a function says otherwise, floating-point results are
compared with an absolute tolerance of ``1e-6``.

Every public function in this module is currently a stub: the repository starts
with fifteen failing acceptance tests, and the implementation belongs here.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence


class OscError(Exception):
    """Raised when an oscillator parameter is invalid or inconsistent."""


def phase_inc(freq: float, sample_rate: int) -> float:
    """Return the per-sample phase increment in normalized cycles.

    Parameters
    ----------
    freq:
        Oscillator frequency in Hz.  It must be finite and greater than zero.
    sample_rate:
        Sampling rate in samples per second.  It must be finite and greater
        than zero.

    Returns
    -------
    float
        ``freq / sample_rate`` reduced modulo ``1.0``, so the result is always
        in ``[0.0, 1.0)``.  The modulo keeps phase arithmetic bounded even for
        long renders and for frequencies at or above the sample rate.

    Raises
    ------
    OscError
        If ``freq`` or ``sample_rate`` is non-positive or non-finite.

    Accuracy target: absolute tolerance ``1e-6``.
    """
    raise NotImplementedError


def waveform(phase: float, shape: str) -> float:
    """Evaluate a normalized oscillator waveform at ``phase``.

    Parameters
    ----------
    phase:
        Phase in normalized cycles.  Any finite real value is accepted and
        reduced modulo ``1.0`` before evaluation.
    shape:
        One of ``"sine"``, ``"saw"``, ``"square"`` or ``"triangle"``.  The
        definitions are:

        * ``sine``: ``sin(2 * pi * phase)``
        * ``saw``: ``2 * phase - 1``
        * ``square``: ``+1`` for ``phase < 0.5`` and ``-1`` otherwise
        * ``triangle``: ``1 - 4 * abs(phase - 0.5)``

    Returns
    -------
    float
        A value in ``[-1.0, 1.0]`` for the normalized phase.

    Raises
    ------
    OscError
        If ``phase`` is non-finite or ``shape`` is not one of the four known
        waveform names.  An unknown waveform must never silently fall back to
        a sine.

    Accuracy target: absolute tolerance ``1e-6``.
    """
    raise NotImplementedError


def hard_sync(
    phase_a: float, phase_b: float, reset: bool
) -> tuple[float, float]:
    """Apply one hard-sync step to a master/slave oscillator pair.

    Parameters
    ----------
    phase_a:
        Master phase in normalized cycles.
    phase_b:
        Slave phase in normalized cycles.
    reset:
        ``True`` when the master wraps during this step.  A hard reset forces
        the slave phase to exactly ``0.0``; ``False`` leaves the slave phase
        untouched.

    Returns
    -------
    tuple[float, float]
        ``(master_phase, slave_phase)`` with both phases wrapped into
        ``[0.0, 1.0)``.  When ``reset`` is true the returned slave phase is
        exactly ``0.0``, which makes the sync seam deterministic instead of
        leaking the previous cycle's phase.

    Raises
    ------
    OscError
        If either input phase is non-finite.

    Accuracy target: absolute tolerance ``1e-6``.
    """
    raise NotImplementedError


def detune(freq: float, cents: float) -> float:
    """Transpose ``freq`` by ``cents`` cents.

    One octave is 1200 cents, so the result is::

        freq * 2 ** (cents / 1200)

    A value of ``0`` cents therefore returns the original frequency, and
    ``+1200`` / ``-1200`` cents double / halve it.

    Parameters
    ----------
    freq:
        Base frequency in Hz.  It must be finite and greater than zero.
    cents:
        Detune amount in cents.  It may be negative and must be finite.

    Returns
    -------
    float
        The detuned frequency in Hz.

    Raises
    ------
    OscError
        If ``freq`` is non-positive or non-finite, or ``cents`` is non-finite.

    Accuracy target: absolute tolerance ``1e-6``.
    """
    raise NotImplementedError


def polyblep(t: float, dt: float) -> float:
    """Return the PolyBLEP correction at normalized phase ``t``.

    ``polyblep`` removes most of the aliasing created by the hard edges of
    naive saw and square waves.  It is added to (or subtracted from) the raw
    waveform around a discontinuity and is zero away from both endpoints.

    Parameters
    ----------
    t:
        Normalized phase in ``[0.0, 1.0)``.
    dt:
        Per-sample phase increment in ``(0.0, 0.5)``, i.e. the oscillator
        frequency divided by the sample rate.

    Returns
    -------
    float
        The correction value.  For ``t < dt`` it is
        ``u + u - u * u - 1`` with ``u = t / dt``.  For ``t > 1 - dt`` it is
        ``u * u + 2 * u + 1`` with ``u = (t - 1) / dt``.  Otherwise it is
        ``0.0``.  Consequently the correction is ``-1.0`` at ``t = 0`` and
        tends to ``0.0`` at both ends of the transition, keeping the corrected
        waveform continuous.

    Raises
    ------
    OscError
        If ``t`` or ``dt`` is non-finite, if ``t`` is outside ``[0.0, 1.0)``,
        or if ``dt`` is outside ``(0.0, 0.5)``.

    Accuracy target: absolute tolerance ``1e-6``.
    """
    raise NotImplementedError


def render_note(
    freq: float, duration: float, sample_rate: int, shape: str
) -> list[float]:
    """Render one note as a list of floating-point samples.

    Parameters
    ----------
    freq:
        Oscillator frequency in Hz.  It must be finite and greater than zero.
    duration:
        Note length in seconds.  It must be finite and greater than zero.
    sample_rate:
        Sampling rate in samples per second.  It must be finite and greater
        than zero.
    shape:
        Waveform name accepted by :func:`waveform`.

    Returns
    -------
    list[float]
        Samples evaluated at integer sample positions starting from phase
        ``0.0``.  The length is the half-up integer sample count
        ``floor(duration * sample_rate + 0.5)``, and is never less than one.
        The result may differ from the ideal duration by at most one sample.

        ``sine`` and ``triangle`` use :func:`waveform` directly.  ``saw`` and
        ``square`` are band-limited with :func:`polyblep`; in particular, the
        first sample of a square wave starts at ``0.0`` on the discontinuity
        rather than at the raw ``+1.0`` edge.

    Raises
    ------
    OscError
        If any argument is invalid, if ``sample_rate`` is zero (never divide
        by zero), or if ``shape`` is unknown.

    Accuracy target: absolute tolerance ``1e-6``.
    """
    raise NotImplementedError


def validate_osc(config: Mapping[str, object]) -> list[str]:
    """Return a list of contract violations for an oscillator config.

    A config uses exactly these fields::

        {"freq": float, "detune": float, "phase": float, "waveform": str}

    The checks are:

    * ``freq`` must be finite and greater than zero.
    * ``phase`` must be finite and in ``[0.0, 1.0)``.
    * ``waveform`` must be one of ``sine``, ``saw``, ``square`` or
      ``triangle``.
    * required fields must be present and ``detune``, when present, must be
      finite.

    Parameters
    ----------
    config:
        Mapping with the oscillator fields above.

    Returns
    -------
    list[str]
        Human-readable problem descriptions in a deterministic order.  An
        empty list means the config is valid.

    Accuracy target: no floating-point arithmetic beyond finite-value checks.
    """
    raise NotImplementedError


def render_batch(
    notes: Sequence[Mapping[str, object]], sample_rate: int
) -> dict[int, list[float]]:
    """Render a sequence of oscillator configs, one cycle per note.

    Each note uses the four fields accepted by :func:`validate_osc`.  Its
    effective frequency is ``detune(freq, cents)`` and its first sample starts
    at the configured ``phase``.  The note is rendered for exactly one cycle
    of that effective frequency, so its ideal length is
    ``sample_rate / effective_freq`` samples (with at most one sample of
    integer-rounding error).

    Parameters
    ----------
    notes:
        Ordered sequence of oscillator configs.  The configs must not be
        mutated.
    sample_rate:
        Sampling rate in samples per second.  It must be finite and greater
        than zero.

    Returns
    -------
    dict[int, list[float]]
        A mapping from zero-based note index to its rendered samples.  Keys
        preserve the input order.  Notes must have independent phase state:
        no phase or sample buffer from one note may leak into the next.

    Raises
    ------
    OscError
        If ``sample_rate`` is invalid or any note config is invalid.  All
        notes are validated before rendering, so a failed batch returns
        nothing and leaves no partial or shared state behind (all-or-nothing
        rollback).

    Accuracy target: absolute tolerance ``1e-6``.
    """
    raise NotImplementedError
