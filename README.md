# Inventory Manager

A small inventory system for a retail company: a Flask REST API, an OpenFoodFacts
integration for product details, and a command-line interface.

## Installation

```bash
git clone <your-repo-url>
cd inventory-manager
pipenv install
pipenv shell
```

Before real use, open `openfoodfacts_client.py` and replace the contact email in
`HEADERS` (OpenFoodFacts asks every app to identify itself).

## Running

Start the API (debug mode on):

```bash
python app.py
```

Run the tests (no internet or server needed):

```bash
pytest
```

Inventory is stored in a Python list, so it resets when the server restarts.

## API Endpoints

| Method | Path | Description | Success |
| --- | --- | --- | --- |
| GET | `/inventory` | List all items | 200 |
| GET | `/inventory/<id>` | Get one item | 200 |
| POST | `/inventory` | Add an item (`name`, `price`, `stock`, optional `barcode`) | 201 |
| PATCH | `/inventory/<id>` | Update `name`, `price`, `stock`, or `barcode` | 200 |
| DELETE | `/inventory/<id>` | Delete an item | 204 |
| GET | `/lookup?barcode=...` or `?name=...` | Search OpenFoodFacts | 200 |
| POST | `/inventory/<id>/enrich` | Add brand, image, Nutri-Score, and size from OpenFoodFacts | 200 |

Errors: `400` invalid input, `404` not found, `502` OpenFoodFacts unavailable.
All errors return `{"error": "message"}`.

## CLI Examples

Start the API first, then in another terminal:

```bash
python cli.py add --name "Oat Milk" --price 4.99 --stock 25 --barcode 3274080005003
python cli.py list
python cli.py view 1
python cli.py update 1 --price 5.49 --stock 20
python cli.py find --name "oat milk"
python cli.py find --barcode 3274080005003
python cli.py enrich 1
python cli.py delete 1
```

## Notes

OpenFoodFacts limits requests to about 15 product reads and 10 searches per
minute per IP, so avoid calling it in a loop.