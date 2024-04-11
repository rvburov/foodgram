from rest_framework.pagination import PageNumberPagination


class PageLimitPagination(PageNumberPagination):
    """Пагинация по количеству элементов на странице."""
    page_size_query_param = 'limit'
    page_size = 6
