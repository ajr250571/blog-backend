from unicodedata import category
from django.contrib import admin
from .models import Category, Post, Heading, PostAnalytics, CategoryAnalytics


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'title', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name', 'title', 'description', 'slug')
    list_filter = ('parent',)
    ordering = ('name',)
    readonly_fields = ('id',)


class HeadingInline(admin.TabularInline):
    model = Heading
    extra = 1
    fields = ('title', 'slug', 'level', 'order')
    prepopulated_fields = {'slug': ('title',)}
    ordering = ('order',)
    readonly_fields = ('id',)
    show_change_link = True


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'status', 'created_at', 'updated_at')
    prepopulated_fields = {'slug': ('title',)}
    search_fields = ('title', 'description', 'content', 'keywords', 'slug')
    list_filter = ('status', 'category', 'created_at', 'updated_at')
    ordering = ('-created_at',)
    readonly_fields = ('id', 'created_at', 'updated_at')
    fieldsets = (
        ('Información General', {
            "fields": (
                'title', 'description', 'content', 'thumbnail', 'keywords', 'slug', 'category'
            ),
        }),
        ('Estado y Tiempos', {
            "fields": (
                'status', 'created_at', 'updated_at'
            ),
        }),
    )
    inlines = [HeadingInline]


@admin.register(PostAnalytics)
class PostAnalyticsAdmin(admin.ModelAdmin):
    list_display = ('post_name', 'views', 'impressions', 'clicks',
                    'click_through_rate', 'avg_time_on_page')
    search_fields = ('post__title',)
    list_filter = ('post',)
    ordering = ('-post__created_at',)
    readonly_fields = ('id', 'post', 'views', 'impressions', 'clicks',
                       'click_through_rate', 'avg_time_on_page')

    def post_name(self, obj):
        return obj.post.title
    post_name.short_description = 'Post Title'


@admin.register(CategoryAnalytics)
class CategoryAnalyticsAdmin(admin.ModelAdmin):
    list_display = ('category_name', 'views', 'impressions', 'clicks',
                    'click_through_rate', 'avg_time_on_page')
    search_fields = ('category__name',)
    list_filter = ('category',)
    ordering = ('-category__created_at',)
    readonly_fields = ('id', 'category', 'views', 'impressions', 'clicks',
                       'click_through_rate', 'avg_time_on_page')

    def category_name(self, obj):
        return obj.category.name
    category_name.short_description = 'Category Name'
