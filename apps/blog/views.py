# imports go here
from re import search
from django.conf import settings
from django.utils.decorators import method_decorator
from django.utils.text import slugify
from django.views.decorators.cache import cache_page
from django.core.cache import cache
from django.db.models import Q, F, Prefetch

from rest_framework.exceptions import NotFound, APIException
from rest_framework_api.views import StandardAPIView

from .models import Post, Category, Heading, PostAnalytics, CategoryAnalytics
from .serializers import PostSerializer, PostListSerializer, HeadingSerializer, CategoryListSerializer, CategorySerializer
from .utils import get_client_ip
from .tasks import increment_post_views
from core.permissions import HasValidAPIKey
from faker import Faker

import logging
import random
import uuid
import redis

# logger
logger = logging.getLogger(__name__)
# redis
redis_client = redis.StrictRedis(host=settings.REDIS_HOST, port=6379, db=0)
# cache timeout
cache_timeout = settings.CACHE_TIMEOUT  # Cache timeout in seconds


class CategoryListView(StandardAPIView):
    permission_classes = [HasValidAPIKey]

    # @method_decorator(cache_page(cache_timeout))
    def get(self, request, *args, **kwargs):
        # params
        parent_slug = request.query_params.get('parent_slug', None)
        search = request.query_params.get('search', None)
        sorting = request.query_params.get('sorting', None)
        ordering = request.query_params.get('ordering', None)
        page = request.query_params.get('p', '1')
        print(ordering)
        try:
            cache_key = f'category_list_{page}_{search}__{sorting}_{ordering}_{parent_slug}'
            cached_categories = cache.get(cache_key)
            if cached_categories:
                categories = cached_categories
            else:
                if parent_slug:
                    categories = Category.objects.filter(parent__slug=parent_slug).prefetch_related(
                        Prefetch(
                            'category_analytics', to_attr='analytics_cache'
                        )
                    )
                else:
                    categories = Category.objects.filter(parent__isnull=True).prefetch_related(
                        Prefetch(
                            'category_analytics', to_attr='analytics_cache'
                        )
                    )
                if search:
                    categories = categories.filter(
                        Q(name__icontains=search) |
                        Q(title__icontains=search) |
                        Q(description__icontains=search)
                    )
                if sorting:
                    if sorting == 'newest':
                        categories = categories.order_by('-created_at')
                    elif sorting == 'recently_updated':
                        categories = categories.order_by('-updated_at')
                    elif sorting == 'most_viewed':
                        posts = categories.annotate(popularity=F(
                            'analytics_cache__views')).order_by('-popularity')
                if ordering:
                    categories = categories.order_by(ordering)

                cache.set(cache_key, categories, timeout=cache_timeout)
        except Category.DoesNotExist:
            raise NotFound("Categories not found.")
        except Exception as e:
            raise APIException(
                f"An error occurred while retrieving categories. {str(e)}")

        # Increment impressions for each post asynchronously in redis
        for category in categories:
            redis_client.incr(f'category:impressions:{category.id}')

        serializer = CategoryListSerializer(categories, many=True)
        return self.paginate(request, serializer.data)


class CategoryDetailView(StandardAPIView):
    permission_classes = [HasValidAPIKey]

    def get(self, request, *args, **kwargs):
        slug = request.query_params.get('slug', None)
        page = request.query_params.get('p', '1')
        if not slug:
            return self.error("Category slug is required.")
        try:
            cache_key = f'category_detail_{slug}_{page}'
            cached_category = cache.get(cache_key)
            if cached_category:
                category = cached_category
            else:
                category = Category.objects.get(slug=slug)
                cache.set(cache_key, category, timeout=cache_timeout)

        except Category.DoesNotExist:
            return self.error("Category slug not found.")
        except Exception as e:
            return self.error(
                f"An error occurred while retrieving the category. {str(e)}"
            )

        serializer = CategorySerializer(category)
        return self.response(serializer.data)


