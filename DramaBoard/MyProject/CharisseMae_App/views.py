from collections import Counter

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Avg, Count, Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import DramaForm, FeaturedDramasForm, RatingForm, RegistrationForm
from .models import Drama, Rating


def _genre_breakdown(dramas):
    counts = Counter()

    for drama in dramas:
        counts.update(
            {
                genre.strip()
                for genre in drama.genre.split(",")
                if genre.strip()
            }
        )

    return [
        {"name": genre, "count": counts[genre]}
        for genre in sorted(counts, key=lambda name: name.lower())
    ]


def _featured_dramas(dramas):
    selected = [drama for drama in dramas if drama.is_featured]
    return selected[:2] if selected else dramas[:2]


def landing(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "Inv_Dramas/landingpage.html")


def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    form = RegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Welcome to DramaBoard. Your account is ready.")
        return redirect("dashboard")

    return render(request, "Inv_Dramas/register.html", {"form": form})


@login_required
def index(request):
    all_dramas = list(
        Drama.objects.select_related("posted_by")
        .annotate(avg_rating=Avg("ratings__score"))
        .order_by("-date_added", "title")
    )
    genre_filters = _genre_breakdown(all_dramas)
    requested_genre = request.GET.get("genre", "").strip()
    genre_lookup = {
        item["name"].lower(): item["name"] for item in genre_filters
    }
    selected_genre = (
        genre_lookup.get(requested_genre.lower(), requested_genre)
        if requested_genre
        else ""
    )
    dramas = all_dramas

    if selected_genre:
        selected_key = selected_genre.lower()
        dramas = [
            drama
            for drama in all_dramas
            if selected_key
            in {
                genre.strip().lower()
                for genre in drama.genre.split(",")
                if genre.strip()
            }
        ]

    context = {
        "dramas": dramas,
        "featured_dramas": _featured_dramas(all_dramas),
        "genre_filters": genre_filters,
        "selected_genre": selected_genre,
        "genre_count": len(genre_filters),
        "total_dramas": len(all_dramas),
    }
    return render(request, "Inv_Dramas/dashboard.html", context)


@login_required
def featured_manage(request):
    if not request.user.is_staff:
        raise PermissionDenied

    dramas = list(
        Drama.objects.select_related("posted_by").order_by("-date_added", "title")
    )
    current_featured = _featured_dramas(dramas)
    form = FeaturedDramasForm(
        request.POST if request.method == "POST" else None,
        initial={"dramas": [drama.pk for drama in current_featured]},
    )

    if request.method == "POST" and form.is_valid():
        selected = list(form.cleaned_data["dramas"])
        selected_ids = [drama.pk for drama in selected]

        with transaction.atomic():
            Drama.objects.update(is_featured=False)
            if selected_ids:
                Drama.objects.filter(pk__in=selected_ids).update(is_featured=True)

        if selected:
            messages.success(request, "Featured dramas updated.")
        else:
            messages.success(
                request,
                "Featured dramas reset to the newest recommendations.",
            )
        return redirect("dashboard")

    if request.method == "POST":
        selected_ids = {
            int(pk) for pk in request.POST.getlist("dramas") if pk.isdigit()
        }
    else:
        selected_ids = {drama.pk for drama in current_featured}

    return render(
        request,
        "Inv_Dramas/featured_manage.html",
        {
            "form": form,
            "dramas": dramas,
            "selected_ids": selected_ids,
        },
    )


@login_required
def drama_list(request):
    search_query = request.GET.get("q", "").strip()
    dramas = (
        Drama.objects.select_related("posted_by")
        .annotate(
            avg_rating=Avg("ratings__score"),
            rating_count=Count("ratings", distinct=True),
        )
        .order_by("-date_added", "title")
    )

    if search_query:
        dramas = dramas.filter(
            Q(title__icontains=search_query)
            | Q(genre__icontains=search_query)
            | Q(country__icontains=search_query)
            | Q(synopsis__icontains=search_query)
            | Q(notes__icontains=search_query)
        )

    return render(
        request,
        "Inv_Dramas/drama_list.html",
        {
            "dramas": dramas,
            "drama_count": dramas.count(),
            "search_query": search_query,
        },
    )


@login_required
def drama_detail(request, pk):
    drama = get_object_or_404(
        Drama.objects.select_related("posted_by"),
        pk=pk,
    )
    user_rating = Rating.objects.filter(drama=drama, user=request.user).first()
    rating_form = RatingForm(
        request.POST or None,
        initial={"score": user_rating.score if user_rating else 8},
    )

    if request.method == "POST":
        if rating_form.is_valid():
            Rating.objects.update_or_create(
                drama=drama,
                user=request.user,
                defaults={"score": rating_form.cleaned_data["score"]},
            )
            messages.success(request, "Your rating has been saved.")
            return redirect(drama)

    rating_stats = drama.ratings.aggregate(
        average=Avg("score"),
        total=Count("id"),
    )
    ratings = drama.ratings.select_related("user").order_by("-updated_at")[:6]

    context = {
        "drama": drama,
        "is_owner": drama.posted_by == request.user,
        "rating_form": rating_form,
        "user_rating": user_rating,
        "average_rating": rating_stats["average"],
        "rating_count": rating_stats["total"],
        "ratings": ratings,
    }
    return render(request, "Inv_Dramas/drama_detail.html", context)


@login_required
def drama_create(request):
    form = DramaForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        drama = form.save(commit=False)
        drama.posted_by = request.user
        drama.save()
        messages.success(request, f"{drama.title} was added to the board.")
        return redirect(drama)

    return render(
        request,
        "Inv_Dramas/drama_form.html",
        {"form": form, "page_title": "Add a drama", "submit_label": "Add drama"},
    )


@login_required
def drama_edit(request, pk):
    drama = get_object_or_404(Drama, pk=pk, posted_by=request.user)
    form = DramaForm(request.POST or None, instance=drama)
    if request.method == "POST" and form.is_valid():
        drama = form.save()
        messages.success(request, f"{drama.title} was updated.")
        return redirect(drama)

    return render(
        request,
        "Inv_Dramas/drama_form.html",
        {
            "form": form,
            "drama": drama,
            "page_title": "Edit drama",
            "submit_label": "Save changes",
        },
    )


@login_required
def drama_delete(request, pk):
    drama = get_object_or_404(Drama, pk=pk, posted_by=request.user)
    if request.method == "POST":
        title = drama.title
        drama.delete()
        messages.success(request, f"{title} was removed from the board.")
        return redirect("drama_list")

    return render(
        request,
        "Inv_Dramas/drama_confirm_delete.html",
        {"drama": drama},
    )
