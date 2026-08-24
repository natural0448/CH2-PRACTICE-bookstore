import csv
import json
import os
from pathlib import Path

import MySQLdb
from MySQLdb.cursors import DictCursor
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent.parent
ENV_FILE = PROJECT_DIR / ".env"
load_dotenv(ENV_FILE)

EXPECTED_COUNTS = {
    "member": 4,
    "category": 3,
    "book": 5,
    "book_order": 5,
    "order_item": 6,
}

CREATE_TABLES = [
    """
    CREATE TABLE IF NOT EXISTS member (
        member_id VARCHAR(20) PRIMARY KEY,
        member_name VARCHAR(100) NOT NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS category (
        category_code VARCHAR(20) PRIMARY KEY,
        category_name VARCHAR(100) NOT NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS book (
        book_id VARCHAR(20) PRIMARY KEY,
        book_name VARCHAR(200) NOT NULL,
        category_code VARCHAR(20) NOT NULL,
        CONSTRAINT fk_book_category
            FOREIGN KEY (category_code) REFERENCES category(category_code)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS book_order (
        order_id VARCHAR(20) PRIMARY KEY,
        member_id VARCHAR(20) NOT NULL,
        order_datetime DATETIME NOT NULL,
        order_status_code VARCHAR(20) NOT NULL,
        CONSTRAINT fk_order_member
            FOREIGN KEY (member_id) REFERENCES member(member_id),
        CONSTRAINT chk_order_status
            CHECK (order_status_code IN ('PAID', 'SHIPPING', 'DONE', 'CANCELLED'))
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS order_item (
        order_id VARCHAR(20) NOT NULL,
        book_id VARCHAR(20) NOT NULL,
        quantity SMALLINT UNSIGNED NOT NULL,
        unit_price DECIMAL(12, 2) NOT NULL,
        PRIMARY KEY (order_id, book_id),
        CONSTRAINT fk_item_order
            FOREIGN KEY (order_id) REFERENCES book_order(order_id),
        CONSTRAINT fk_item_book
            FOREIGN KEY (book_id) REFERENCES book(book_id),
        CONSTRAINT chk_item_quantity CHECK (quantity BETWEEN 1 AND 999),
        CONSTRAINT chk_item_price CHECK (unit_price > 0)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
]


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def open_connection():
    required_variables = (
        "BOOKSTORE_MYSQL_NAME",
        "BOOKSTORE_MYSQL_USER",
        "BOOKSTORE_MYSQL_PASSWORD",
    )
    missing_variables = [
        variable for variable in required_variables if variable not in os.environ
    ]
    if missing_variables:
        missing_names = ", ".join(missing_variables)
        raise RuntimeError(
            f"Missing MySQL environment variables: {missing_names}. "
            f"Check {ENV_FILE}."
        )

    return MySQLdb.connect(
        host=os.getenv("BOOKSTORE_MYSQL_HOST", "127.0.0.1"),
        port=int(os.getenv("BOOKSTORE_MYSQL_PORT", "3306")),
        user=os.environ["BOOKSTORE_MYSQL_USER"],
        passwd=os.environ["BOOKSTORE_MYSQL_PASSWORD"],
        db=os.environ["BOOKSTORE_MYSQL_NAME"],
        charset="utf8mb4",
        cursorclass=DictCursor,
    )


def main():
    with (BASE_DIR / "day5-validation.json").open(encoding="utf-8") as file:
        validation = json.load(file)
    if validation.get("status") != "ready":
        raise SystemExit("day5-validation.json 상태가 ready가 아닙니다.")

    rows = read_csv(BASE_DIR / "standardized-orders.csv")
    connection = open_connection()

    try:
        with connection.cursor() as cursor:
            for statement in CREATE_TABLES:
                cursor.execute(statement)
        connection.commit()

        with connection.cursor() as cursor:
            for row in rows:
                cursor.execute(
                    """
                    INSERT INTO member (member_id, member_name)
                    VALUES (%s, %s)
                    ON DUPLICATE KEY UPDATE member_name = %s
                    """,
                    (row["member_id"], row["member_name"], row["member_name"]),
                )
                cursor.execute(
                    """
                    INSERT INTO category (category_code, category_name)
                    VALUES (%s, %s)
                    ON DUPLICATE KEY UPDATE category_name = %s
                    """,
                    (
                        row["category_code"],
                        row["category_name"],
                        row["category_name"],
                    ),
                )
                cursor.execute(
                    """
                    INSERT INTO book (book_id, book_name, category_code)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        book_name = %s,
                        category_code = %s
                    """,
                    (
                        row["book_id"],
                        row["book_name"],
                        row["category_code"],
                        row["book_name"],
                        row["category_code"],
                    ),
                )
                cursor.execute(
                    """
                    INSERT INTO book_order (
                        order_id,
                        member_id,
                        order_datetime,
                        order_status_code
                    )
                    VALUES (%s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        member_id = %s,
                        order_datetime = %s,
                        order_status_code = %s
                    """,
                    (
                        row["order_id"],
                        row["member_id"],
                        row["order_datetime"],
                        row["order_status_code"],
                        row["member_id"],
                        row["order_datetime"],
                        row["order_status_code"],
                    ),
                )
                cursor.execute(
                    """
                    INSERT INTO order_item (
                        order_id,
                        book_id,
                        quantity,
                        unit_price
                    )
                    VALUES (%s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        quantity = %s,
                        unit_price = %s
                    """,
                    (
                        row["order_id"],
                        row["book_id"],
                        row["quantity"],
                        row["unit_price"],
                        row["quantity"],
                        row["unit_price"],
                    ),
                )

            counts = {}
            for table_name in EXPECTED_COUNTS:
                cursor.execute(
                    f"SELECT COUNT(*) AS row_count FROM {table_name}"
                )
                counts[table_name] = cursor.fetchone()["row_count"]

            cursor.execute(
                """
                SELECT COUNT(*) AS row_count
                FROM order_item AS oi
                JOIN book_order AS o ON o.order_id = oi.order_id
                JOIN member AS m ON m.member_id = o.member_id
                JOIN book AS b ON b.book_id = oi.book_id
                JOIN category AS c ON c.category_code = b.category_code
                """
            )
            joined_count = cursor.fetchone()["row_count"]

            cursor.execute(
                """
                SELECT COALESCE(SUM(quantity * unit_price), 0) AS total_amount
                FROM order_item
                """
            )
            total_amount = cursor.fetchone()["total_amount"]

        if counts != EXPECTED_COUNTS:
            raise RuntimeError(
                f"MySQL 건수 불일치: expected={EXPECTED_COUNTS}, actual={counts}"
            )
        if joined_count != 6 or str(total_amount) != "153000.00":
            raise RuntimeError(
                f"복원 검증 실패: joined={joined_count}, amount={total_amount}"
            )

        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    print("MySQL 적재 PASS")
    print(counts)
    print("join:", joined_count, "amount:", total_amount)


if __name__ == "__main__":
    main()