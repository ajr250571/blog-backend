import keyword
from pydoc import cli
from turtle import title
from unittest.mock import patch
import click
from django.test import TestCase
from django.urls import reverse
from .models import Category, Post, PostAnalytics, Heading
from rest_framework.test import APIClient
from django.conf import settings
from django.core.cache import cache


class CategoryModelTest(TestCase):
    def setUp(self):
        self.category = Category.objects.create(
            name="Test Category",
            title="A category for testing",
            description="This category is used for unit testing purposes.",
            slug="test-category"
        )
        cache.clear()

    def tearDown(self) -> None:
        cache.clear()

    def test_category_creation(self):
        category = self.category
        self.assertEqual(category.name, "Test Category")
        self.assertEqual(category.title, "A category for testing")
        self.assertEqual(category.description,
                         "This category is used for unit testing purposes.")
        self.assertEqual(category.slug, "test-category")
        self.assertIsNotNone(category.id)


class PostModelTest(TestCase):
    def setUp(self):
        self.category = Category.objects.create(
            name="Test Category",
            title="A category for testing",
            description="This category is used for unit testing purposes.",
            slug="test-category"
        )
        self.post = Post.objects.create(
            title="Test Post",
            description="This is a test post description.",
            content="This is a test post content.",
            keywords="test,post,unit",
            slug="test-post",
            category=self.category,
            status="published"
        )
        cache.clear()

    def tearDown(self) -> None:
        cache.clear()

    def test_post_creation(self):
        post = self.post
        self.assertEqual(post.title, "Test Post")
        self.assertEqual(post.description, "This is a test post description.")
        self.assertEqual(post.content, "This is a test post content.")
        self.assertEqual(post.keywords, "test,post,unit")
        self.assertEqual(post.slug, "test-post")
        self.assertEqual(post.category, self.category)
        self.assertEqual(post.status, "published")
        self.assertIsNotNone(post.id)

    def test_post_published_manager(self):
        published_posts = Post.postobjects.all()
        self.assertIn(self.post, published_posts)
        self.assertEqual(published_posts.count(), 1)


class PostAnalyticsModelTest(TestCase):
    def setUp(self):
        self.category = Category.objects.create(
            name="Test Category",
            title="A category for testing",
            description="This category is used for unit testing purposes.",
            slug="test-category"
        )
        self.post = Post.objects.create(
            title="Test Post",
            description="This is a test post description.",
            content="This is a test post content.",
            keywords="test,post,unit",
            slug="test-post",
            category=self.category,
            status="published"
        )
        self.analytics = PostAnalytics.objects.create(post=self.post)
        cache.clear()

    def tearDown(self) -> None:
        cache.clear()

    def test_post_analytics_creation(self):
        analytics = self.analytics
        self.assertEqual(analytics.post, self.post)
        self.assertEqual(analytics.impressions, 0)
        self.assertEqual(analytics.views, 0)
        self.assertEqual(analytics.clicks, 0)
        self.assertEqual(analytics.click_through_rate, 0.0)
        self.assertIsNotNone(analytics.id)

    def test_ctr(self):
        analytics = self.analytics
        analytics.increment_impressions()  # Ensure there's at least one impression
        analytics.increment_clicks()
        self.assertEqual(analytics.clicks, 1)
        self.assertEqual(analytics.impressions, 1)
        self.assertEqual(analytics.click_through_rate, 100.0)


class HeadingModelTest(TestCase):
    def setUp(self):
        self.category = Category.objects.create(
            name="Test Category",
            title="A category for testing",
            description="This category is used for unit testing purposes.",
            slug="test-category"
        )
        self.post = Post.objects.create(
            title="Test Post",
            description="This is a test post description.",
            content="This is a test post content.",
            keywords="test,post,unit",
            slug="test-post",
            category=self.category,
            status="published"
        )
        self.heading = Heading.objects.create(
            post=self.post,
            title="Test Heading",
            level=1,
            order=1,
            slug="test-heading"
        )
        cache.clear()

    def tearDown(self) -> None:
        cache.clear()

    def test_heading_creation(self):
        heading = self.heading
        self.assertEqual(heading.post, self.post)
        self.assertEqual(heading.title, "Test Heading")
        self.assertEqual(heading.level, 1)
        self.assertEqual(heading.order, 1)
        self.assertEqual(heading.slug, "test-heading")
        self.assertIsNotNone(heading.id)

# Views tests


class PostListViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.api_key = settings.VALID_API_KEYS[0]

        self.category = Category.objects.create(
            name="Test Category",
            title="A category for testing",
            description="This category is used for unit testing purposes.",
            slug="test-category"
        )
        self.post = Post.objects.create(
            title="Test Post 1",
            description="This is a test post description.",
            content="This is a test post content.",
            keywords="test,post,unit",
            slug="test-post-1",
            category=self.category,
            status="published"
        )
        cache.clear()

    def tearDown(self) -> None:
        cache.clear()

    def test_get_published_posts(self):
        url = reverse('post-list')
        response = self.client.get(
            url,
            HTTP_API_KEY=self.api_key
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['status'], 200)
        self.assertIn('results', data)
        self.assertEqual(len(data['results']), 1)
        results = data['results'][0]
        self.assertEqual(results['title'], self.post.title)
        self.assertEqual(results['description'], self.post.description)
        self.assertEqual(results['slug'], self.post.slug)