class IncrementCategoryClicksView(StandardAPIView):
    permission_classes = [HasValidAPIKey]

    def post(self, request):
        data = request.data
        slug = data.get('slug', None)

        if not slug:
            raise NotFound("Category slug is required.")
        try:
            category = Category.objects.get(slug=slug)
        except Category.DoesNotExist:
            raise NotFound("Category not found.")
        except Exception as e:
            raise APIException(
                f"An error occurred while retrieving the category. {str(e)}")

        try:
            category_analytics, _ = CategoryAnalytics.objects.get_or_create(
                category=category)
            category_analytics.increment_clicks()
        except CategoryAnalytics.DoesNotExist:
            raise NotFound("Category analytics not found.")

        return self.response({
            "message": "Click count incremented.",
            "clicks": category_analytics.clicks
        })


class PostListView(StandardAPIView):
    permission_classes = [HasValidAPIKey]
    # @method_decorator(cache_page(60*1))  # Cache the view for 1 minutes

    def get(self, request, *args, **kwargs):
        # parametros
        search = request.query_params.get('search', None)
        sorting = request.query_params.get('sorting', None)
        ordering = request.query_params.get('ordering', None)
        categories = request.query_params.getlist('category', [])
        page = request.query_params.get('p', '1')

        try:
            cache_key = f'post_list_{search}_{sorting}_{ordering}_{categories}_{page}'
            cached_posts = cache.get(cache_key)
            if cached_posts:
                posts = cached_posts
            else:
                # consulta inicial optimizada
                posts = Post.postobjects.all().select_related('category').prefetch_related(
                    Prefetch(
                        'post_analytics', to_attr='analytics_cache'
                    ))
                if search:
                    posts = posts.filter(
                        Q(title__icontains=search) |
                        Q(description__icontains=search) |
                        Q(content__icontains=search)
                    )
                if categories:
                    category_queries = Q()
                    for category in categories:
                        try:
                            uuid.UUID(category)
                            category_queries |= Q(category__id=category)
                        except ValueError:
                            category_queries |= Q(category__slug=category)
                    posts = posts.filter(category_queries)
                # Sort posts based on sorting parameter
                if sorting:
                    if sorting == 'newest':
                        posts = posts.order_by('-created_at')
                    elif sorting == 'recently_updated':
                        posts = posts.order_by('-updated_at')
                    elif sorting == 'most_viewed':
                        posts = posts.annotate(popularity=F(
                            'analytics_cache__views')).order_by('-popularity')
                # Apply ordering if provided
                if ordering:
                    posts = posts.order_by(ordering)

                # Cache for 1 minute
                cache.set(cache_key, posts, timeout=cache_timeout)

        except Post.DoesNotExist:
            raise NotFound("No posts found.")
        except Exception as e:
            raise APIException(
                f"An error occurred while retrieving posts. {str(e)}")

        # Increment impressions for each post asynchronously
        for post in posts:
            # increment_post_impressions.delay(post.id)
            redis_client.incr(f'post:impressions:{post.id}')

        serializer = PostListSerializer(posts, many=True)
        return self.paginate(request, serializer.data)


class PostDetailView(StandardAPIView):
    permission_classes = [HasValidAPIKey]

    def get(self, request, *args, **kwargs):
        ip_address = get_client_ip(request)
        slug = request.query_params.get('slug', None)
        if not slug:
            return self.error("Post slug is required.")
        try:
            cached_posts = cache.get(f'post_detail_{slug}')
            if cached_posts:
                post = cached_posts
            else:
                post = Post.postobjects.get(slug=slug)
                cache.set(f'post_detail_{slug}', post, timeout=cache_timeout)

        except Post.DoesNotExist:
            return self.error("Post not found.")
        except Exception as e:
            return self.error(
                f"An error occurred while retrieving the post. {str(e)}"
            )

        # Increment views asynchronously
        increment_post_views.delay(post.slug, ip_address)

        # Increment views
        # try:
        #     post_analytics = PostAnalytics.objects.get(post=post)
        #     post_analytics.increment_views(request)
        # except PostAnalytics.DoesNotExist:
        #     raise NotFound("Post analytics not found.")
        # except Exception as e:
        #     raise APIException(
        #         f"An error occurred while updating post analytics. {str(e)}")

        serializer = PostSerializer(post)
        return self.response(serializer.data)


