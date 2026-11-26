"""Workspace-scoped entrance animation; no browser scripts or financial changes."""
import re


def workspace_key(page):
    return 'fs_workspace_' + re.sub(r'[^a-z0-9]+', '_', page.lower()).strip('_')


def navigation_css(motion=True, changed=False):
    # changed is retained for compatibility; keyed mounts replace transient CSS.
    css = '''
    [data-testid="stSidebar"] [class*="st-key-nav_"] button {
      border-color: transparent; position: relative;
    }
    [data-testid="stSidebar"] [class*="st-key-nav_"] button[kind="primary"] {
      box-shadow: inset 3px 0 #76dbc3;
    }
    [data-testid="stSidebar"] [class*="st-key-nav_"] button:hover {
      background-color: #385a79;
    }
    '''
    if motion:
        css += '''
        [data-testid="stSidebar"] [class*="st-key-nav_"] button {
          transition: background-color 150ms ease, border-color 150ms ease, box-shadow 250ms ease;
        }
        [data-testid="stSidebar"] [class*="st-key-nav_"] button:active {
          background-color: #527da0; transform: translateX(2px);
        }
        @keyframes finsightWorkspaceEnter {
          from {opacity: .15; transform: translateY(12px);}
          to {opacity: 1; transform: translateY(0);}
        }
        [class*="st-key-fs_workspace_"] {
          animation: finsightWorkspaceEnter 320ms cubic-bezier(.2,.75,.25,1) both;
        }
        '''
    return css + '''
    @media (prefers-reduced-motion: reduce) {
      [class*="st-key-fs_workspace_"] {animation: none !important;}
      [data-testid="stSidebar"] [class*="st-key-nav_"] button {transition: none !important; transform: none !important;}
    }
    '''
