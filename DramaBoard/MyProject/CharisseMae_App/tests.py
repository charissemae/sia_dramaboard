from io import StringIO

from django import forms
from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.urls import reverse

from .models import Drama, Rating


class AuthenticationTests(TestCase):
    def test_landing_is_public_and_links_to_auth(self):
        response = self.client.get(reverse("landing"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Track the dramas you love.")
        self.assertContains(response, reverse("login"))
        self.assertContains(response, reverse("register"))

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("dashboard"))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('dashboard')}")

    def test_authenticated_user_is_redirected_from_landing(self):
        self.client.force_login(User.objects.create_user("viewer", password="StrongPass123!"))
        response = self.client.get(reverse("landing"))
        self.assertRedirects(response, reverse("dashboard"))

    def test_register_creates_hashed_user_and_logs_in(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "newmember",
                "email": "newmember@example.com",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            },
        )
        self.assertRedirects(response, reverse("dashboard"))

        user = User.objects.get(username="newmember")
        self.assertEqual(user.email, "newmember@example.com")
        self.assertNotEqual(user.password, "StrongPass123!")
        self.assertTrue(user.check_password("StrongPass123!"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_register_rejects_short_password(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "shortpass",
                "email": "shortpass@example.com",
                "password1": "short",
                "password2": "short",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "at least 8 characters")
        self.assertFalse(User.objects.filter(username="shortpass").exists())

    def test_register_shows_duplicate_username_error(self):
        User.objects.create_user("existing", password="StrongPass123!")
        response = self.client.post(
            reverse("register"),
            {
                "username": "EXISTING",
                "email": "new@example.com",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "That username is already taken.")
        self.assertEqual(User.objects.filter(username__iexact="existing").count(), 1)

    def test_register_shows_duplicate_email_error(self):
        User.objects.create_user(
            "existing",
            email="taken@example.com",
            password="StrongPass123!",
        )
        response = self.client.post(
            reverse("register"),
            {
                "username": "another",
                "email": "TAKEN@example.com",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "An account with that email already exists.")
        self.assertFalse(User.objects.filter(username="another").exists())

    def test_register_rejects_mismatched_passwords(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "mismatch",
                "email": "mismatch@example.com",
                "password1": "StrongPass123!",
                "password2": "StrongPass124!",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="mismatch").exists())

    def test_authenticated_user_is_redirected_from_login_and_register(self):
        self.client.force_login(User.objects.create_user("viewer", password="StrongPass123!"))
        self.assertRedirects(self.client.get(reverse("login")), reverse("dashboard"))
        self.assertRedirects(self.client.get(reverse("register")), reverse("dashboard"))

    def test_login_and_logout(self):
        user = User.objects.create_user(
            "boardmember",
            email="member@example.com",
            password="StrongPass123!",
        )
        response = self.client.post(
            reverse("login"),
            {"username": "boardmember", "password": "StrongPass123!"},
        )
        self.assertRedirects(response, reverse("dashboard"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

        response = self.client.post(reverse("logout"))
        self.assertRedirects(response, reverse("landing"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_navbar_shows_username_and_email(self):
        User.objects.create_user(
            "boardmember",
            email="member@example.com",
            password="StrongPass123!",
        )
        self.client.login(username="boardmember", password="StrongPass123!")
        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, "boardmember")
        self.assertContains(response, "member@example.com")
        self.assertContains(response, reverse("logout"))


class DramaFeatureTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            "owner",
            email="owner@example.com",
            password="StrongPass123!",
        )
        self.other = User.objects.create_user(
            "other",
            email="other@example.com",
            password="StrongPass123!",
        )
        self.drama = Drama.objects.create(
            title="Test Drama",
            genre="Romance",
            country="South Korea",
            release_year=2024,
            episode_count=16,
            synopsis="A test synopsis.",
            notes="A test recommendation.",
            posted_by=self.owner,
        )

    def test_drama_pages_require_login(self):
        pages = [
            (reverse("drama_list"), reverse("drama_list")),
            (reverse("drama_detail", args=[self.drama.pk]), reverse("drama_detail", args=[self.drama.pk])),
            (reverse("drama_create"), reverse("drama_create")),
        ]
        for url, next_url in pages:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)
            self.assertIn(f"{reverse('login')}?next={next_url}", response.url)

    def test_all_dramas_lists_cards_and_links_to_detail(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse("drama_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Drama")
        self.assertContains(response, "A test synopsis.")
        self.assertContains(response, reverse("drama_detail", args=[self.drama.pk]))
        self.assertContains(response, "1 recommendation")

    def test_all_dramas_search_filters_results_and_preserves_query(self):
        Drama.objects.create(
            title="Sky Castle",
            genre="Drama",
            country="South Korea",
            posted_by=self.other,
        )
        self.client.force_login(self.owner)

        response = self.client.get(reverse("drama_list"), {"q": "romance"})

        self.assertContains(response, "Test Drama")
        self.assertNotContains(response, "Sky Castle")
        self.assertContains(response, "1 result for")
        self.assertContains(response, 'value="romance"')

        response = self.client.get(reverse("drama_list"), {"q": "not on the board"})

        self.assertContains(response, "No dramas found")
        self.assertNotContains(response, "Test Drama")

    def test_dashboard_genre_filters_split_and_filter_combined_genres(self):
        Drama.objects.create(
            title="Signal Test",
            genre="Thriller",
            country="South Korea",
            posted_by=self.other,
        )
        Drama.objects.create(
            title="Mixed Test",
            genre="Romance, Fantasy",
            country="China",
            posted_by=self.other,
        )
        self.client.force_login(self.owner)

        response = self.client.get(reverse("dashboard"))
        genre_counts = {
            item["name"]: item["count"]
            for item in response.context["genre_filters"]
        }

        self.assertEqual(genre_counts["Romance"], 2)
        self.assertEqual(genre_counts["Fantasy"], 1)
        self.assertEqual(genre_counts["Thriller"], 1)
        self.assertContains(
            response,
            f"{reverse('dashboard')}?genre=Romance#all-dramas",
        )
        self.assertContains(
            response,
            f"{reverse('dashboard')}?genre=Fantasy#all-dramas",
        )

        response = self.client.get(reverse("dashboard"), {"genre": "Fantasy"})

        self.assertEqual(
            [drama.title for drama in response.context["dramas"]],
            ["Mixed Test"],
        )
        self.assertEqual(response.context["selected_genre"], "Fantasy")
        self.assertContains(response, 'aria-current="true"')

    def test_detail_shows_drama_fields_and_owner_actions(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse("drama_detail", args=[self.drama.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Drama")
        self.assertContains(response, "2024")
        self.assertContains(response, "16 episodes")
        self.assertContains(response, "A test synopsis.")
        self.assertContains(response, "A test recommendation.")
        self.assertContains(response, reverse("drama_edit", args=[self.drama.pk]))
        self.assertContains(response, reverse("drama_delete", args=[self.drama.pk]))

    def test_create_assigns_logged_in_user_and_ignores_posted_by_input(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("drama_create"),
            {
                "title": "New Drama",
                "genre": "Thriller",
                "country": "South Korea",
                "release_year": "2025",
                "episode_count": "12",
                "poster_url": "https://example.com/poster.jpg",
                "synopsis": "A new synopsis.",
                "notes": "A new recommendation.",
                "posted_by": self.other.pk,
            },
        )
        drama = Drama.objects.get(title="New Drama")
        self.assertRedirects(
            response,
            reverse("drama_detail", args=[drama.pk]),
        )
        self.assertEqual(drama.posted_by, self.owner)
        self.assertEqual(drama.release_year, 2025)
        self.assertEqual(drama.episode_count, 12)
        self.assertEqual(drama.poster_url, "https://example.com/poster.jpg")

    def test_drama_form_uses_country_choices_and_multiple_genres(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse("drama_create"))
        form = response.context["form"]

        self.assertIsInstance(form.fields["country"].widget, forms.Select)
        self.assertIsInstance(form.fields["genre"].widget, forms.CheckboxSelectMultiple)
        self.assertContains(response, 'class="select-shell"')
        self.assertContains(response, 'class="icon select-chevron"')

    def test_create_accepts_multiple_genres(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("drama_create"),
            {
                "title": "Multi Genre Drama",
                "genre": ["Thriller", "Mystery"],
                "country": "Japan",
            },
        )
        drama = Drama.objects.get(title="Multi Genre Drama")

        self.assertRedirects(response, reverse("drama_detail", args=[drama.pk]))
        self.assertEqual(drama.genre, "Thriller, Mystery")
        self.assertEqual(drama.country, "Japan")

    def test_create_requires_title_and_genre(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("drama_create"),
            {"title": "   "},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Enter the drama title.")
        self.assertContains(response, "Enter at least one genre.")
        self.assertFalse(Drama.objects.filter(posted_by=self.owner).exclude(pk=self.drama.pk).exists())

    def test_owner_can_edit_drama(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("drama_edit", args=[self.drama.pk]),
            {
                "title": "Updated Drama",
                "genre": "Comedy",
                "country": "Japan",
                "release_year": "2023",
                "episode_count": "10",
                "poster_url": "",
                "synopsis": "Updated synopsis.",
                "notes": "Updated notes.",
            },
        )
        self.assertRedirects(
            response,
            reverse("drama_detail", args=[self.drama.pk]),
        )
        self.drama.refresh_from_db()
        self.assertEqual(self.drama.title, "Updated Drama")
        self.assertEqual(self.drama.genre, "Comedy")
        self.assertEqual(self.drama.country, "Japan")
        self.assertEqual(self.drama.release_year, 2023)
        self.assertEqual(self.drama.episode_count, 10)
        self.assertEqual(self.drama.synopsis, "Updated synopsis.")
        self.assertEqual(self.drama.notes, "Updated notes.")

    def test_non_owner_cannot_edit_or_delete_drama(self):
        self.client.force_login(self.other)
        self.assertEqual(
            self.client.get(reverse("drama_edit", args=[self.drama.pk])).status_code,
            404,
        )
        self.assertEqual(
            self.client.get(reverse("drama_delete", args=[self.drama.pk])).status_code,
            404,
        )
        response = self.client.post(
            reverse("drama_delete", args=[self.drama.pk]),
        )
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Drama.objects.filter(pk=self.drama.pk).exists())

    def test_owner_can_delete_drama_and_its_ratings(self):
        Rating.objects.create(drama=self.drama, user=self.other, score=8)
        self.client.force_login(self.owner)
        response = self.client.get(reverse("drama_delete", args=[self.drama.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Delete Test Drama?")

        response = self.client.post(reverse("drama_delete", args=[self.drama.pk]))
        self.assertRedirects(response, reverse("drama_list"))
        self.assertFalse(Drama.objects.filter(pk=self.drama.pk).exists())
        self.assertFalse(Rating.objects.filter(drama_id=self.drama.pk).exists())

    def test_rating_can_be_created_updated_and_averaged(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("drama_detail", args=[self.drama.pk]),
            {"score": "7"},
        )
        self.assertRedirects(
            response,
            reverse("drama_detail", args=[self.drama.pk]),
        )
        rating = Rating.objects.get(drama=self.drama, user=self.owner)
        self.assertEqual(rating.score, 7)

        self.client.post(
            reverse("drama_detail", args=[self.drama.pk]),
            {"score": "9"},
        )
        rating.refresh_from_db()
        self.assertEqual(rating.score, 9)
        self.assertEqual(
            Rating.objects.filter(drama=self.drama, user=self.owner).count(),
            1,
        )

        self.client.force_login(self.other)
        self.client.post(
            reverse("drama_detail", args=[self.drama.pk]),
            {"score": "5"},
        )
        response = self.client.get(reverse("drama_detail", args=[self.drama.pk]))
        self.assertContains(response, "7.0")
        self.assertContains(response, "2 community ratings")

    def test_invalid_rating_is_rejected(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("drama_detail", args=[self.drama.pk]),
            {"score": "11"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Select a valid choice.")
        self.assertFalse(Rating.objects.filter(drama=self.drama, user=self.owner).exists())

    def test_drama_list_annotates_average_rating(self):
        Rating.objects.create(drama=self.drama, user=self.owner, score=8)
        Rating.objects.create(drama=self.drama, user=self.other, score=6)
        self.client.force_login(self.owner)
        response = self.client.get(reverse("drama_list"))
        listed_drama = response.context["dramas"].get(pk=self.drama.pk)
        self.assertEqual(listed_drama.avg_rating, 7.0)
        self.assertEqual(listed_drama.rating_count, 2)


class FeaturedDramaTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            "owner",
            email="owner@example.com",
            password="StrongPass123!",
        )
        self.staff = User.objects.create_superuser(
            "curator",
            email="curator@example.com",
            password="StrongPass123!",
        )
        self.first = Drama.objects.create(
            title="First Pick",
            genre="Romance",
            country="South Korea",
            posted_by=self.owner,
        )
        self.second = Drama.objects.create(
            title="Second Pick",
            genre="Thriller",
            country="South Korea",
            posted_by=self.owner,
        )
        self.third = Drama.objects.create(
            title="Third Pick",
            genre="Comedy",
            country="South Korea",
            posted_by=self.owner,
        )

    def test_dashboard_uses_featured_flags_with_newest_fallback(self):
        self.client.force_login(self.owner)

        response = self.client.get(reverse("dashboard"))
        self.assertEqual(
            [drama.title for drama in response.context["featured_dramas"]],
            ["Third Pick", "Second Pick"],
        )

        self.first.is_featured = True
        self.first.save(update_fields=["is_featured"])

        response = self.client.get(reverse("dashboard"))
        self.assertEqual(
            [drama.title for drama in response.context["featured_dramas"]],
            ["First Pick"],
        )

    def test_non_staff_cannot_manage_featured_dramas(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse("featured_manage"))
        self.assertEqual(response.status_code, 403)

        response = self.client.post(
            reverse("featured_manage"),
            {"dramas": [self.first.pk]},
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Drama.objects.filter(is_featured=True).exists())

    def test_staff_can_change_featured_dramas(self):
        self.client.force_login(self.staff)

        response = self.client.get(reverse("featured_manage"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Change featured dramas")
        self.assertContains(response, 'name="dramas"')

        response = self.client.post(
            reverse("featured_manage"),
            {"dramas": [self.first.pk, self.third.pk]},
        )
        self.assertRedirects(response, reverse("dashboard"))

        self.first.refresh_from_db()
        self.second.refresh_from_db()
        self.third.refresh_from_db()
        self.assertTrue(self.first.is_featured)
        self.assertFalse(self.second.is_featured)
        self.assertTrue(self.third.is_featured)

        response = self.client.get(reverse("dashboard"))
        self.assertEqual(
            [drama.title for drama in response.context["featured_dramas"]],
            ["Third Pick", "First Pick"],
        )

    def test_staff_cannot_feature_more_than_two_dramas(self):
        self.client.force_login(self.staff)

        response = self.client.post(
            reverse("featured_manage"),
            {
                "dramas": [
                    self.first.pk,
                    self.second.pk,
                    self.third.pk,
                ]
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Choose no more than two featured dramas.")
        self.assertFalse(Drama.objects.filter(is_featured=True).exists())

    def test_staff_can_clear_featured_selection(self):
        self.client.force_login(self.staff)
        self.first.is_featured = True
        self.first.save(update_fields=["is_featured"])

        response = self.client.post(reverse("featured_manage"), {})

        self.assertRedirects(response, reverse("dashboard"))
        self.assertFalse(Drama.objects.filter(is_featured=True).exists())


class SeedCommandTests(TestCase):
    def test_seed_dramas_creates_twelve_and_is_idempotent(self):
        owner = User.objects.create_superuser(
            "seedowner",
            email="seed@example.com",
            password="StrongPass123!",
        )
        output = StringIO()
        call_command("seed_dramas", stdout=output)
        self.assertEqual(Drama.objects.count(), 12)
        self.assertEqual(Drama.objects.filter(posted_by=owner).count(), 12)

        second_output = StringIO()
        call_command("seed_dramas", stdout=second_output)
        self.assertEqual(Drama.objects.count(), 12)
        self.assertIn("0 added, 12 skipped", second_output.getvalue())

    def test_seed_fills_missing_fields_without_overwriting_user_content(self):
        owner = User.objects.create_superuser(
            "seedowner",
            email="seed@example.com",
            password="StrongPass123!",
        )
        drama = Drama.objects.create(
            title="True Beauty",
            genre="My genre",
            notes="My recommendation.",
            posted_by=owner,
        )
        call_command("seed_dramas", stdout=StringIO())
        drama.refresh_from_db()
        self.assertEqual(drama.genre, "My genre")
        self.assertEqual(drama.notes, "My recommendation.")
        self.assertEqual(drama.release_year, 2020)
        self.assertEqual(drama.episode_count, 16)
        self.assertTrue(drama.synopsis)

    def test_seed_dramas_requires_an_existing_user(self):
        with self.assertRaisesMessage(CommandError, "Create a user before seeding dramas."):
            call_command("seed_dramas", stdout=StringIO())
