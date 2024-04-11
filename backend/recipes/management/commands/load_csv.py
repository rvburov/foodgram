import csv
import os

from django.conf import settings
from django.core.management.base import BaseCommand

from recipes.models import Ingredient


class Command(BaseCommand):
    help = 'Выгружаем ингредиенты в БД'

    def handle(self, *args, **options):
        file_path = os.path.join(settings.BASE_DIR, 'data', 'ingredients.csv')
        ingredients_to_create = []
        with open(file_path, 'r', encoding='utf-8') as file:
            reader = csv.reader(file)
            for row in reader:
                name, measurement_unit = row
                if not Ingredient.objects.filter(
                    name=name,
                    measurement_unit=measurement_unit
                ).exists():
                    ingredient = Ingredient(
                        name=name,
                        measurement_unit=measurement_unit
                    )
                    ingredients_to_create.append(ingredient)

        Ingredient.objects.bulk_create(ingredients_to_create)
        self.stdout.write(
            self.style.SUCCESS('Ингредиенты успешно добавлены в БД'))
