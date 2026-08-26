from django.db import migrations


def seed_orm_items(apps, schema_editor):
    OrmItem = apps.get_model("db_mount", "OrmItem")

    OrmItem.objects.using("sqlite3").bulk_create(
        [
            OrmItem(id=1, name="ORM item 1"),
            OrmItem(id=2, name="ORM item 2"),
        ]
    )


def remove_orm_items(apps, schema_editor):
    OrmItem = apps.get_model("db_mount", "OrmItem")

    OrmItem.objects.using("sqlite3").filter(id__in=[1, 2]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("db_mount", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            sql=[
                """
                CREATE TABLE raw_item (
                    id INTEGER PRIMARY KEY,
                    name VARCHAR(50) NOT NULL
                )
                """,
                """
                INSERT INTO raw_item (id, name)
                VALUES (1, 'Raw item 1')
                """,
                """
                INSERT INTO raw_item (id, name)
                VALUES (2, 'Raw item 2')
                """,
            ],
            reverse_sql=[
                "DROP TABLE raw_item",
            ],
        ),
        migrations.RunPython(
            seed_orm_items,
            remove_orm_items,
        ),
    ]