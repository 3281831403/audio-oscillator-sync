"""Acceptance tests for the audio oscillator exercise.

There are exactly fifteen tests.  Each one exercises the public stubs in
``osc/oscillator.py`` and is expected to fail until the implementation is
completed.  The tests use only the standard library and pytest; they are
deterministic and perform no I/O, sleeping or network access.
"""

import math

import pytest

from osc.oscillator import (
    OscError,
    detune,
    hard_sync,
    phase_inc,
    polyblep,
    render_batch,
    render_note,
    validate_osc,
    waveform,
)


def test_phase_increment_is_wrapped_modulo_one():
    """The per-sample increment is normalized instead of growing forever."""
    assert phase_inc(440.0, 44100) == pytest.approx(440.0 / 44100.0, abs=1e-6)
    assert phase_inc(2500.0, 1000) == pytest.approx(0.5, abs=1e-6)


def test_square_wave_uses_polyblep_at_discontinuity():
    """A square note is band-limited at its phase-zero edge."""
    dt = 1000.0 / 48000.0
    assert polyblep(0.0, dt) == pytest.approx(-1.0, abs=1e-6)
    assert polyblep(0.5, dt) == pytest.approx(0.0, abs=1e-6)

    note = render_note(1000.0, 1.0 / 1000.0, 48000, "square")
    assert note[0] == pytest.approx(0.0, abs=1e-6)


def test_hard_sync_resets_slave_phase_cleanly():
    """Resetting the master forces the slave to zero without stale phase."""
    master, slave = hard_sync(0.25, 0.8, False)
    assert master == pytest.approx(0.25, abs=1e-6)
    assert slave == pytest.approx(0.8, abs=1e-6)

    master, slave = hard_sync(1.0, 0.8, True)
    assert master == pytest.approx(0.0, abs=1e-6)
    assert slave == pytest.approx(0.0, abs=1e-6)

    master, slave = hard_sync(-0.25, 1.25, False)
    assert master == pytest.approx(0.75, abs=1e-6)
    assert slave == pytest.approx(0.25, abs=1e-6)


def test_detune_uses_1200_cents_per_octave():
    """One hundred cents is a semitone, not a full octave."""
    assert detune(440.0, 100.0) == pytest.approx(
        440.0 * 2.0 ** (100.0 / 1200.0), abs=1e-6
    )
    assert detune(440.0, 1200.0) == pytest.approx(880.0, abs=1e-6)
    assert detune(440.0, -1200.0) == pytest.approx(220.0, abs=1e-6)


def test_low_frequency_long_note_does_not_drift():
    """A long low note still matches the ideal phase at its final samples."""
    sample_rate = 8000
    freq = 20.0
    duration = 60.0
    note = render_note(freq, duration, sample_rate, "sine")
    expected_length = math.floor(duration * sample_rate + 0.5)
    assert len(note) == expected_length

    for index in (0, 1, 12345, expected_length - 1):
        expected = math.sin(2.0 * math.pi * freq * index / sample_rate)
        assert note[index] == pytest.approx(expected, abs=1e-6)


def test_triangle_wave_is_piecewise_linear():
    """The triangle is linear between its extrema, not a rectified sine."""
    expected_values = {
        0.0: -1.0,
        0.125: -0.5,
        0.25: 0.0,
        0.375: 0.5,
        0.5: 1.0,
        0.625: 0.5,
        0.75: 0.0,
        0.875: -0.5,
    }
    for phase, expected in expected_values.items():
        assert waveform(phase, "triangle") == pytest.approx(expected, abs=1e-6)


def test_unknown_waveform_raises_instead_of_defaulting_to_sine():
    """Validation and evaluation both reject an unknown shape."""
    valid = {
        "freq": 440.0,
        "detune": 0.0,
        "phase": 0.25,
        "waveform": "sine",
    }
    assert validate_osc(valid) == []

    invalid = dict(valid, waveform="noise")
    assert validate_osc(invalid)

    with pytest.raises(OscError):
        waveform(0.25, "noise")

    with pytest.raises(OscError):
        render_note(440.0, 0.01, 44100, "noise")


