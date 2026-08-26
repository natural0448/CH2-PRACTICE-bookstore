from dataclasses import dataclass

from django.db import connections

from .models import OrmItem


@dataclass(frozen=True)
class RawItemDTO:
    id: int
    name: str


def insert_orm_item(name):
    item = OrmItem.objects.using("sqlite3").create(name=name)
    return {"id": item.id, "name": item.name}


def insert_raw_item(name):
    with connections["sqlite3"].cursor() as cursor:
        cursor.execute(
            "INSERT INTO raw_item (name) VALUES (%s)",
            [name],
        )
        item_id = cursor.lastrowid
    return {"id": item_id, "name": name}


def find_all_orm_items():
    return list(
        # default인 경우는 .using("디비명") 생략 가능
        OrmItem.objects.using("sqlite3").order_by("id").values("id", "name")
    )


def find_all_raw_items():
    # default인 경우는 ['디비명'] 생략 가능
    with connections["sqlite3"].cursor() as cursor:
        cursor.execute(
            "SELECT id, name FROM raw_item ORDER BY id"
        )
        rows = cursor.fetchall()

    return [
        RawItemDTO(id=row[0], name=row[1])
        for row in rows
    ]
