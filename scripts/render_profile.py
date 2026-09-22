"""Render both profile-card themes from one canonical layout."""

from __future__ import annotations

import html
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

THEMES = {
    "dark": {
        "background": "#161b22",
        "text": "#c9d1d9",
        "key": "#ffa657",
        "value": "#a5d6ff",
        "add": "#3fb950",
        "delete": "#f85149",
        "muted": "#616e7f",
    },
    "light": {
        "background": "#f6f8fa",
        "text": "#24292f",
        "key": "#953800",
        "value": "#0a3069",
        "add": "#1a7f37",
        "delete": "#cf222e",
        "muted": "#c2cfde",
    },
}

DEFAULT_STATS = {
    "repo_data": 27,
    "contrib_data": 7,
    "star_data": 1,
    "follower_data": 4,
}

# The original 28-row Daredevil/gargoyle artwork, resampled to Andrew's
# 39-column by 25-row drawing area so it fits the reference grid without
# cutting off the bottom of the sculpture.
ASCII_ART = (
    "             .::.",
    "            -@@@%",
    "            :@@@@=",
    "             *@%%#*+-.",
    "          :+%@@%%@@@@@*-",
    "         :@@@@@@@@@@@@@@:",
    "         -@@%@@@@@@@@@@@*",
    "         *@@=:%@@@@@@@@@#",
    "        .@@#  -#@@@@@@@@@",
    "        %@@=   -@@@@@@@@@.",
    "        *@@*:...@@@@@@@@@%.",
    "      .*%@@@@@@@@@@@@@@@@@+",
    "      =@@@@@@@@@@@@@@@@@@@%",
    "       #@@@@@@@%##=:::%@@@#.   :-+**:",
    "        :=*%@@@@#     =@@@. :=#%%#+.",
    "            =#@@@#+   =@@-:*%%##*#-",
    "            -=%@@%%- :@@@=#%%####:",
    "           :=**+###%#%#@##@%%###*.",
    "          .+*+===+#%@%#%#@@%%%##=.",
    "     .    ++++*#%%@%%@@%#@@%%###:    .",
    "          +#*%###%@@@%@@@@@@%%#.   ...",
    "          +***#%%@@@##%@@%*%%=:    ..:",
    ".         :#%%%@@@@%##%@@%...  . ....:",
    ".....      .=@@@@@%%#%@@@%%+.........:",
    ".........    -@@@@@@%%%@@%%%=........:",
)

STAT_IDS = tuple(DEFAULT_STATS)


def _dots(total_width: int, value: int) -> str:
    """Return a padded dot leader whose combined width with value is fixed."""
    count = max(1, total_width - len(f"{value:,}") - 2)
    return f" {'.' * count} "


def read_existing_stats(path: Path) -> dict[str, int]:
    """Preserve current live figures when regenerating the layout."""
    values = DEFAULT_STATS.copy()
    if not path.exists():
        return values

    source = path.read_text(encoding="utf-8")
    for element_id in STAT_IDS:
        match = re.search(
            rf'<tspan[^>]*\bid="{element_id}"[^>]*>([^<]+)</tspan>', source
        )
        if match and match.group(1).replace(",", "").isdigit():
            values[element_id] = int(match.group(1).replace(",", ""))
    return values


def render_svg(theme_name: str, stats: dict[str, int]) -> str:
    """Return a complete profile SVG for one theme."""
    theme = THEMES[theme_name]
    art = "\n".join(
        f'<tspan x="15" y="{30 + index * 20}">{html.escape(line)}</tspan>'
        for index, line in enumerate(ASCII_ART)
    )

    repo = stats["repo_data"]
    contributed = stats["contrib_data"]
    stars = stats["star_data"]
    followers = stats["follower_data"]
    repo_dots = _dots(8, repo)
    star_dots = _dots(16, stars)
    follower_dots = _dots(12, followers)

    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" font-family="ConsolasFallback,Consolas,monospace" width="985px" height="530px" font-size="16px" role="img" aria-label="Edmond Abraham's developer profile">
