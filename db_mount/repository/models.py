from django.db import models



class OrmItem(models.Model):
    name = models.CharField(max_length=50)

    class Meta:
        db_table = "orm_item"