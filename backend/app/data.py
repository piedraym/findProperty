import json
from pathlib import Path

from app.models import Listing

DATA_FILE = Path(__file__).parent.parent / "data" / "sample_listings.json"


def load_listings() -> list[Listing]:
    with DATA_FILE.open() as f:
        return [Listing.model_validate(item) for item in json.load(f)]
