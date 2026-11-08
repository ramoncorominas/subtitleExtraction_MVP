from pipeline.frame_sampler import build_sampling_plan, compute_index_padding


def test_build_sampling_plan_basic() -> None:
    indices = build_sampling_plan(total_frames=100, fps=25.0, interval_seconds=0.5)
    assert indices[:4] == [0, 12, 24, 36]


def test_build_sampling_plan_invalid_fps() -> None:
    try:
        build_sampling_plan(total_frames=100, fps=0.0, interval_seconds=0.5)
    except ValueError:
        assert True
    else:
        assert False


def test_compute_index_padding_scales_with_sample_count() -> None:
    assert compute_index_padding(0) == 1
    assert compute_index_padding(1) == 1
    assert compute_index_padding(40) == 2
    assert compute_index_padding(400) == 3
