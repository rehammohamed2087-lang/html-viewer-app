from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import UploadForm
from .models import HtmlPage


def home(request):
    pages = HtmlPage.objects.all()
    selected = None
    if request.GET.get("p", "").isdigit():
        selected = pages.filter(pk=request.GET["p"]).first()
    selected = selected or pages.first()
    return render(request, "viewer/home.html", {"pages": pages, "selected": selected})


@staff_member_required(login_url="login")
@require_POST
def upload(request):
    form = UploadForm(request.POST, request.FILES)
    if not form.is_valid():
        for errs in form.errors.values():
            for e in errs:
                messages.error(request, e)
        return redirect("home")
    f = form.cleaned_data["file"]
    try:
        html = f.read().decode("utf-8-sig")
    except UnicodeDecodeError:
        messages.error(request, "الملف لازم يكون بترميز UTF-8.")
        return redirect("home")
    if "\x00" in html:
        messages.error(request, "الملف يحتوي على بيانات غير صالحة.")
        return redirect("home")
    page = HtmlPage.objects.create(title=f.name.rsplit(".", 1)[0][:150], content=html)
    return redirect(f"/?p={page.pk}")


@staff_member_required(login_url="login")
@require_POST
def delete(request, pk):
    get_object_or_404(HtmlPage, pk=pk).delete()
    return redirect("home")


def raw(request, pk):
    """بيقدّم الـ HTML بعزل كامل: ميقدرش يوصل لكوكيز/جلسة الأدمن."""
    page = get_object_or_404(HtmlPage, pk=pk)
    resp = HttpResponse(page.content, content_type="text/html; charset=utf-8")
    resp["Content-Security-Policy"] = (
        "sandbox allow-scripts allow-forms allow-popups allow-modals allow-pointer-lock"
    )
    resp["X-Content-Type-Options"] = "nosniff"
    resp["Cache-Control"] = "private, max-age=0, must-revalidate"
    return resp
