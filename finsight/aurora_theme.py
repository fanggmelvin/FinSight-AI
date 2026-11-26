"""Decorative CSS only; financial chart encodings remain untouched."""


def aurora_css(motion: bool = True) -> str:
    css = '''
    [data-testid="stAppViewContainer"] {
      background-color: #eaf1f9;
      background-image: radial-gradient(ellipse at 20% 30%, #a4c9f5 0%, transparent 53%),
        radial-gradient(ellipse at 75% 35%, #b3eadb 0%, transparent 50%),
        radial-gradient(ellipse at 45% 85%, #c9c1f4 0%, transparent 52%);
      background-size: 155% 155%;
      background-position: 0% 35%;
    }
    [data-testid="stMain"], [data-testid="stHeader"] {background: transparent;}
    [data-testid="stSidebar"] {background: linear-gradient(155deg,#10243D,#173D59);}
    [data-testid="stMetric"], [data-testid="stChatMessage"], [data-testid="stExpander"] {
      background: rgba(255,255,255,.84); border-color: rgba(255,255,255,.95);
      box-shadow: 0 5px 20px rgba(36,75,112,.10);
    }
    [data-testid="stMetric"] {backdrop-filter: blur(10px); transition: box-shadow .25s ease;}
    [data-testid="stMetric"]:hover {box-shadow: 0 8px 24px rgba(36,75,112,.20);}
    [data-testid="stBottom"], [data-testid="stBottomBlockContainer"] {background: transparent !important;}
    [data-testid="stChatInput"] {background: rgba(255,255,255,.92); border-radius: 12px;}
    [data-testid="stChatMessage"] {box-shadow: none;}
    [data-testid="stPlotlyChart"] {background: #fff;}
    .finsight-orb {width: 42px; height: 42px; border-radius: 50%;
      background: conic-gradient(#7caef4,#79e1c4,#a9a5ed,#7caef4);
      box-shadow: 0 0 18px #7bbdd888;}
    @keyframes finsightAurora {0% {background-position: 0% 35%;} 50% {background-position: 100% 65%;} 100% {background-position: 0% 35%;}}
    @keyframes finsightOrb {to {transform: rotate(360deg);}}
    '''
    if motion:
        css += '''
        [data-testid="stAppViewContainer"] {animation: finsightAurora 18s ease-in-out infinite;}
        .finsight-orb {animation: finsightOrb 8s linear infinite;}
        '''
    return css + '''
    @media (prefers-reduced-motion: reduce) {
      [data-testid="stAppViewContainer"], .finsight-orb {animation: none !important;}
      [data-testid="stMetric"] {transition: none !important;}
    }
    '''
