from rest_framework.exceptions import ValidationError
from rest_framework import serializers
from rest_framework.fields import SerializerMethodField

from drf_extra_fields.fields import Base64ImageField
from djoser.serializers import UserCreateSerializer, UserSerializer

from users.validators import validate_username
from users.models import User
from recipes.models import (
    Tag,
    Ingredient,
    Recipe,
    RecipeIngredient,
    Favorite,
    ShoppingCart,
    Follow
)


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор для тегов."""
    class Meta:
        model = Tag
        fields = ('id', 'name', 'color', 'slug')


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для ингредиентов."""
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class ShoppingCartSerializer(serializers.ModelSerializer):
    """Сериализатор для списка покупок."""
    class Meta:
        model = ShoppingCart
        fields = ('user', 'recipe')

    def to_representation(self, instance):
        context = {'request': self.context.get('request')}
        return RecipeShortSerializer(instance.recipe, context=context).data


class FavoriteSerializer(serializers.ModelSerializer):
    """Сериализатор для избранного."""
    class Meta:
        model = Favorite
        fields = ('user', 'recipe')

    def to_representation(self, instance):
        context = {'request': self.context.get('request')}
        return RecipeShortSerializer(instance.recipe, context=context).data


class RecipeIngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для ингредиентов рецепта."""
    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit')

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeIngredientCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания ингредиентов рецепта."""
    id = serializers.IntegerField(write_only=True)

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'amount')


class CustomUserSerializer(UserSerializer):
    """Пользовательский сериализатор пользователей."""
    is_subscribed = SerializerMethodField(required=False)

    def get_is_subscribed(self, obj):
        """
        Получение информации о том,
        подписан ли текущий пользователь на данного пользователя.
        """
        request = self.context.get('request')
        if request.user.is_authenticated:
            return Follow.objects.filter(
                user=request.user,
                author=obj
            ).exists()
        return False

    class Meta:
        model = User
        fields = (
            'email', 'id', 'username',
            'first_name', 'last_name', 'is_subscribed'
        )


class CustomUserCreateSerializer(UserCreateSerializer):
    """Сериализатор создания пользователей."""
    class Meta:
        model = User
        validators = (validate_username,)
        fields = (
            'email', 'id', 'username',
            'first_name', 'last_name', 'password',
        )


class SubscriptionSerializer(serializers.ModelSerializer):
    """Сериализатор для подписок."""
    class Meta:
        model = Follow
        fields = ('user', 'author')

    def to_representation(self, instance):
        """
        Преобразование объекта подписки в его сериализованное представление.
        """
        return SubscriptionReadSerializer(instance['author'], context={
            'request': self.context.get('request')
        }).data


class SubscriptionReadSerializer(CustomUserSerializer):
    """Сериализатор для чтения подписок."""
    recipes_count = serializers.SerializerMethodField()
    recipes = SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name',
            'last_name', 'is_subscribed', 'recipes',
            'recipes_count'
        )

    def get_recipes_count(self, obj):
        """Получение количества рецептов пользователя."""
        return obj.recipes.count()

    def get_recipes(self, obj):
        """Получение списка рецептов пользователя с учетом ограничения."""
        request = self.context.get('request')
        limit = request.GET.get('recipes_limit')
        recipes = obj.recipes.all()
        if limit:
            recipes = recipes[: int(limit)]
        serializer = RecipeShortSerializer(recipes, many=True, read_only=True)
        return serializer.data


class RecipeShortSerializer(serializers.ModelSerializer):
    """Краткий сериализатор рецептов."""
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class RecipeReadSerializer(serializers.ModelSerializer):
    """Сериализатор для чтения рецептов."""
    author = CustomUserSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    ingredients = RecipeIngredientSerializer(
        source='recipes_ingredients',
        many=True
    )
    image = Base64ImageField(read_only=True)
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = [
            'id', 'tags', 'author', 'ingredients', 'is_favorited',
            'is_in_shopping_cart', 'name', 'image', 'text', 'cooking_time',
        ]

    def get_is_favorited(self, obj):
        """Получение информации о том, добавлен ли рецепт в избранное."""
        request = self.context.get('request')
        if request.user.is_authenticated:
            return Favorite.objects.filter(
                user=request.user,
                recipe=obj
            ).exists()
        return False

    def get_is_in_shopping_cart(self, obj):
        """Получение информации о том, добавлен ли рецепт в список покупок."""
        request = self.context.get('request')
        if request.user.is_authenticated:
            return ShoppingCart.objects.filter(
                user=request.user,
                recipe=obj
            ).exists()
        return False


class RecipeWriteSerializer(serializers.ModelSerializer):
    """Сериализатор для создания и обновления рецептов."""
    author = CustomUserSerializer(read_only=True)
    tags = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Tag.objects.all()
    )
    ingredients = RecipeIngredientCreateSerializer(many=True)
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = [
            'id', 'tags', 'author', 'ingredients',
            'name', 'image', 'text', 'cooking_time'
        ]

    def create(self, validated_data):
        """Создание нового рецепта."""
        ingredients_data = validated_data.pop('ingredients')
        tags_data = validated_data.pop('tags')
        user = self.context.get('request').user
        recipe = Recipe.objects.create(author=user, **validated_data)
        recipe.tags.set(tags_data)
        for ingredient_data in ingredients_data:
            ingredient_id = ingredient_data.get('id')
            ingredient = self.get_ingredient_or_raise_404(ingredient_id)
            RecipeIngredient.objects.create(
                recipe=recipe,
                ingredient=ingredient,
                amount=ingredient_data['amount']
            )
        return recipe

    def update(self, instance, validated_data):
        """Редактирование рецепта."""
        ingredients_data = validated_data.pop('ingredients')
        tags_data = validated_data.pop('tags')
        RecipeIngredient.objects.filter(recipe=instance).delete()
        instance.tags.set(tags_data)
        for ingredient_data in ingredients_data:
            ingredient_id = ingredient_data.get('id')
            ingredient = self.get_ingredient_or_raise_404(ingredient_id)
            RecipeIngredient.objects.create(
                recipe=instance,
                ingredient=ingredient,
                amount=ingredient_data['amount']
            )
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        """Представление рецепта."""
        return RecipeReadSerializer(
            instance,
            context={'request': self.context.get('request')}
        ).data

    def get_ingredient_or_raise_404(self, ingredient_id):
        """Получение ингредиента или вызов ошибки 404."""
        try:
            return Ingredient.objects.get(pk=ingredient_id)
        except Ingredient.DoesNotExist:
            raise ValidationError(
                f'Ингредиент с идентификатором {ingredient_id} не существует.'
            )

    def validate(self, attrs):
        """Проверка данных при создании и редактировании рецепта."""
        ingredients = attrs.get('ingredients')
        tags = attrs.get('tags')
        image = attrs.get('image')
        if not self.instance and not image:
            raise ValidationError(
                {'image': 'Обязательное поле!'}
            )
        if not ingredients:
            raise ValidationError(
                {'ingredients': 'Обязательное поле!'}
            )
        if len(set(
            ingredient['id'] for ingredient in ingredients
        )) != len(ingredients):
            raise ValidationError(
                {'ingredients': 'Ингредиенты должны быть уникальными!'}
            )
        if not tags:
            raise ValidationError(
                {'tags': 'Обязательное поле!'}
            )
        if len(set(tags)) != len(tags):
            raise ValidationError(
                {'tags': 'Теги должны быть уникальными!'}
            )

        return attrs
