import json
from pathlib import Path


DATA_DIR = Path(__file__).parents[1] / "data"


def load_kpis():
    path = DATA_DIR / "kpi_definitions.json"

    if not path.exists():
        raise FileNotFoundError("kpi_definitions.json not found")

    with open(path) as f:
        data = json.load(f)

    return data


def load_pillar_weights():
    path = DATA_DIR / "pillar_weights.json"

    if not path.exists():
        raise FileNotFoundError("pillar_weights.json not found")

    with open(path) as f:
        return json.load(f)
