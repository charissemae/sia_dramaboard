from django.contrib import admin

from .models import Drama, Rating


@admin.register(Drama)
class DramaAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "genre",
        "country",
        "release_year",
        "is_featured",
        "posted_by",
        "date_added",
    )
    list_filter = ("genre", "country", "release_year", "is_featured")
    search_fields = ("title", "genre", "country", "posted_by__username")
    raw_id_fields = ("posted_by",)


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ("drama", "user", "score", "updated_at")
    list_filter = ("score",)
    search_fields = ("drama__title", "user__username")
    raw_id_fields = ("drama", "user")
