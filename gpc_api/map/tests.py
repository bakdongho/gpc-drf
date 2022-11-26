import pytest

from gpc_api.map.scrapper import NaverScrapper

# Create your tests here.


@pytest.fixture
def scrapper():
    return NaverScrapper()


def test_get_store(scrapper):
    # Given: 위도, 경도
    lng, lat = 37.5142950, 127.0626243

    stores = scrapper.run(lng, lat)
    assert isinstance(stores, list)
