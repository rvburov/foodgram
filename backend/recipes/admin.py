from django.contrib import admin

from recipes.models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                            ShoppingCart, Tag, Follow)

MIN_RECIPE_ADMIN = 1


class IngredientAdmin(admin.ModelAdmin):
    """Администратор модели Ингредиент."""
    list_display = ('id', 'name', 'measurement_unit',)
    list_filter = ('name', )


class TagAdmin(admin.ModelAdmin):
    """Администратор модели Тег."""
    list_display = ('name', 'color', 'slug',)
    search_fields = ('name',)


class RecipeIngredientAdmin(admin.ModelAdmin):
    """Администратор модели Ингредиент рецепта."""
    list_display = ('ingredient', 'amount', 'recipe',)
    search_fields = ('recipe__name', 'ingredient__name',)
    list_filter = ('ingredient__name',)


class RecipeIngredientInline(admin.TabularInline):
    """Встраиваемый администратор модели Ингредиент рецепта."""
    model = RecipeIngredient
    min_num = MIN_RECIPE_ADMIN


class RecipeAdmin(admin.ModelAdmin):
    """Администратор модели Рецепт."""
    list_display = ('name', 'author', 'in_favorites',)
    readonly_fields = ('in_favorites',)
    list_filter = ('author', 'name', 'tags',)
    inlines = [RecipeIngredientInline]

    def in_favorites(self, obj):
        return Favorite.objects.filter(recipe=obj).count()

    in_favorites.short_description = 'Добавлений в избранное'


class ShoppingCartAdmin(admin.ModelAdmin):
    """Администратор модели Список покупок."""
    list_display = ('user', 'recipe',)


class FavoriteAdmin(admin.ModelAdmin):
    """Администратор модели Избранное."""
    list_display = ('user', 'recipe',)


class FollowAdmin(admin.ModelAdmin):
    """Администратор модели Подписка на автора."""
    list_display = ('user', 'author',)


admin.site.register(Favorite, FavoriteAdmin)
admin.site.register(Ingredient, IngredientAdmin)
admin.site.register(Recipe, RecipeAdmin)
admin.site.register(ShoppingCart, ShoppingCartAdmin)
admin.site.register(Tag, TagAdmin)
admin.site.register(RecipeIngredient, RecipeIngredientAdmin)
admin.site.register(Follow, FollowAdmin)
