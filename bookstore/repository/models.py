from django.db import models


class StandardWord(models.Model):
    word_id = models.CharField(max_length=40, primary_key=True)
    logical_word = models.CharField(max_length=100)
    english_word = models.CharField(max_length=100)
    approved_abbreviation = models.CharField(max_length=30, blank=True)
    definition = models.TextField()
    legacy_examples = models.TextField(blank=True)

    class Meta:
        ordering = ["word_id"]

    def __str__(self):
        return f"{self.word_id}: {self.logical_word}"


class DataDomain(models.Model):
    domain_id = models.CharField(max_length=60, primary_key=True)
    description = models.TextField()
    logical_type = models.CharField(max_length=40)
    python_type = models.CharField(max_length=40)
    database_type = models.CharField(max_length=40)
    length = models.PositiveIntegerField(null=True, blank=True)
    precision = models.PositiveIntegerField(null=True, blank=True)
    scale = models.PositiveIntegerField(null=True, blank=True)
    value_nullable = models.BooleanField(default=False)
    format_rule = models.CharField(max_length=200, blank=True)
    minimum_value = models.CharField(max_length=40, blank=True)
    maximum_value = models.CharField(max_length=40, blank=True)
    allowed_values = models.JSONField(default=list, blank=True)
    examples = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["domain_id"]

    def __str__(self):
        return self.domain_id


class StandardTerm(models.Model):
    term_id = models.CharField(max_length=60, primary_key=True)
    logical_term = models.CharField(max_length=100, unique=True)
    physical_name = models.CharField(max_length=100, unique=True)
    word_ids = models.CharField(max_length=200)
    definition = models.TextField()
    domain = models.ForeignKey(
        DataDomain,
        on_delete=models.PROTECT,
        related_name="terms",
    )
    nullable = models.BooleanField(default=False)
    source_columns = models.CharField(max_length=300)

    class Meta:
        ordering = ["term_id"]

    def __str__(self):
        return f"{self.logical_term} ({self.physical_name})"