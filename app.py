from flask import Flask, jsonify, request
from openfoodfacts_client import lookup_by_barcode, search_by_name

app = Flask(__name__)
inventory = []  # In-memory inventory list

def find_item(item_id):
    """Helper function to find an item in the inventory by its ID or None."""
    return next((item for item in inventory if item["id"] == item_id), None)

def next_id():
    """Helper function to pick an ID 1 higher."""
    return max((item["id"] for item in inventory), default=0) + 1

def get_body():
    """Helper function to get the JSON body of a request."""
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}

def validate_fields(data, require_all):
    """Check name, price, stock, barcode. Returns (clean_dict, error_message)."""
    clean = {}

    if "name" in data:
        if not isinstance(data["name"], str) or not data["name"].strip():
            return None, "name must be a non-empty string"
        clean["name"] = data["name"].strip()
    elif require_all:
        return None, "name is required"

    if "price" in data:
        price = data["price"]
        if isinstance(price, bool) or not isinstance(price, (int, float)) or price < 0:
            return None, "price must be a number that is 0 or more"
        clean["price"] = price
    elif require_all:
        return None, "price is required"

    if "stock" in data:
        stock = data["stock"]
        if isinstance(stock, bool) or not isinstance(stock, int) or stock < 0:
            return None, "stock must be a whole number that is 0 or more"
        clean["stock"] = stock
    elif require_all:
        return None, "stock is required"

    if "barcode" in data:
        barcode = data["barcode"]
        if barcode is not None and (not isinstance(barcode, str) or not barcode.isdigit()):
            return None, "barcode must be a string of digits"
        clean["barcode"] = barcode

    return clean, None

@app.get("/inventory")
def get_inventory():
    return jsonify(inventory), 200


@app.get("/inventory/<int:item_id>")
def get_item(item_id):
    item = find_item(item_id)
    if item is None:
        return jsonify({"error": "Item not found"}), 404
    return jsonify(item), 200


@app.post("/inventory")
def add_item():
    clean, error = validate_fields(get_body(), require_all=True)
    if error:
        return jsonify({"error": error}), 400

    item = {
        "id": next_id(),
        "name": clean["name"],
        "barcode": clean.get("barcode"),
        "price": clean["price"],
        "stock": clean["stock"],
        "brand": None,
        "image_url": None,
        "nutriscore": None,
        "quantity": None,
    }
    inventory.append(item)
    return jsonify(item), 201


@app.patch("/inventory/<int:item_id>")
def update_item(item_id):
    item = find_item(item_id)
    if item is None:
        return jsonify({"error": "Item not found"}), 404

    clean, error = validate_fields(get_body(), require_all=False)
    if error:
        return jsonify({"error": error}), 400
    if not clean:
        return jsonify({"error": "No valid fields to update"}), 400

    item.update(clean)
    return jsonify(item), 200


@app.delete("/inventory/<int:item_id>")
def delete_item(item_id):
    item = find_item(item_id)
    if item is None:
        return jsonify({"error": "Item not found"}), 404

    inventory.remove(item)
    return "", 204

@app.get("/lookup")
def lookup_product():
    """Search OpenFoodFacts by ?barcode= or ?name= (does not change inventory)."""
    barcode = request.args.get("barcode")
    name = request.args.get("name")

    if not barcode and not name:
        return jsonify({"error": "Provide a barcode or a name to look up"}), 400

    try:
        if barcode:
            product = lookup_by_barcode(barcode)
            if product is None:
                return jsonify({"error": "Product not found on OpenFoodFacts"}), 404
            return jsonify(product), 200
        return jsonify(search_by_name(name)), 200
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except OpenFoodFactsError as error:
        return jsonify({"error": str(error)}), 502


@app.post("/inventory/<int:item_id>/enrich")
def enrich_item(item_id):
    """Fill in brand, image, Nutri-Score, and size from OpenFoodFacts using the item's barcode."""
    item = find_item(item_id)
    if item is None:
        return jsonify({"error": "Item not found"}), 404
    if not item["barcode"]:
        return jsonify({"error": "Item has no barcode to look up"}), 400

    try:
        product = lookup_by_barcode(item["barcode"])
    except OpenFoodFactsError as error:
        return jsonify({"error": str(error)}), 502

    if product is None:
        return jsonify({"error": "Product not found on OpenFoodFacts"}), 404

    for key in ("brand", "image_url", "nutriscore", "quantity"):
        if product.get(key):
            item[key] = product[key]

    return jsonify(item), 200


if __name__ == "__main__":
    app.run(debug=True)