def test_render_note_uses_integer_sample_count():
    """Note lengths follow the half-up integer sample count."""
    assert len(render_note(440.0, 0.01, 44100, "sine")) == 441
    assert len(render_note(100.0, 0.333, 1000, "sine")) == 333
    assert len(render_note(1.0, 0.1, 5, "sine")) == 1


def test_batch_notes_are_phase_independent_and_roll_back():
    """Each note starts from its own phase and a bad batch leaks no state."""
    notes = [
        {"freq": 100.0, "detune": 0.0, "phase": 0.0, "waveform": "sine"},
        {"freq": 100.0, "detune": 0.0, "phase": 0.25, "waveform": "sine"},
        {"freq": 200.0, "detune": 0.0, "phase": 0.5, "waveform": "sine"},
    ]
    batch = render_batch(notes, 1000)
    assert list(batch) == [0, 1, 2]
    assert [len(batch[index]) for index in range(3)] == [10, 10, 5]
    assert batch[0][0] == pytest.approx(0.0, abs=1e-6)
    assert batch[1][0] == pytest.approx(1.0, abs=1e-6)
    assert batch[2][0] == pytest.approx(0.0, abs=1e-6)

    before = {index: list(samples) for index, samples in batch.items()}
    bad_note = {"freq": -5.0, "detune": 0.0, "phase": 0.0, "waveform": "sine"}
    with pytest.raises(OscError):
        render_batch([notes[0], bad_note, notes[2]], 1000)

    after = render_batch(notes, 1000)
    assert after == before


def test_render_note_rejects_zero_sample_rate():
    """A zero sample rate raises OscError instead of dividing by zero."""
    with pytest.raises(OscError):
        render_note(440.0, 0.1, 0, "sine")


def test_combo_sine_at_zero_phase_is_zero():
    """The sine starts at zero at phase zero and after a full wrap."""
    assert waveform(0.0, "sine") == pytest.approx(0.0, abs=1e-6)
    assert waveform(1.0, "sine") == pytest.approx(0.0, abs=1e-6)


def test_combo_zero_cents_preserves_frequency():
    """Zero detune is the identity transform."""
    assert detune(440.0, 0.0) == pytest.approx(440.0, abs=1e-6)
    assert detune(1234.5, 0.0) == pytest.approx(1234.5, abs=1e-6)


def test_combo_zero_sample_rate_raises_osc_error():
    """phase_inc validates the sample rate before doing any division."""
    with pytest.raises(OscError):
        phase_inc(440.0, 0)


def test_combo_single_cycle_length_matches_period():
    """One cycle at 1 kHz and 48 kHz contains exactly 48 samples."""
    note = render_note(1000.0, 1.0 / 1000.0, 48000, "sine")
    assert len(note) == 48
    assert note[0] == pytest.approx(0.0, abs=1e-6)
    assert note[12] == pytest.approx(1.0, abs=1e-6)


def test_combo_batch_preserves_note_order():
    """Successful batches key samples by input position and apply detune."""
    notes = [
        {"freq": 100.0, "detune": 0.0, "phase": 0.0, "waveform": "sine"},
        {"freq": 200.0, "detune": 1200.0, "phase": 0.25, "waveform": "saw"},
        {"freq": 300.0, "detune": -1200.0, "phase": 0.5, "waveform": "triangle"},
    ]
    batch = render_batch(notes, 9600)
    assert list(batch) == [0, 1, 2]
    assert [len(batch[index]) for index in range(3)] == [96, 24, 64]
    assert batch[0][0] == pytest.approx(0.0, abs=1e-6)
    assert batch[1][0] == pytest.approx(-0.5, abs=1e-6)
    assert batch[2][0] == pytest.approx(1.0, abs=1e-6)
