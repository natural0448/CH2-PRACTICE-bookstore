import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from University.models import UniversityAdmission


REQUIRED_HEADERS = {
    "area",
    "region",
    "university",
    "line",
    "lesson",
    "type",
    "personnel",
}


class Command(BaseCommand):
    help = "대학교 모집 CSV 데이터를 적재합니다."

    def add_arguments(self, parser):
        parser.add_argument("csv_file", type=str)
        parser.add_argument(
            "--batch-size",
            type=int,
            default=500,
        )

    def handle(self, *args, **options):
        csv_path = Path(options["csv_file"])
        batch_size = options["batch_size"]

        if not csv_path.exists():
            raise CommandError(
                f"파일을 찾을 수 없습니다: {csv_path}"
            )

        batch = []

        with csv_path.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as file:
            reader = csv.DictReader(file)

            actual_headers = set(reader.fieldnames or [])
            missing_headers = REQUIRED_HEADERS - actual_headers

            if missing_headers:
                raise CommandError(
                    f"필수 컬럼이 없습니다: {missing_headers}"
                )

            with transaction.atomic():
                before_count = UniversityAdmission.objects.count()

                for row in reader:
                    batch.append(
                        UniversityAdmission(
                            area=row["area"].strip(),
                            region=row["region"].strip(),
                            university=row["university"].strip(),
                            line=row["line"].strip(),
                            lesson=row["lesson"].strip(),
                            type=row["type"].strip(),
                            personnel=row["personnel"].strip(),
                        )
                    )

                    if len(batch) >= batch_size:
                        UniversityAdmission.objects.bulk_create(
                            batch,
                            batch_size=batch_size,
                            ignore_conflicts=True,
                        )
                        batch.clear()

                if batch:
                    UniversityAdmission.objects.bulk_create(
                        batch,
                        batch_size=batch_size,
                        ignore_conflicts=True,
                    )

                after_count = UniversityAdmission.objects.count()
