from django.shortcuts import render


def home(request):
    return render(request, "core/home.html")


def coming_soon(request, page_title):
    return render(request, "core/coming_soon.html", {"page_title": page_title})
