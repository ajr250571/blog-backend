from celery import shared_task
import logging
from .models import PostAnalytics, CategoryAnalytics, Post, Category
import redis
from django.conf import settings

logger = logging.getLogger(__name__)

redis_client = redis.StrictRedis(host=settings.REDIS_HOST, port=6379, db=0)


@shared_task
def increment_post_impressions(post_id):
    try:
        analytics, created = PostAnalytics.objects.get_or_create(
            post__id=post_id)
        analytics.increment_impressions()
        logger.info(
            f"Incremented impressions for post {post_id}. Total impressions: {analytics.impressions}")
    except Exception as e:
        logger.error(f"Error incrementing impressions for post {post_id}: {e}")


@shared_task
def sync_impressions_to_db():
    try:
        keys = redis_client.keys('post:impressions:*')
        for key in keys:
            post_id = key.decode().split(':')[-1]
            # validamos que el post existe
            if not Post.objects.filter(post__id=post_id).exists():
                logger.info(
                    f"Post {post_id} not found. Skipping synchronization.")
                continue
            impressions = int(redis_client.get(key))
            if impressions > 0:
                analytics, _ = PostAnalytics.objects.get_or_create(
                    post__id=post_id)
                analytics.impressions += impressions
                analytics._update_ctr()
                analytics.save()
                redis_client.delete(key)
                logger.info(
                    f"Synchronized {impressions} impressions for post {post_id} to database.")
    except Exception as e:
        logger.error(f"Error synchronizing impressions to database: {e}")


@shared_task
def sync_category_impressions_to_db():
    # Sincroniza las impresiones almacenadas en Redis a la base de datos
    try:
        keys = redis_client.keys('category:impressions:*')
        for key in keys:
            category_id = key.decode().split(':')[-1]
            # validamos que la categoria existe
            if not Category.objects.filter(category__id=category_id).exists():
                logger.info(
                    f"Category {category_id} not found. Skipping synchronization."
                )
                continue
            impressions = int(redis_client.get(key))
            if impressions > 0:
                analytics, _ = CategoryAnalytics.objects.get_or_create(
                    category__id=category_id)
                analytics.impressions += impressions
                analytics._update_ctr()
                analytics.save()
                logger.info(
                    f"Synchronized {impressions} impressions for category {category_id} to database.")
            else:
                logger.info(
                    f"No impressions found for category {category_id}.")
            redis_client.delete(key)
    except Exception as e:
        logger.error(
            f"Error synchronizing category impressions to database: {e}")


@shared_task
def increment_post_views(slug, ip_address):
    try:
        analytics = PostAnalytics.objects.get(post__slug=slug)
        analytics.increment_views(ip_address)
        logger.info(
            f"Incremented views for post {slug}. Total views: {analytics.views}")
    except PostAnalytics.DoesNotExist:
        logger.error(f"PostAnalytics does not exist for post {slug}")
    except Exception as e:
        logger.error(f"Error incrementing views for post {slug}: {e}")
