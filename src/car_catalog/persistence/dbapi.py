"""Parameterized SQLite DB-API queries used by the catalog."""

import sqlite3


CarSearchRow = tuple[int, str, str, int, float, int, str]


def search_cars_by_manufacturer(
    connection: sqlite3.Connection,
    manufacturer_name: str,
) -> list[CarSearchRow]:
    """Return cars for a manufacturer using a parameterized DB-API query."""
    cursor = connection.execute(
        """
        SELECT cars.id, manufacturers.name, cars.model, cars.year,
               cars.price, cars.mileage, cars.vin
        FROM cars
        JOIN manufacturers ON manufacturers.id = cars.manufacturer_id
        WHERE lower(manufacturers.name) = lower(?)
        ORDER BY cars.id
        """,
        (manufacturer_name.strip(),),
    )
    return [
        (
            int(row[0]),
            str(row[1]),
            str(row[2]),
            int(row[3]),
            float(row[4]),
            int(row[5]),
            str(row[6]),
        )
        for row in cursor.fetchall()
    ]
