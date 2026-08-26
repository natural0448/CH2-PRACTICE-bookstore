from dataclasses import asdict

from db_mount.repository.sqlite_repository import (
    find_all_orm_items,
    find_all_raw_items,
    insert_orm_item,
    insert_raw_item,
)


def validate_name(name):
    normalized_name = name.strip()
    if not normalized_name:
        raise ValueError("name을 입력해 주세요.")
    if len(normalized_name) > 50:
        raise ValueError("name은 50자 이하여야 합니다.")
    return normalized_name


def create_orm_item(name):
    return insert_orm_item(validate_name(name))


def create_raw_item(name):
    return insert_raw_item(validate_name(name))


def get_orm_items():
    return find_all_orm_items()


def get_raw_items():
    return [asdict(item) for item in find_all_raw_items()]
