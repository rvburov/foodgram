from django.db import transaction
from rest_framework.exceptions import ValidationError
from rest_framework import serializers
from rest_framework.fields import SerializerMethodField
from drf_extra_fields.fields import Base64ImageField
from djoser.serializers import UserCreateSerializer, UserSerializer

from recipes.constans import MIN_VALUE, MAX_VALUE
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
    amount = serializers.IntegerField(min_value=MIN_VALUE, max_value=MAX_VALUE)

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
        request = self.context['request']
        if request.user.is_authenticated:
            return obj.following.filter(user=request.user).exists()
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

    def validate(self, value):
        """
        Проверка, что пользователь не подписывается на самого себя.
        """
        if value['author'] == value['user']:
            raise serializers.ValidationError(
                {'errors': 'Вы не можете подписаться на самого себя!'}
            )
        return value

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
        request = self.context['request']
        limit = request.GET['recipes_limit'] if 'recipes_limit' in request.GET else None
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
        request = self.context['request']
        if request.user.is_authenticated:
            return obj.favorites.filter(user=request.user).exists()
        return False

    def get_is_in_shopping_cart(self, obj):
        """Получение информации о том, добавлен ли рецепт в список покупок."""
        request = self.context['request']
        if request.user.is_authenticated:
            return obj.shopping_cart.filter(user=request.user).exists()
        return False


class RecipeWriteSerializer(serializers.ModelSerializer):
    """Сериализатор для создания и обновления рецептов."""
    author = CustomUserSerializer(read_only=True)
    tags = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Tag.objects.all()
    )
    ingredients = RecipeIngredientCreateSerializer(many=True)
    cooking_time = serializers.IntegerField(
        min_value=MIN_VALUE,
        max_value=MAX_VALUE
    )
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = [
            'id', 'tags', 'author', 'ingredients',
            'name', 'image', 'text', 'cooking_time'
        ]

    def get_ingredient_or_raise_400(self, ingredient_id):
        """Получение ингредиента или вызов ошибки 400."""
        try:
            return Ingredient.objects.get(pk=ingredient_id)
        except Ingredient.DoesNotExist:
            raise ValidationError(
                f'Ингредиент с идентификатором {ingredient_id} не существует.',
                code='invalid'
            )
        
    def process_ingredients_data(self, instance, ingredients_data):
        """Обработка данных об ингредиентах."""
        ingredients_to_create = []
        for ingredient_data in ingredients_data:
            ingredient_id = ingredient_data.get('id')
            ingredient = self.get_ingredient_or_raise_400(ingredient_id)
            ingredients_to_create.append(
                RecipeIngredient(
                    recipe=instance,
                    ingredient=ingredient,
                    amount=ingredient_data['amount']
                )
            )
        RecipeIngredient.objects.bulk_create(ingredients_to_create)

    def create(self, validated_data):
        """Создание нового рецепта."""
        ingredients_data = validated_data.pop('ingredients')
        tags_data = validated_data.pop('tags')
        user = self.context['request'].user
        with transaction.atomic():
            recipe = Recipe.objects.create(author=user, **validated_data)
            recipe.tags.set(tags_data)
            self.process_ingredients_data(recipe, ingredients_data)
        return recipe

    def update(self, instance, validated_data):
        """Редактирование рецепта."""
        ingredients_data = validated_data.pop('ingredients')
        tags_data = validated_data.pop('tags')
        with transaction.atomic():
            instance.recipes_ingredients.all().delete()
            instance.tags.set(tags_data)
            self.process_ingredients_data(instance, ingredients_data)
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        """Представление рецепта."""
        return RecipeReadSerializer(
            instance,
            context={'request': self.context.get('request')}
        ).data

    def validate(self, attrs):
        """Проверка данных при создании и редактировании рецепта."""
        ingredients = attrs.get('ingredients')
        tags = attrs.get('tags')
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

    def validate_image(self, value):
        if not value:
            raise serializers.ValidationError(
                {'image': 'Обязательное поле!'}
            )
        return value