class PostHeadingView(StandardAPIView):
    permission_classes = [HasValidAPIKey]

    # Cache the view for 1 minutes
    @method_decorator(cache_page(cache_timeout))
    def get(self, request, *args, **kwargs):
        slug = request.query_params.get('slug', None)
        if not slug:
            raise NotFound("Post slug is required.")
        try:
            post = Post.postobjects.get(slug=slug)
        except Post.DoesNotExist:
            raise NotFound("Post not found.")
        except Exception as e:
            raise APIException(
                f"An error occurred while retrieving the post. {str(e)}")

        headings = Heading.objects.filter(post=post).order_by('order')
        serializer = HeadingSerializer(headings, many=True)
        return self.response(serializer.data)


class IncrementPostClicksView(StandardAPIView):
    permission_classes = [HasValidAPIKey]

    def post(self, request):
        data = request.data
        slug = data.get('slug', None)

        if not slug:
            raise NotFound("Post slug is required.")
        try:
            post = Post.postobjects.get(slug=slug)
        except Post.DoesNotExist:
            raise NotFound("Post not found.")
        except Exception as e:
            raise APIException(
                f"An error occurred while retrieving the post. {str(e)}")

        try:
            post_analytics, created = PostAnalytics.objects.get_or_create(
                post=post)
            post_analytics.increment_clicks()
        except PostAnalytics.DoesNotExist:
            raise NotFound("Post analytics not found.")
        except Exception as e:
            raise APIException(
                f"An error occurred while updating post analytics. {str(e)}")

        return self.response({
            "message": "Click count incremented.",
            "clicks": post_analytics.clicks,
        })


class GenerateFakePostsView(StandardAPIView):

    def get(self, request):
        # Elimina todos los posts analytics existentes
        PostAnalytics.objects.all().delete()

        # Elimina todos los posts existentes
        Post.objects.all().delete()

        # Elimina todas las categorías existentes
        Category.objects.all().delete()

        # Crea nuevas categorías sobre programacion
        categories_create = [
            "Programacion",
            "Tecnologia",
            "Deportes",
            "Ciencia",
            "Cultura",
            "Vida",
            "Viajes",
            "Negocios",
            "Finanzas",
            "Salud",
            "Politica",
            "Economia",
            "Educacion",
        ]
        for category in categories_create:
            Category.objects.create(
                name=category,
                title=category,
                slug=slugify(category),
            )

        fake = Faker()
        status_options = ['draft', 'published']
        categories = list(Category.objects.all())
        posts_to_generate = 100
        for _ in range(posts_to_generate):
            title = fake.sentence(nb_words=6)
            Post.objects.create(
                title=title,
                description=fake.sentence(nb_words=12),
                content=fake.paragraph(nb_sentences=5),
                category=random.choice(categories),
                status=random.choice(status_options),
                slug=fake.slug(),
                keywords="test,post,unit",
            )

        return self.response({"message": "Fake posts generated."})


class GenerateFakeAnalyticsView(StandardAPIView):

    def get(self, request):
        # Elimina todos los posts analytics existentes
        PostAnalytics.objects.all().delete()

        # Crea nuevos posts analytics
        posts = Post.objects.all()
        for post in posts:
            views = random.randint(1, 100)
            impressions = views+random.randint(1, 100)
            clicks = random.randint(1, views)
            analytics = PostAnalytics.objects.create(
                post=post,
                views=views,
                impressions=impressions,
                clicks=clicks,
                avg_time_on_page=round(random.uniform(10, 300), 2),
            )
            analytics._update_ctr()
        return self.response({"message": "Fake analytics generated."})
