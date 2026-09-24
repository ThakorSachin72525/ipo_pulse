import pytest

from app.providers.ipo_guru_client import IPOGuruClient


def test_client_requires_api_key():
    with pytest.raises(ValueError, match="API key is required"):
        IPOGuruClient(api_key="")


def test_client_uses_documented_endpoint_and_header():
    client = IPOGuruClient(api_key="test-key")

    assert client._base_url == "https://www.ipoguru.in/api/v2"
    assert client._api_key == "test-key"