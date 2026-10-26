from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from .models import Drama

COUNTRY_CHOICES = (
    ("", "Select a country"),
    ("South Korea", "South Korea"),
    ("China", "China"),
    ("Japan", "Japan"),
    ("Taiwan", "Taiwan"),
    ("Thailand", "Thailand"),
    ("Philippines", "Philippines"),
    ("Hong Kong", "Hong Kong"),
    ("United States", "United States"),
    ("United Kingdom", "United Kingdom"),
    ("Other", "Other"),
)

GENRE_CHOICES = (
    ("Romance", "Romance"),
    ("Romantic Comedy", "Romantic Comedy"),
    ("Comedy", "Comedy"),
    ("Drama", "Drama"),
    ("Thriller", "Thriller"),
    ("Crime", "Crime"),
    ("Mystery", "Mystery"),
    ("Fantasy", "Fantasy"),
    ("Medical", "Medical"),
    ("Historical", "Historical"),
    ("Action", "Action"),
    ("Adventure", "Adventure"),
    ("Horror", "Horror"),
    ("Sci-Fi", "Sci-Fi"),
    ("Slice of Life", "Slice of Life"),
)


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update(
            {
                "class": "form-input",
                "autocomplete": "username",
                "placeholder": "Username",
            }
        )
        self.fields["password"].widget.attrs.update(
            {
                "class": "form-input",
                "autocomplete": "current-password",
                "placeholder": "Password",
            }
        )


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        placeholders = {
            "username": "Username",
            "email": "Email address",
            "password1": "Password",
            "password2": "Confirm password",
        }
        autocomplete = {
            "username": "username",
            "email": "email",
            "password1": "new-password",
            "password2": "new-password",
        }
        for name, field in self.fields.items():
            field.widget.attrs.update(
                {
                    "class": "form-input",
                    "autocomplete": autocomplete.get(name, ""),
                    "placeholder": placeholders.get(name, field.label),
                }
            )

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError("That username is already taken.")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with that email already exists.")
        return email


class DramaForm(forms.ModelForm):
    class Meta:
        model = Drama
        fields = (
            "title",
            "genre",
            "country",
            "release_year",
            "episode_count",
            "poster_url",
            "synopsis",
            "notes",
        )
        labels = {
            "poster_url": "Poster URL",
            "notes": "Why you recommend it",
        }
        widgets = {
            "title": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "Drama title"}
            ),
            "release_year": forms.NumberInput(
                attrs={"class": "form-input", "placeholder": "2024", "min": 1900, "max": 2100}
            ),
            "episode_count": forms.NumberInput(
                attrs={"class": "form-input", "placeholder": "16", "min": 1}
            ),
            "poster_url": forms.URLInput(
                attrs={"class": "form-input", "placeholder": "https://example.com/poster.jpg"}
            ),
            "synopsis": forms.Textarea(
                attrs={
                    "class": "form-input",
                    "placeholder": "What is the drama about?",
                    "rows": 4,
                }
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-input",
                    "placeholder": "Why should the board watch it?",
                    "rows": 3,
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        current_country = self.instance.country if self.instance and self.instance.pk else ""
        current_genres = (
            [
                genre.strip()
                for genre in self.instance.genre.split(",")
                if genre.strip()
            ]
            if self.instance and self.instance.pk
            else []
        )

        country_choices = list(COUNTRY_CHOICES)
        if current_country and current_country not in dict(country_choices):
            country_choices.append((current_country, current_country))

        genre_choices = list(GENRE_CHOICES)
        for genre in current_genres:
            if genre not in dict(genre_choices):
                genre_choices.append((genre, genre))

        self.fields["genre"] = forms.MultipleChoiceField(
            choices=genre_choices,
            label="Genres",
            widget=forms.CheckboxSelectMultiple(),
            error_messages={"required": "Enter at least one genre."},
            help_text="Choose one or more genres.",
        )
        self.fields["country"] = forms.ChoiceField(
            choices=country_choices,
            required=False,
            label="Country",
            widget=forms.Select(attrs={"class": "form-input"}),
        )

        if current_genres:
            self.initial["genre"] = current_genres

        self.fields["title"].error_messages["required"] = "Enter the drama title."
        self.fields["release_year"].widget.attrs.update({"min": 1900, "max": 2100})
        self.fields["episode_count"].widget.attrs.update({"min": 1})

    def clean_title(self):
        title = self.cleaned_data["title"].strip()
        if not title:
            raise ValidationError("Enter the drama title.")
        return title

    def clean_genre(self):
        return ", ".join(self.cleaned_data["genre"])

    def clean_country(self):
        return self.cleaned_data["country"]

    def clean_poster_url(self):
        return self.cleaned_data["poster_url"].strip()


class FeaturedDramasForm(forms.Form):
    dramas = forms.ModelMultipleChoiceField(
        queryset=Drama.objects.all(),
        required=False,
        label="Featured dramas",
        widget=forms.CheckboxSelectMultiple,
        help_text="Choose up to two dramas.",
    )

    def clean_dramas(self):
        dramas = self.cleaned_data["dramas"]
        if len(dramas) > 2:
            raise ValidationError("Choose no more than two featured dramas.")
        return dramas


class RatingForm(forms.Form):
    score = forms.ChoiceField(
        choices=[(score, f"{score} / 10") for score in range(1, 11)],
        label="Your rating",
        widget=forms.Select(attrs={"class": "form-input"}),
    )

