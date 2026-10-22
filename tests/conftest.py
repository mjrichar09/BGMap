import os
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_xml() -> Path:
    return FIXTURES / "thing_sample.xml"
