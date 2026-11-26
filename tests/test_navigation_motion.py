from finsight.navigation_motion import navigation_css, workspace_key


def test_navigation_change_animates():
    assert 'animation: finsightWorkspaceEnter 320ms' in navigation_css(True, True)
    assert 'st-key-fs_workspace_' in navigation_css(True)


def test_ordinary_rerun_keeps_rules_and_key():
    assert navigation_css(True, True) == navigation_css(True, False)
    assert workspace_key('Overview') == workspace_key('Overview')
    assert workspace_key('Overview') != workspace_key('AI Copilot')


def test_motion_disabled():
    assert '@keyframes' not in navigation_css(False, True)
    assert 'transition: background-color' not in navigation_css(False, True)


def test_reduced_motion():
    assert 'prefers-reduced-motion: reduce' in navigation_css(True, True)
    assert 'animation: none !important' in navigation_css(True, True)
