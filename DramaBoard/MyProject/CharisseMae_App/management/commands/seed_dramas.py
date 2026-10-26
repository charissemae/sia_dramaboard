from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from CharisseMae_App.models import Drama


DRAMAS = [
    {
        "title": "True Beauty",
        "genre": "Romance",
        "country": "South Korea",
        "release_year": 2020,
        "episode_count": 16,
        "synopsis": "A high school student uses makeup to reinvent herself after being bullied, then navigates friendship, family, and first love.",
        "notes": "A bright comfort watch with a funny supporting cast and a satisfying glow-up arc.",
    },
    {
        "title": "Crash Landing on You",
        "genre": "Romance",
        "country": "South Korea",
        "release_year": 2019,
        "episode_count": 16,
        "synopsis": "A South Korean heiress accidentally paraglides into North Korea and is hidden by an army officer and his squad.",
        "notes": "Big-hearted romance, found family, and a surprisingly funny ensemble.",
    },
    {
        "title": "Goblin",
        "genre": "Fantasy",
        "country": "South Korea",
        "release_year": 2016,
        "episode_count": 16,
        "synopsis": "An immortal goblin searches for his human bride while a grim reaper and a mysterious past complicate their fates.",
        "notes": "A gorgeous fantasy romance with a soundtrack that stays with you.",
    },
    {
        "title": "Reply 1988",
        "genre": "Comedy",
        "country": "South Korea",
        "release_year": 2015,
        "episode_count": 20,
        "synopsis": "Five families in a Seoul neighborhood share the small joys and growing pains of life in the late 1980s.",
        "notes": "Warm, nostalgic, and full of characters who feel like real neighbors.",
    },
    {
        "title": "Itaewon Class",
        "genre": "Drama",
        "country": "South Korea",
        "release_year": 2020,
        "episode_count": 16,
        "synopsis": "An ex-convict opens a restaurant in Itaewon and builds a team while pursuing revenge against a powerful food conglomerate.",
        "notes": "A determined underdog story with a strong found-family streak.",
    },
    {
        "title": "Hospital Playlist",
        "genre": "Medical",
        "country": "South Korea",
        "release_year": 2020,
        "episode_count": 12,
        "synopsis": "Five doctors who have been friends since medical school balance patients, families, and their band practice.",
        "notes": "Gentle, funny, and deeply human. The friendship is the real main character.",
    },
    {
        "title": "Vincenzo",
        "genre": "Crime",
        "country": "South Korea",
        "release_year": 2021,
        "episode_count": 20,
        "synopsis": "An Italian-Korean lawyer returns to Seoul and uses unconventional methods to take on a ruthless pharmaceutical conglomerate.",
        "notes": "Stylish, darkly funny, and full of satisfying revenge beats.",
    },
    {
        "title": "Twenty-Five Twenty-One",
        "genre": "Romance",
        "country": "South Korea",
        "release_year": 2022,
        "episode_count": 16,
        "synopsis": "A fencer and a reporter meet as teenagers during a time of uncertainty and grow together through the highs and lows of youth.",
        "notes": "A bittersweet coming-of-age romance with a memorable summer atmosphere.",
    },
    {
        "title": "My Mister",
        "genre": "Drama",
        "country": "South Korea",
        "release_year": 2018,
        "episode_count": 16,
        "synopsis": "A weary office worker and a young contract employee form an unexpected bond while facing pressure from work and family.",
        "notes": "Quiet, heavy, and ultimately hopeful. Give it time to unfold.",
    },
    {
        "title": "Signal",
        "genre": "Thriller",
        "country": "South Korea",
        "release_year": 2016,
        "episode_count": 16,
        "synopsis": "A profiler communicates through a mysterious walkie-talkie with a detective from the past to solve cold cases.",
        "notes": "A tense, tightly plotted crime thriller that keeps the stakes personal.",
    },
    {
        "title": "The Glory",
        "genre": "Thriller",
        "country": "South Korea",
        "release_year": 2022,
        "episode_count": 16,
        "synopsis": "A woman builds a meticulous plan to take revenge on the classmates who made her school years a living nightmare.",
        "notes": "A slow-burn revenge drama with a chilling central performance.",
    },
    {
        "title": "Business Proposal",
        "genre": "Romantic Comedy",
        "country": "South Korea",
        "release_year": 2022,
        "episode_count": 12,
        "synopsis": "A woman goes on a blind date in disguise for a friend and discovers the man across the table is her new CEO.",
        "notes": "Light, fast, and full of classic rom-com chaos.",
        "poster_url": "https://image.tmdb.org/t/p/w500/iLh7L8ZuvgdxFaM9sImyv2iKYLe.jpg",
    },
]


class Command(BaseCommand):
    help = "Create the initial DramaBoard catalog with 12 dramas."

    @transaction.atomic
    def handle(self, *args, **options):
        owner = (
            User.objects.filter(is_superuser=True).order_by("id").first()
            or User.objects.order_by("id").first()
        )
        if owner is None:
            raise CommandError("Create a user before seeding dramas.")

        created = 0
        skipped = 0
        for data in DRAMAS:
            drama, was_created = Drama.objects.get_or_create(
                title=data["title"],
                defaults={
                    "genre": data["genre"],
                    "country": data["country"],
                    "release_year": data["release_year"],
                    "episode_count": data["episode_count"],
                    "synopsis": data["synopsis"],
                    "notes": data["notes"],
                    "posted_by": owner,
                },
            )
            if was_created:
                created += 1
                self.stdout.write(f"Added {drama.title}")
            else:
                skipped += 1
                filled = []
                for field in ("release_year", "episode_count", "synopsis", "poster_url"):
                    if not getattr(drama, field) and data.get(field):
                        setattr(drama, field, data[field])
                        filled.append(field)
                if filled:
                    drama.save(update_fields=filled)
                    self.stdout.write(
                        f"Skipped existing {drama.title}; filled {', '.join(filled)}"
                    )
                else:
                    self.stdout.write(f"Skipped existing {drama.title}")

        self.stdout.write(
            self.style.SUCCESS(
                f"Seed complete: {created} added, {skipped} skipped, {owner.username} owns new entries."
            )
        )