<style>
@font-face {{
src: local('Consolas'), local('Consolas Bold');
font-family: 'ConsolasFallback';
font-display: swap;
-webkit-size-adjust: 109%;
size-adjust: 109%;
}}
.key {{fill: {theme['key']};}}
.value {{fill: {theme['value']};}}
.addColor {{fill: {theme['add']};}}
.delColor {{fill: {theme['delete']};}}
.cc {{fill: {theme['muted']};}}
text, tspan {{white-space: pre;}}
</style>
<rect width="985px" height="530px" fill="{theme['background']}" rx="15"/>
<text x="15" y="30" fill="{theme['text']}" class="ascii">
{art}
</text>
<text x="390" y="30" fill="{theme['text']}">
<tspan x="390" y="30">edmond@gitedmond</tspan> -———————————————————————————————————————-—-
<tspan x="390" y="50" class="cc">. </tspan><tspan class="key">OS</tspan>:<tspan class="cc"> ............................. </tspan><tspan class="value">Windows 11, Linux</tspan>
<tspan x="390" y="70" class="cc">. </tspan><tspan class="key">Uptime</tspan>:<tspan class="cc"> ..................... </tspan><tspan class="value">[add age / coding years]</tspan>
<tspan x="390" y="90" class="cc">. </tspan><tspan class="key">Host</tspan>:<tspan class="cc"> ....................... </tspan><tspan class="value">[add company or school]</tspan>
<tspan x="390" y="110" class="cc">. </tspan><tspan class="key">Kernel</tspan>:<tspan class="cc"> .................... </tspan><tspan class="value">[add role or specialty]</tspan>
<tspan x="390" y="130" class="cc">. </tspan><tspan class="key">IDE</tspan>:<tspan class="cc"> ................... </tspan><tspan class="value">VS Code, IntelliJ IDEA</tspan>
<tspan x="390" y="150" class="cc">. </tspan>
<tspan x="390" y="170" class="cc">. </tspan><tspan class="key">Languages</tspan>.<tspan class="key">Programming</tspan>:<tspan class="cc"> . </tspan><tspan class="value">C#, C++, Java, TypeScript, Python, SQL</tspan>
<tspan x="390" y="190" class="cc">. </tspan><tspan class="key">Languages</tspan>.<tspan class="key">Computer</tspan>:<tspan class="cc"> .... </tspan><tspan class="value">JavaScript, HTML, CSS, JSON</tspan>
<tspan x="390" y="210" class="cc">. </tspan><tspan class="key">Languages</tspan>.<tspan class="key">Real</tspan>:<tspan class="cc"> ............................. </tspan><tspan class="value">English</tspan>
<tspan x="390" y="230" class="cc">. </tspan>
<tspan x="390" y="250" class="cc">. </tspan><tspan class="key">Hobbies</tspan>.<tspan class="key">Software</tspan>:<tspan class="cc"> . </tspan><tspan class="value">Open source, self-hosting, automation</tspan>
<tspan x="390" y="270" class="cc">. </tspan><tspan class="key">Hobbies</tspan>.<tspan class="key">Hardware</tspan>:<tspan class="cc"> ........... </tspan><tspan class="value">Homelab, PC building</tspan>
<tspan x="390" y="310">- Contact</tspan> -——————————————————————————————————————————————-—-
<tspan x="390" y="330" class="cc">. </tspan><tspan class="key">Email</tspan>.<tspan class="key">Personal</tspan>:<tspan class="cc"> .................. </tspan><tspan class="value">edmondbusiness@gmail.com</tspan>
<tspan x="390" y="350" class="cc">. </tspan><tspan class="key">Email</tspan>.<tspan class="key">Personal</tspan>:<tspan class="cc"> ....................... </tspan><tspan class="value">[add personal email]</tspan>
<tspan x="390" y="370" class="cc">. </tspan><tspan class="key">Email</tspan>.<tspan class="key">Work</tspan>:<tspan class="cc"> ............................ </tspan><tspan class="value">[add work email]</tspan>
<tspan x="390" y="390" class="cc">. </tspan><tspan class="key">LinkedIn</tspan>:<tspan class="cc"> ......................... </tspan><tspan class="value">edmond-abraham-9b900a221</tspan>
<tspan x="390" y="410" class="cc">. </tspan><tspan class="key">Discord</tspan>:<tspan class="cc"> .................................. </tspan><tspan class="value">[add Discord]</tspan>
<tspan x="390" y="450">- GitHub Stats</tspan> -—————————————————————————————————————————-—-
<tspan x="390" y="470" class="cc">. </tspan><tspan class="key">Repos</tspan>:<tspan class="cc" id="repo_data_dots">{repo_dots}</tspan><tspan class="value" id="repo_data">{repo:,}</tspan> {{<tspan class="key">Contributed</tspan>: <tspan class="value" id="contrib_data">{contributed:,}</tspan>}} | <tspan class="key">Stars</tspan>:<tspan class="cc" id="star_data_dots">{star_dots}</tspan><tspan class="value" id="star_data">{stars:,}</tspan>
<tspan x="390" y="490" class="cc">. </tspan><tspan class="key">Commits</tspan>:<tspan class="cc"> .................. </tspan><tspan class="value">[pending]</tspan> | <tspan class="key">Followers</tspan>:<tspan class="cc" id="follower_data_dots">{follower_dots}</tspan><tspan class="value" id="follower_data">{followers:,}</tspan>
<tspan x="390" y="510" class="cc">. </tspan><tspan class="key">Lines of Code on GitHub</tspan>:<tspan class="cc"> .. </tspan><tspan class="value">[pending]</tspan> ( <tspan class="addColor">[pending]++</tspan>, <tspan class="delColor">[pending]--</tspan> )
</text>
</svg>
'''


def main() -> None:
    stats = read_existing_stats(ROOT / "dark_mode.svg")
    for theme_name in THEMES:
        output = ROOT / f"{theme_name}_mode.svg"
        output.write_text(render_svg(theme_name, stats), encoding="utf-8")


if __name__ == "__main__":
    main()
