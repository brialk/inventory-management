import argparse
import os
import sys

import requests

API_URL = os.environ.get("INVENTORY_API_URL", "http://127.0.0.1:5000")


def call_api(method, path, **kwargs):
    """Send a request to the Flask API. Returns the response, or None if unreachable."""
    try:
        return requests.request(method, f"{API_URL}{path}", timeout=10, **kwargs)
    except requests.exceptions.RequestException:
        print(
            f"Error: could not reach the inventory API at {API_URL}. "
            "Is the Flask server running?",
            file=sys.stderr,
        )
        return None

def format_item(item):
    line = f"[{item['id']}] {item['name']} - ${item['price']:.2f} - stock: {item['stock']}"
    if item.get("brand"):
        line += f" - brand: {item['brand']}"
    if item.get("barcode"):
        line += f" - barcode: {item['barcode']}"
    return line


def report_error(response):
    """Print the API's error message (or a generic one) and return exit code 1."""
    try:
        message = response.json().get("error", "Unknown error")
    except (ValueError, AttributeError):
        message = f"Request failed with status {response.status_code}"
    print(f"Error: {message}", file=sys.stderr)
    return 1

def cmd_list(args):
    response = call_api("GET", "/inventory")
    if response is None:
        return 1
    if response.status_code >= 400:
        return report_error(response)

    items = response.json()
    if not items:
        print("Inventory is empty.")
    for item in items:
        print(format_item(item))
    return 0


def cmd_view(args):
    response = call_api("GET", f"/inventory/{args.id}")
    if response is None:
        return 1
    if response.status_code >= 400:
        return report_error(response)

    item = response.json()
    for key, value in item.items():
        print(f"{key}: {value}")
    return 0


def cmd_add(args):
    payload = {"name": args.name, "price": args.price, "stock": args.stock}
    if args.barcode:
        payload["barcode"] = args.barcode

    response = call_api("POST", "/inventory", json=payload)
    if response is None:
        return 1
    if response.status_code >= 400:
        return report_error(response)

    print("Added:", format_item(response.json()))
    return 0


def cmd_update(args):
    payload = {}
    if args.name is not None:
        payload["name"] = args.name
    if args.price is not None:
        payload["price"] = args.price
    if args.stock is not None:
        payload["stock"] = args.stock

    if not payload:
        print("Error: provide at least one of --name, --price, or --stock.", file=sys.stderr)
        return 1

    response = call_api("PATCH", f"/inventory/{args.id}", json=payload)
    if response is None:
        return 1
    if response.status_code >= 400:
        return report_error(response)

    print("Updated:", format_item(response.json()))
    return 0


def cmd_delete(args):
    response = call_api("DELETE", f"/inventory/{args.id}")
    if response is None:
        return 1
    if response.status_code >= 400:
        return report_error(response)

    print(f"Deleted item {args.id}.")
    return 0


def cmd_find(args):
    params = {"barcode": args.barcode} if args.barcode else {"name": args.name}
    response = call_api("GET", "/lookup", params=params)
    if response is None:
        return 1
    if response.status_code >= 400:
        return report_error(response)

    data = response.json()
    products = [data] if args.barcode else data
    if not products:
        print("No products found.")
        return 0

    for product in products:
        print(
            f"{product.get('barcode') or '?'} | "
            f"{product.get('name') or 'Unknown name'} | "
            f"{product.get('brand') or 'Unknown brand'}"
        )
    return 0


def cmd_enrich(args):
    response = call_api("POST", f"/inventory/{args.id}/enrich")
    if response is None:
        return 1
    if response.status_code >= 400:
        return report_error(response)

    print("Enriched:", format_item(response.json()))
    return 0

def build_parser():
    parser = argparse.ArgumentParser(description="Inventory manager CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="Show all inventory items")
    list_parser.set_defaults(func=cmd_list)

    view_parser = subparsers.add_parser("view", help="Show one item in detail")
    view_parser.add_argument("id", type=int)
    view_parser.set_defaults(func=cmd_view)

    add_parser = subparsers.add_parser("add", help="Add a new item")
    add_parser.add_argument("--name", required=True)
    add_parser.add_argument("--price", type=float, required=True)
    add_parser.add_argument("--stock", type=int, required=True)
    add_parser.add_argument("--barcode")
    add_parser.set_defaults(func=cmd_add)

    update_parser = subparsers.add_parser("update", help="Update name, price, or stock")
    update_parser.add_argument("id", type=int)
    update_parser.add_argument("--name")
    update_parser.add_argument("--price", type=float)
    update_parser.add_argument("--stock", type=int)
    update_parser.set_defaults(func=cmd_update)

    delete_parser = subparsers.add_parser("delete", help="Delete an item")
    delete_parser.add_argument("id", type=int)
    delete_parser.set_defaults(func=cmd_delete)

    find_parser = subparsers.add_parser("find", help="Look up a product on OpenFoodFacts")
    group = find_parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--barcode")
    group.add_argument("--name")
    find_parser.set_defaults(func=cmd_find)

    enrich_parser = subparsers.add_parser("enrich", help="Fill in an item's details from OpenFoodFacts")
    enrich_parser.add_argument("id", type=int)
    enrich_parser.set_defaults(func=cmd_enrich)

    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())