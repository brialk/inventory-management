import requests

BASE_URL = "https://world.openfoodfacts.org"
HEADERS = {
    "User-Agent": "Inventory Manager/1.0 (briannagogins@gmail.com)"}
FIELDS = "code,product_name,brands,image_url,nutriscore_grade,quantity"

class OpenFoodFactsError(RuntimeError):
    """Raised when the OpenFoodFacts service can't be reached or answers badly."""

def _get_json(url, params):
    """Call OpenFoodFacts and return parsed JSON, or None if the page doesn't exist."""
    try:
        response = requests.get(url, params=params, headers=HEADERS, timeout=10)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout as error:
        raise OpenFoodFactsError("OpenFoodFacts too long to respond.") from error
    except requests.exceptions.RequestException as error:
        raise OpenFoodFactsError(f"OpenFoodFacts request failed: {error}") from error
    except ValueError as error:
        raise OpenFoodFactsError("OpenFoodFacts returned invalid JSON.") from error

def _clean_product(product):
    """Keep only the fields we care about, with friendly names."""
    return {
        "barcode": product.get("code"),
        "name": product.get("product_name") or None,
        "brand": product.get("brands") or None,
        "image_url": product.get("image_url") or None,
        "nutriscore": product.get("nutriscore_grade") or None,
        "quantity": product.get("quantity") or None,
    }

def lookup_by_barcode(barcode):
    """Return cleaned product details for a barcode, or None if not found."""
    if not isinstance(barcode, str) or not barcode.isdigit():
        raise ValueError("Barcode must contain digits only.")

    data = _get_json(
        f"{BASE_URL}/api/v2/product/{barcode}.json", {"fields": FIELDS}
    )
    if data is None:
        return None

    product = data.get("product")
    return _clean_product(product) if product else None


def search_by_name(name, limit=5):
    """Return a list of cleaned products matching a name."""
    data = _get_json(
        f"{BASE_URL}/cgi/search.pl",
        {
            "search_terms": name,
            "search_simple": 1,
            "action": "process",
            "json": 1,
            "page_size": limit,
            "fields": FIELDS,
        },
    )
    if data is None:
        return []

    return [_clean_product(product) for product in data.get("products", [])]