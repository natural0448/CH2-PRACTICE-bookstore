import csv
import json
from pathlib import Path

import yaml
from django.conf import settings
from django.shortcuts import render
from django.http import HttpResponse

def read_csv(path):
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def day2_dashboard(request):
    data_dir = Path(settings.BASE_DIR) / "bookstore-standard" / "day2"

    words = read_csv(data_dir / "standard-words.csv")
    terms = read_csv(data_dir / "standard-terms.csv")

    with (data_dir / "data-domains.yaml").open(encoding="utf-8") as file:
        domains = yaml.safe_load(file)["domains"]

    with (data_dir / "day2-validation.json").open(encoding="utf-8") as file:
        validation = json.load(file)

    unit_price = next(
        (term for term in terms if term["term_id"] == "UNIT_PRICE"),
        None,
    )

    context = {
        "validation": validation,
        "counts": {
            "words": len(words),
            "domains": len(domains),
            "terms": len(terms),
        },
        "terms": terms,
        "domains": domains,
        "unit_price": unit_price,
    }
    return render(request, "day2_dashboard.html", context)