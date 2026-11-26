from finsight.aurora_theme import aurora_css


def test_motion_opt_out():
    assert 'animation: finsightAurora' in aurora_css(True)
    assert 'animation: finsightAurora' not in aurora_css(False)
    assert 'animation: finsightOrb' not in aurora_css(False)


def test_accessibility_and_chart_surface():
    css = aurora_css()
    assert 'prefers-reduced-motion: reduce' in css
    assert 'animation: none !important' in css
    assert '[data-testid="stPlotlyChart"] {background: #fff;}' in css
