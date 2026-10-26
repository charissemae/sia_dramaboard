from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse


class Drama(models.Model):
    title = models.CharField(max_length=200)
    genre = models.CharField(max_length=100)
    country = models.CharField(max_length=100, blank=True)
    release_year = models.PositiveSmallIntegerField(
        blank=True,
        null=True,
        validators=[MinValueValidator(1900), MaxValueValidator(2100)],
    )
    episode_count = models.PositiveSmallIntegerField(
        blank=True,
        null=True,
        validators=[MinValueValidator(1), MaxValueValidator(10000)],
    )
    poster_url = models.URLField(max_length=500, blank=True)
    synopsis = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    is_featured = models.BooleanField(default=False, db_index=True)
    date_added = models.DateTimeField(auto_now_add=True)
    posted_by = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        ordering = ["-date_added", "title"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("drama_detail", args=[self.pk])


class Rating(models.Model):
    drama = models.ForeignKey(Drama, on_delete=models.CASCADE, related_name="ratings")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="drama_ratings")
    score = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["drama", "user"],
                name="unique_drama_rating",
            )
        ]

    def __str__(self):
        return f"{self.user} rated {self.drama} {self.score}/10"
