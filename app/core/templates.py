from pathlib import Path
from fastapi.templating import Jinja2Templates

_CSS_PATH = Path("app/static/dist/app.css")
try:
    ASSET_VERSION = str(int(_CSS_PATH.stat().st_mtime))
except FileNotFoundError:
    ASSET_VERSION = "0"


def make_templates(directory: str = "app/templates") -> Jinja2Templates:
    t = Jinja2Templates(directory=directory)
    t.env.globals["asset_version"] = ASSET_VERSION
    return t
