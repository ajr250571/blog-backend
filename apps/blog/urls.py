from django.urls import path
from .views import (PostListView, PostDetailView, PostHeadingView, IncrementPostClicksView,
                    GenerateFakePostsView, GenerateFakeAnalyticsView, CategoryListView, IncrementCategoryClicksView, CategoryDetailView)

urlpatterns = [
    path('categories/', CategoryListView.as_view(), name='category-list'),
    path('category/', CategoryDetailView.as_view(), name='category-detail'),
    path('category/increment_clicks/',
         IncrementCategoryClicksView.as_view(), name='increment-category-click'),

    path('posts/', PostListView.as_view(), name='post-list'),
    path('post/', PostDetailView.as_view(), name='post-detail'),
    path('posts/headings/', PostHeadingView.as_view(), name='post-headings'),
    path('post/increment_clicks/',
         IncrementPostClicksView.as_view(), name='increment-post-click'),

    path('post/generate_posts/',
         GenerateFakePostsView.as_view(), name='generate-fake-posts'),
    path('post/generate_analytics/',
         GenerateFakeAnalyticsView.as_view(), name='generate-fake-analytics'),
]
