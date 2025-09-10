from django.db import models
from django.utils import timezone
import uuid
from django.utils.text import slugify


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

    def __str__(self):
        return self.name


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
    description = models.CharField(max_length=256)
    content = models.TextField()
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


class Heading(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.ForeignKey(
        Post, on_delete=models.PROTECT, related_name='headings')
    title = models.CharField(max_length=255)
    slug = models.SlugField()
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
