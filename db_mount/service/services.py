from dataclasses import asdict

from db_mount.repository.sqlite_repository import (
    find_all_orm_items,
    find_all_raw_items,
)


def get_orm_items():
    return find_all_orm_items()


def get_raw_items():
    return [asdict(item) for item in find_all_raw_items()]