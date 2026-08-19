from django.db import models


class UniversityAdmission(models.Model):
    area = models.CharField(max_length=10)
    region = models.CharField(max_length=10)
    university = models.CharField(max_length=50)
    line = models.CharField(max_length=10)
    lesson = models.CharField(max_length=100)
    type = models.CharField(max_length=50)
    personnel = models.CharField(max_length=30)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "area",
                    "region",
                    "university",
                    "line",
                    "lesson",
                    "type",
                    "personnel",
                ],
                name="unique_university_admission",
            )
        ]

    def __str__(self):
        return f"{self.university} - {self.lesson}"