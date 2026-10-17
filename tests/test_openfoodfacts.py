from unittest.mock import MagicMock, patch

import pytest
import requests

from openfoodfacts_client import (
    OpenFoodFactsError,
    lookup_by_barcode,
    search_by_name,
)


def fake_response(status_code=200, json_data=None):
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_data
    return response


@patch("openfoodfacts_client.requests.get")
def test_lookup_by_barcode_returns_cleaned_product(mock_get):
    mock_get.return_value = fake_response(
        json_data={
            "status": 1,
            "product": {
                "code": "3274080005003",
                "product_name": "Spring Water",
                "brands": "Cristaline",
                "nutriscore_grade": "a",
            },
        }
    )

    product = lookup_by_barcode("3274080005003")

    assert product["barcode"] == "3274080005003"
    assert product["name"] == "Spring Water"
    assert product["brand"] == "Cristaline"
    assert product["nutriscore"] == "a"
    assert product["image_url"] is None


@patch("openfoodfacts_client.requests.get")
def test_lookup_by_barcode_returns_none_when_not_found(mock_get):
    mock_get.return_value = fake_response(status_code=404)

    assert lookup_by_barcode("0000000000000") is None


def test_lookup_by_barcode_rejects_non_digit_barcode():
    with pytest.raises(ValueError):
        lookup_by_barcode("not-a-barcode")


@patch("openfoodfacts_client.requests.get")
def test_search_by_name_returns_list_of_products(mock_get):
    mock_get.return_value = fake_response(
        json_data={
            "products": [
                {"code": "111", "product_name": "Oat Milk", "brands": "Oatly"},
                {"code": "222", "product_name": "Oat Drink", "brands": "Alpro"},
            ]
        }
    )

    results = search_by_name("oat")

    assert len(results) == 2
    assert results[0]["name"] == "Oat Milk"
    assert results[1]["brand"] == "Alpro"


@patch("openfoodfacts_client.requests.get")
def test_connection_failure_raises_openfoodfacts_error(mock_get):
    mock_get.side_effect = requests.exceptions.ConnectionError()

    with pytest.raises(OpenFoodFactsError):
        lookup_by_barcode("3274080005003")


@patch("openfoodfacts_client.requests.get")
def test_timeout_raises_openfoodfacts_error(mock_get):
    mock_get.side_effect = requests.exceptions.Timeout()

    with pytest.raises(OpenFoodFactsError):
        search_by_name("oat")