# imports
from django.db import models
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
import uuid

from django.utils.text import slugify
from ckeditor.fields import RichTextField


def blog_thumbnail_directory(instance, filename):
    return 'blog/{0}/{1}'.format(instance.title, filename)


def category_thumbnail_directory(instance, filename):
    return 'blog_categories/{0}/{1}'.format(instance.name, filename)


class Category(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    name = models.CharField(max_length=255)
    title = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    thumbnail = models.ImageField(
        upload_to=category_thumbnail_directory, null=True, blank=True)
    slug = models.SlugField(unique=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class CategoryView(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name='category_view')
    ip_address = models.GenericIPAddressField()
    timestamp = models.DateTimeField(auto_now_add=True)


class CategoryAnalytics(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name='category_analytics')
    views = models.PositiveIntegerField(default=0)
    impressions = models.PositiveIntegerField(default=0)
    clicks = models.PositiveIntegerField(default=0)
    click_through_rate = models.FloatField(default=0.0)
    avg_time_on_page = models.FloatField(default=0.0)

    def increment_clicks(self):
        self.clicks += 1
        self._update_ctr()
        self.save()

    def increment_impressions(self):
        self.impressions += 1
        self._update_ctr()
        self.save()

    def _update_ctr(self):
        if self.impressions > 0:
            self.click_through_rate = round(
                (self.clicks / self.impressions) * 100, 2)
        else:
            self.click_through_rate = 0.0
        self.save()

    def increment_views(self, ip_address):
        if not CategoryView.objects.filter(category=self.category, ip_address=ip_address).exists():
            CategoryView.objects.create(
                category=self.category, ip_address=ip_address)
            self.views += 1
            self.save()


class Post(models.Model):
    class PostObjects(models.Manager):
        def get_queryset(self) -> models.QuerySet:
            return super().get_queryset().filter(status='published')

    status_options = (
        ('draft', 'Draft'),
        ('published', 'Published'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=128)
    description = models.CharField(max_length=256, blank=True, null=True)
    content = RichTextField()
    thumbnail = models.ImageField(
        upload_to=blog_thumbnail_directory, null=True, blank=True)
    keywords = models.CharField(max_length=256, null=True, blank=True)
    slug = models.SlugField(unique=True)
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name='posts')

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    status = models.CharField(
        max_length=10, choices=status_options, default='draft')

    objects = models.Manager()  # The default manager.
    postobjects = PostObjects()  # Our custom manager.

    class Meta:
        ordering = ['status', '-created_at']

    def __str__(self):
        return self.title


class PostAnalytics(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.OneToOneField(
        Post, on_delete=models.CASCADE, related_name='post_analytics')
    views = models.PositiveIntegerField(default=0)
    impressions = models.PositiveIntegerField(default=0)
    clicks = models.PositiveIntegerField(default=0)
    click_through_rate = models.FloatField(default=0.0)
    avg_time_on_page = models.FloatField(default=0.0)  # in seconds

    def increment_clicks(self):
        self.clicks += 1
        self._update_ctr()
        self.save()

    def _update_ctr(self):
        if self.impressions > 0:
            self.click_through_rate = round(
                (self.clicks / self.impressions) * 100, 2)
        else:
            self.click_through_rate = 0.0
        self.save()

    def increment_impressions(self):
        self.impressions += 1
        self._update_ctr()
        self.save()

    def increment_views(self, ip_address):

        if not PostView.objects.filter(post=self.post, ip_address=ip_address).exists():
            PostView.objects.create(post=self.post, ip_address=ip_address)
            self.views += 1
            self.save()

    def __str__(self):
        return f"Analytics for {self.post.title}"


class Heading(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.ForeignKey(
        Post, on_delete=models.CASCADE, related_name='headings')
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    level = models.PositiveSmallIntegerField(
        choices=[(i, f'H{i}') for i in range(1, 6)], default=1)
    order = models.PositiveIntegerField()

    class Meta:
        ordering = ['order']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.post.title} - {self.title}"


class PostView(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.ForeignKey(
        Post, on_delete=models.CASCADE, related_name='post_view')
    ip_address = models.GenericIPAddressField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"View of {self.post.title} from {self.ip_address} at {self.timestamp}"


@receiver(post_save, sender=Post)
def create_post_analytics(sender, instance, created, **kwargs):
    if created:
        PostAnalytics.objects.create(post=instance)


@receiver(post_save, sender=Category)
def create_category_analytics(sender, instance, created, **kwargs):
    if created:
        CategoryAnalytics.objects.create(category=instance)
