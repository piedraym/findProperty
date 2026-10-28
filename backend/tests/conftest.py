from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import Listing


# Returns a function that builds a valid Listing with sensible defaults.
# Tests only pass the fields they care about, e.g. make_listing(price=500000).
@pytest.fixture
def make_listing():
    def _make(**overrides) -> Listing:
        data = {
            "id": "X1",
            "source": "MLS_A",
            "address": "1 Test St",
            "city": "Springfield",
            "state": "VA",
            "zip": "22150",
            "price": 400000,
            "bedrooms": 3,
            "bathrooms": 2.0,
            "sqft": 1000,
            "latitude": 38.0,
            "longitude": -77.0,
            "listed_date": date(2026, 9, 1),
            "status": "active",
            "description": "Nice home near the park",
        }
        data.update(overrides)
        return Listing(**data)

    return _make


# HTTP client for the real API, loaded with the sample dataset (12 listings)
@pytest.fixture
def client():
    return TestClient(app)
