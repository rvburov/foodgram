from django.db.models import Sum
from django_filters.rest_framework import DjangoFilterBackend
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from djoser.views import UserViewSet
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import SAFE_METHODS, IsAuthenticated, AllowAny
from rest_framework.response import Response

from .filters import IngredientFilter, RecipeFilter
from .paginations import PageLimitPagination
from .permissions import IsAuthorOrReadOnly
from .serializers import (
    CustomUserSerializer,
    TagSerializer,
    IngredientSerializer,
    FavoriteSerializer,
    ShoppingCartSerializer,
    SubscriptionSerializer,
    SubscriptionReadSerializer,
    RecipeReadSerializer,
    RecipeWriteSerializer
)
from recipes.models import (
    Tag,
    Ingredient,
    Recipe,
    Favorite,
    ShoppingCart,
    RecipeIngredient,
    Follow
)
from users.models import User


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    """Представление для работы с тегами."""
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (AllowAny,)
    pagination_class = None


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """Представление для работы с ингредиентами."""
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = (AllowAny,)
    filter_backends = [DjangoFilterBackend]
    filterset_class = IngredientFilter
    pagination_class = None


class CustomUserViewSet(UserViewSet):
    """Представление для пользователей."""
    queryset = User.objects.all().order_by('id')
    pagination_class = PageLimitPagination

    def get_serializer_class(self):
        """
        Возвращает класс сериализатора в зависимости от метода запроса.
        """
        if (self.request.method in SAFE_METHODS
                and self.request.user.is_authenticated):
            return CustomUserSerializer
        return super().get_serializer_class()

    def get_permissions(self):
        """
        Возвращает список прав доступа в зависимости от выполняемого действия.
        """
        if self.action in [
            'subscribe', 'subscriptions', 'destroy', 'me'
        ]:
            return [IsAuthenticated()]
        return [AllowAny()]

    @action(
        detail=True,
        methods=['post']
    )
    def subscribe(self, request, id):
        """Подписка на пользователя."""
        user = request.user
        author = get_object_or_404(User, id=id)
        if user.follower.filter(author=author).exists():
            raise ValidationError("Вы уже подписаны на этого автора")
        serializer = SubscriptionSerializer(
            data={'user': user.id, 'author': author.id},
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        Follow.objects.create(user=user, author=author)
        return Response(data=serializer.data, status=status.HTTP_201_CREATED)

    @subscribe.mapping.delete
    def delete_subscribe(self, request, id):
        """Удаление подписки на пользователя."""
        if not request.user.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        user = request.user
        author = get_object_or_404(User, id=id)
        if not user.follower.filter(author=author).exists():
            raise ValidationError("Подписка не найдена")
        subscription = get_object_or_404(Follow, user=user, author=author)
        subscription.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=['get'],
        pagination_class=PageLimitPagination
    )
    def subscriptions(self, request):
        """Список подписок текущего пользователя."""
        if not request.user.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        queryset = User.objects.filter(
            following__user=request.user
        ).order_by('id')
        pages = self.paginate_queryset(queryset)
        serializer = SubscriptionReadSerializer(
            pages, many=True, context={'request': request})
        return self.get_paginated_response(serializer.data)


class RecipeViewSet(viewsets.ModelViewSet):
    """Вьюсет для рецептов."""
    queryset = Recipe.objects.all()
    permission_classes = (IsAuthorOrReadOnly,)
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter
    pagination_class = PageLimitPagination

    def get_serializer_class(self):
        if self.request.method in SAFE_METHODS:
            return RecipeReadSerializer
        return RecipeWriteSerializer

    @action(
        detail=True, methods=['post'],
        permission_classes=[IsAuthenticated],
    )
    def favorite(self, request, pk):
        """Добавление рецепта в избранное."""
        user = request.user
        try:
            recipe = Recipe.objects.get(pk=pk)
        except Recipe.DoesNotExist:
            raise ValidationError(
                'Рецепт не найден в избранном!',
                code=status.HTTP_400_BAD_REQUEST
            )
        if user.favorites.filter(recipe=recipe).exists():
            raise ValidationError('Рецепт уже добавлен в избранное!')
        serializer = FavoriteSerializer(
            data={'user': user.pk, 'recipe': recipe.pk},
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(data=serializer.data, status=status.HTTP_201_CREATED)

    @favorite.mapping.delete
    def delete_favorite(self, request, pk):
        """Удаление рецепта из избранного."""
        if not request.user.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        recipe = get_object_or_404(Recipe, id=pk)
        if not request.user.favorites.filter(recipe=recipe).exists():
            raise ValidationError('Рецепта нет в избранном!')
        deleted_favorites = get_object_or_404(
            Favorite,
            user=request.user,
            recipe=recipe
        )
        deleted_favorites.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=['post'],
        permission_classes=[IsAuthenticated],
    )
    def shopping_cart(self, request, pk):
        """Добавление рецепта в список покупок."""
        user = request.user
        try:
            recipe = Recipe.objects.get(pk=pk)
        except Recipe.DoesNotExist:
            raise ValidationError(
                "Рецепт не найден в списоке покупок!",
                code=status.HTTP_400_BAD_REQUEST
            )
        if user.shopping_cart.filter(recipe=recipe).exists():
            raise ValidationError("Рецепт уже добавлен в списоке покупок!")
        serializer = ShoppingCartSerializer(
            data={'user': user.pk, 'recipe': recipe.pk},
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(data=serializer.data, status=status.HTTP_201_CREATED)

    @shopping_cart.mapping.delete
    def delete_shopping_cart(self, request, pk):
        """Удаление рецепта из списка покупок."""
        if not request.user.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        recipe = get_object_or_404(Recipe, id=pk)
        if not request.user.shopping_cart.filter(recipe=recipe).exists():
            raise ValidationError('Рецепта нет в списке покупок!')
        deleted_cart_item = get_object_or_404(
            ShoppingCart,
            user=request.user,
            recipe=recipe
        )
        deleted_cart_item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, permission_classes=(IsAuthenticated,))
    def download_shopping_cart(self, request):
        """Скачивание списка покупок в виде текстового файла."""
        ingredients = RecipeIngredient.objects.filter(
            recipe__shopping_cart__user=request.user
        ).order_by('ingredient__name').values(
            'ingredient__name',
            'ingredient__measurement_unit'
        ).annotate(amount=Sum('amount'))
        shopping_list = 'Список покупок:\n'
        for ingredient in ingredients:
            shopping_list += (
                f"{ingredient['ingredient__name']} "
                f"({ingredient['ingredient__measurement_unit']}) - "
                f"{ingredient['amount']}\n"
            )
        file_name = 'список_покупок.txt'
        response = HttpResponse(shopping_list, content_type='text/plain')
        response['Content-Disposition'] = f"attachment; filename='{file_name}'"
        return response