class PostDetailViewTest(TestCase):
    def setUp(self) -> None:

        self.client = APIClient()
        self.api_key = settings.VALID_API_KEYS[0]

        self.category = Category.objects.create(
            name="Test Category",
            title="A category for testing",
            description="This category is used for unit testing purposes.",
            slug="test-category"
        )
        self.post = Post.objects.create(
            title="Test Post 1",
            description="This is a test post description.",
            content="This is a test post content.",
            keywords="test,post,unit",
            slug="test-post-1",
            category=self.category,
            status="published"
        )
        self.heading1 = Heading.objects.create(
            post=self.post,
            title="Test Heading 1",
            level=1,
            order=1,
            slug="test-heading-1"
        )
        self.heading2 = Heading.objects.create(
            post=self.post,
            title="Test Heading 2",
            level=2,
            order=2,
            slug="test-heading-2"
        )
        cache.clear()

    def tearDown(self) -> None:
        cache.clear()

    @patch('apps.blog.tasks.increment_post_views.delay')
    def test_get_post_detail_success(self, moch_increment_views):
        url = reverse('post-detail') + f'?slug={self.post.slug}'
        response = self.client.get(
            url,
            HTTP_API_KEY=self.api_key
        )
        self.assertEqual(response.status_code, 200)

        data = response.json()
        # print(data)

        self.assertIn('success', data)
        self.assertTrue(data['success'])
        self.assertIn('status', data)
        self.assertEqual(data['status'], 200)
        self.assertIn('results', data)

        post_data = data['results']
        # print(post_data)
        self.assertEqual(post_data['title'], self.post.title)
        self.assertEqual(post_data['description'], self.post.description)
        self.assertEqual(post_data['slug'], self.post.slug)

        category_data = post_data['category']
        # print(category_data)
        self.assertEqual(category_data['name'], self.category.name)
        self.assertEqual(category_data['slug'], self.category.slug)

        moch_increment_views.assert_called_once_with(
            self.post.slug, '127.0.0.1')

        headings_data = post_data['headings']
        # print(headings_data)
        self.assertEqual(len(headings_data), 2)
        self.assertEqual(headings_data[0]['title'], self.heading1.title)
        self.assertEqual(headings_data[0]['level'], self.heading1.level)
        self.assertEqual(headings_data[0]['order'], self.heading1.order)
        self.assertEqual(headings_data[0]['slug'], self.heading1.slug)

        self.assertEqual(headings_data[1]['title'], self.heading2.title)
        self.assertEqual(headings_data[1]['level'], self.heading2.level)
        self.assertEqual(headings_data[1]['order'], self.heading2.order)
        self.assertEqual(headings_data[1]['slug'], self.heading2.slug)


class PostHeadingsViewTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.api_key = settings.VALID_API_KEYS[0]

        self.category = Category.objects.create(
            name="Test Category",
            title="A category for testing",
            description="This category is used for unit testing purposes.",
            slug="test-category"
        )
        self.post = Post.objects.create(
            title="Test Post 1",
            description="This is a test post description.",
            content="This is a test post content.",
            keywords="test,post,unit",
            slug="test-post-1",
            category=self.category,
            status="published"
        )
        self.heading1 = Heading.objects.create(
            post=self.post,
            title="Test Heading 1",
            level=1,
            order=1,
            slug="test-heading-1"
        )
        self.heading2 = Heading.objects.create(
            post=self.post,
            title="Test Heading 2",
            level=2,
            order=2,
            slug="test-heading-2"
        )
        cache.clear()

    def tearDown(self) -> None:
        cache.clear()

    def test_get_post_headings_success(self):
        url = reverse('post-headings') + f'?slug={self.post.slug}'
        response = self.client.get(
            url,
            HTTP_API_KEY=self.api_key
        )
        self.assertEqual(response.status_code, 200)

        data = response.json()
        # print(data)

        self.assertIn('success', data)
        self.assertTrue(data['success'])
        self.assertIn('status', data)
        self.assertEqual(data['status'], 200)
        self.assertIn('results', data)

        headings_data = data['results']
        # print(headings_data)
        self.assertEqual(len(headings_data), 2)
        self.assertEqual(headings_data[0]['title'], self.heading1.title)
        self.assertEqual(headings_data[0]['level'], self.heading1.level)
        self.assertEqual(headings_data[0]['order'], self.heading1.order)

        self.assertEqual(headings_data[1]['title'], self.heading2.title)
        self.assertEqual(headings_data[1]['level'], self.heading2.level)
        self.assertEqual(headings_data[1]['order'], self.heading2.order)


class IncrementPostClickViewTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.api_key = settings.VALID_API_KEYS[0]

        self.category = Category.objects.create(
            name="Test Category",
            title="A category for testing",
            description="This category is used for unit testing purposes.",
            slug="test-category"
        )
        self.post = Post.objects.create(
            title="Test Post 1",
            description="This is a test post description.",
            content="This is a test post content.",
            keywords="test,post,unit",
            slug="test-post-1",
            category=self.category,
            status="published"
        )
        cache.clear()

    def tearDown(self) -> None:
        cache.clear()

    def test_increment_post_clicks_success(self):
        url = reverse('increment-post-click')
        response = self.client.post(
            url,
            {"slug": self.post.slug},
            HTTP_API_KEY=self.api_key,
            format='json'
        )

        data = response.json()
        print(data)

        self.assertIn('success', data)
        self.assertTrue(data['success'])
        self.assertIn('status', data)
        self.assertEqual(data['status'], 200)
        self.assertIn('results', data)

        results = data['results']
        self.assertIn('clicks', results)
        self.assertEqual(results['clicks'], 1)

        from apps.blog.models import PostAnalytics
        analytics = PostAnalytics.objects.get(post=self.post)
        self.assertEqual(analytics.clicks, 1)
