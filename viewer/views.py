from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Max, Prefetch, ProtectedError
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .access import has_access
from .forms import (
    CodeCreateForm, FileEditForm, GradeForm, StageForm, SettingsForm, SubjectForm, UploadForm,
    read_html_file,
)
from .models import AccessCode, Grade, HtmlPage, SiteSettings, Stage, Subject

staff_only = staff_member_required(login_url="login")

# (اسم المرحلة، عدد الصفوف)
DEFAULT_STAGES = [("المرحلة الابتدائية", 6), ("المرحلة الإعدادية", 3), ("المرحلة الثانوية", 3)]
ORDINALS = ["الأول", "الثاني", "الثالث", "الرابع", "الخامس", "السادس",
            "السابع", "الثامن", "التاسع", "العاشر", "الحادي عشر", "الثاني عشر"]


def _add_grades(stage, count):
    """بيضيف «الصف الأول» ... حتى العدد المطلوب، ويتخطى الموجود."""
    existing = set(stage.grades.values_list("name", flat=True))
    order = stage.grades.aggregate(m=Max("order"))["m"] or 0
    added = 0
    for i in range(min(count, len(ORDINALS))):
        name = f"الصف {ORDINALS[i]}"
        if name in existing:
            continue
        order += 1
        Grade.objects.create(stage=stage, name=name, order=order)
        added += 1
    return added


def _flash_errors(request, form):
    for errs in form.errors.values():
        for e in errs:
            messages.error(request, e)


def _int(value):
    value = str(value or "")
    return int(value) if value.isdigit() else 0


# ───────────────────────── الزوار ─────────────────────────

def home(request):
    legacy = request.GET.get("p", "")          # روابط قديمة ?p=ID
    if legacy.isdigit():
        return redirect("page", pk=int(legacy))
    stages = Stage.objects.annotate(n=Count("grades"))
    free_page = (
        HtmlPage.objects.filter(is_free=True)
        .select_related("subject__grade__stage").defer("content").first()
    )
    return render(request, "viewer/home.html", {"stages": stages, "free_page": free_page})


def stage_view(request, pk):
    stage = get_object_or_404(Stage, pk=pk)
    grades = stage.grades.annotate(n=Count("subjects"))
    return render(request, "viewer/stage.html", {"stage": stage, "grades": grades})


def grade_view(request, pk):
    grade = get_object_or_404(Grade.objects.select_related("stage"), pk=pk)
    subjects = grade.subjects.annotate(n=Count("pages"))
    return render(request, "viewer/grade.html", {"grade": grade, "subjects": subjects})


def subject_view(request, pk):
    subject = get_object_or_404(Subject.objects.select_related("grade__stage"), pk=pk)
    pages = subject.pages.defer("content")
    return render(request, "viewer/subject.html", {"subject": subject, "pages": pages})


def page_view(request, pk):
    page = get_object_or_404(
        HtmlPage.objects.select_related("subject__grade__stage").defer("content"), pk=pk
    )
    free_page = None
    allowed = has_access(request, page)
    if not allowed:
        free_page = HtmlPage.objects.filter(is_free=True).defer("content").first()
    return render(request, "viewer/page.html", {"page": page, "allowed": allowed, "free_page": free_page})


def raw(request, pk):
    """بيقدّم الـ HTML بعزل كامل، وبعد التأكد إن الزائر مسموح له."""
    page = get_object_or_404(HtmlPage, pk=pk)
    if not has_access(request, page):
        return HttpResponseForbidden("هذا الملف يحتاج كود دخول.")
    resp = HttpResponse(page.content, content_type="text/html; charset=utf-8")
    resp["Content-Security-Policy"] = (
        "sandbox allow-scripts allow-forms allow-popups allow-modals allow-pointer-lock"
    )
    resp["X-Content-Type-Options"] = "nosniff"
    resp["Cache-Control"] = "private, no-store"
    return resp


def _client_ip(request):
    fwd = request.META.get("HTTP_X_FORWARDED_FOR", "")
    return fwd.split(",")[0].strip() if fwd else request.META.get("REMOTE_ADDR", "")


@require_POST
def unlock(request):
    nxt = request.POST.get("next", "")
    if not url_has_allowed_host_and_scheme(
        nxt, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        nxt = reverse("home")

    key = f"unlock-fail:{_client_ip(request)}"
    fails = cache.get(key, 0)
    if fails >= settings.UNLOCK_MAX_ATTEMPTS:
        messages.error(request, "محاولات كثيرة خاطئة. حاول مرة أخرى بعد عدة دقائق.")
        return redirect(nxt)

    entered = request.POST.get("code", "").strip()
    code = AccessCode.objects.filter(code__iexact=entered).first() if entered else None
    if code and code.is_valid():
        request.session["code_id"] = code.pk
        AccessCode.objects.filter(pk=code.pk).update(last_used_at=timezone.now())
        cache.delete(key)
        messages.success(request, "تم تفعيل الدخول. يمكنك الآن فتح كل الملفات.")
    else:
        cache.set(key, fails + 1, settings.UNLOCK_WINDOW)
        messages.error(request, "الكود غير صحيح أو منتهي. تواصل مع الأدمن للحصول على كود.")
    return redirect(nxt)


@require_POST
def lock(request):
    request.session.pop("code_id", None)
    return redirect("home")


# ───────────────────────── لوحة الأدمن: الملفات ─────────────────────────

@staff_only
def panel(request):
    stages = Stage.objects.prefetch_related(
        Prefetch("grades__subjects__pages", queryset=HtmlPage.objects.defer("content"))
    )
    structure = [
        {"id": st.id, "name": st.name,
         "grades": [
             {"id": g.id, "name": g.name,
              "subjects": [{"id": su.id, "name": su.name} for su in g.subjects.all()]}
             for g in st.grades.all()
         ]}
        for st in stages
    ]
    orphans = HtmlPage.objects.filter(subject__isnull=True).defer("content")
    return render(request, "viewer/panel/dashboard.html", {
        "stages": stages,
        "structure": structure,
        "orphans": orphans,
        "preset": _int(request.GET.get("s")),
        "codes_count": AccessCode.objects.filter(is_active=True).count(),
    })


NEW = "__new__"      # قيمة خيار «إضافة جديد» في قوائم الرفع


def _next_order(model, **filters):
    return (model.objects.filter(**filters).aggregate(m=Max("order"))["m"] or 0) + 1


def _clean_name(post, key, label):
    name = " ".join((post.get(key) or "").split())[:100]
    if not name:
        raise ValidationError(f"اكتب اسم {label} الجديد.")
    return name


def _resolve_subject(post):
    """بيرجّع المادة المختارة، وبينشئ المرحلة/الصف/المادة لو الأدمن اختار «إضافة جديد»."""
    if post.get("stage") == NEW:
        name = _clean_name(post, "new_stage", "المرحلة")
        stage = Stage.objects.filter(name=name).first() or Stage.objects.create(
            name=name, order=_next_order(Stage))
    else:
        stage = Stage.objects.filter(pk=_int(post.get("stage"))).first()
        if not stage:
            raise ValidationError("اختر المرحلة أولاً.")

    if post.get("grade") == NEW:
        name = _clean_name(post, "new_grade", "الصف")
        grade = Grade.objects.filter(stage=stage, name=name).first() or Grade.objects.create(
            stage=stage, name=name, order=_next_order(Grade, stage=stage))
    else:
        grade = Grade.objects.filter(pk=_int(post.get("grade")), stage=stage).first()
        if not grade:
            raise ValidationError("اختر الصف أولاً.")

    if post.get("subject") == NEW:
        name = _clean_name(post, "new_subject", "المادة")
        subject = Subject.objects.filter(grade=grade, name=name).first() or Subject.objects.create(
            grade=grade, name=name, order=_next_order(Subject, grade=grade))
    else:
        subject = Subject.objects.filter(pk=_int(post.get("subject")), grade=grade).first()
        if not subject:
            raise ValidationError("اختر المادة أولاً.")
    return subject


@staff_only
@require_POST
def panel_upload(request):
    files = request.FILES.getlist("file")
    if not files:
        messages.error(request, "اختر ملف HTML واحد على الأقل.")
        return redirect("panel")
    make_free = request.POST.get("is_free") == "on"
    if make_free and len(files) > 1:
        messages.error(request, "الملف المجاني واحد فقط. ارفع ملفاً واحداً إذا أردته مجانياً.")
        return redirect("panel")

    try:
        parsed = [(Path(f.name).stem[:150], read_html_file(f)) for f in files]
        with transaction.atomic():          # لو حصل خطأ مفيش حاجة بتتحفظ (حتى التصنيفات الجديدة)
            subject = _resolve_subject(request.POST)
            for title, html in parsed:
                HtmlPage.objects.create(title=title, content=html, subject=subject, is_free=make_free)
    except ValidationError as e:
        messages.error(request, e.messages[0])
        return redirect("panel")

    messages.success(request, f"تم رفع {len(parsed)} ملف في «{subject}».")
    return redirect(f"{reverse('panel')}?s={subject.pk}")


@staff_only
def file_edit(request, pk):
    page = get_object_or_404(HtmlPage, pk=pk)
    form = FileEditForm(request.POST or None, instance=page)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "تم حفظ التعديلات.")
        return redirect("panel")
    return render(request, "viewer/panel/file_edit.html", {"form": form, "page": page})


@staff_only
@require_POST
def file_toggle_free(request, pk):
    page = get_object_or_404(HtmlPage, pk=pk)
    page.is_free = not page.is_free
    page.save(update_fields=["is_free"])
    messages.success(request, f"«{page.title}» أصبح ملفاً مجانياً." if page.is_free
                     else f"«{page.title}» لم يعد مجانياً.")
    return redirect("panel")


@staff_only
@require_POST
def file_delete(request, pk):
    page = get_object_or_404(HtmlPage, pk=pk)
    page.delete()
    messages.success(request, "تم حذف الملف.")
    return redirect("panel")


# ───────────────────────── لوحة الأدمن: المراحل والمواد ─────────────────────────

@staff_only
def panel_structure(request):
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "add_stage":
            form = StageForm(request.POST)
            if form.is_valid():
                obj = form.save(commit=False)
                obj.order = (Stage.objects.aggregate(m=Max("order"))["m"] or 0) + 1
                obj.save()
                messages.success(request, f"تمت إضافة «{obj.name}».")
            else:
                _flash_errors(request, form)
        elif action == "add_grade":
            form = GradeForm(request.POST)
            if form.is_valid():
                obj = form.save(commit=False)
                obj.order = (Grade.objects.filter(stage=obj.stage).aggregate(m=Max("order"))["m"] or 0) + 1
                obj.save()
                messages.success(request, f"تمت إضافة «{obj.name}».")
            else:
                _flash_errors(request, form)
        elif action == "add_grades":
            stage = get_object_or_404(Stage, pk=_int(request.POST.get("stage")))
            count = min(max(_int(request.POST.get("count")), 1), len(ORDINALS))
            added = _add_grades(stage, count)
            messages.success(request, f"تمت إضافة {added} صف." if added else "الصفوف موجودة بالفعل.")
        elif action == "add_subject":
            form = SubjectForm(request.POST)
            if form.is_valid():
                obj = form.save(commit=False)
                obj.order = (Subject.objects.filter(grade=obj.grade).aggregate(m=Max("order"))["m"] or 0) + 1
                obj.save()
                messages.success(request, f"تمت إضافة المادة «{obj.name}».")
            else:
                _flash_errors(request, form)
        elif action == "delete_stage":
            stage = get_object_or_404(Stage, pk=_int(request.POST.get("id")))
            try:
                stage.delete()
                messages.success(request, "تم حذف المرحلة.")
            except ProtectedError:
                messages.error(request, "لا يمكن حذف مرحلة بها ملفات. انقل الملفات أو احذفها أولاً.")
        elif action == "delete_grade":
            grade = get_object_or_404(Grade, pk=_int(request.POST.get("id")))
            try:
                grade.delete()
                messages.success(request, "تم حذف الصف.")
            except ProtectedError:
                messages.error(request, "لا يمكن حذف صف به ملفات. انقل الملفات أو احذفها أولاً.")
        elif action == "delete_subject":
            subject = get_object_or_404(Subject, pk=_int(request.POST.get("id")))
            try:
                subject.delete()
                messages.success(request, "تم حذف المادة.")
            except ProtectedError:
                messages.error(request, "لا يمكن حذف مادة بها ملفات. انقل الملفات أو احذفها أولاً.")
        elif action in ("rename_stage", "rename_grade", "rename_subject"):
            name = " ".join((request.POST.get("name") or "").split())[:100]
            pk = _int(request.POST.get("id"))
            if not name:
                messages.error(request, "اكتب الاسم الجديد.")
            elif action == "rename_stage":
                obj = get_object_or_404(Stage, pk=pk)
                if Stage.objects.filter(name=name).exclude(pk=pk).exists():
                    messages.error(request, "يوجد مرحلة بنفس الاسم.")
                else:
                    obj.name = name; obj.save(update_fields=["name"]); messages.success(request, "تم تعديل الاسم.")
            elif action == "rename_grade":
                obj = get_object_or_404(Grade, pk=pk)
                if Grade.objects.filter(stage=obj.stage, name=name).exclude(pk=pk).exists():
                    messages.error(request, "يوجد صف بنفس الاسم في هذه المرحلة.")
                else:
                    obj.name = name; obj.save(update_fields=["name"]); messages.success(request, "تم تعديل الاسم.")
            else:
                obj = get_object_or_404(Subject, pk=pk)
                if Subject.objects.filter(grade=obj.grade, name=name).exclude(pk=pk).exists():
                    messages.error(request, "يوجد مادة بنفس الاسم في هذا الصف.")
                else:
                    obj.name = name; obj.save(update_fields=["name"]); messages.success(request, "تم تعديل الاسم.")
        elif action == "seed" and not Stage.objects.exists():
            for i, (name, count) in enumerate(DEFAULT_STAGES, start=1):
                _add_grades(Stage.objects.create(name=name, order=i), count)
            messages.success(request, "تمت إضافة المراحل والصفوف الافتراضية.")
        return redirect("panel_structure")

    stages = Stage.objects.prefetch_related(
        Prefetch("grades__subjects", queryset=Subject.objects.annotate(n=Count("pages")))
    )
    return render(request, "viewer/panel/structure.html", {"stages": stages})


# ───────────────────────── لوحة الأدمن: الأكواد ─────────────────────────

@staff_only
def panel_codes(request):
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "create":
            form = CodeCreateForm(request.POST)
            if form.is_valid():
                cd = form.cleaned_data
                code = cd["code"] or AccessCode.generate()
                expires = timezone.now() + timedelta(days=cd["days"]) if cd["days"] else None
                AccessCode.objects.create(code=code, label=cd["label"].strip(), expires_at=expires)
                messages.success(request, f"تم إنشاء الكود: {code}")
            else:
                _flash_errors(request, form)
        elif action == "toggle":
            code = get_object_or_404(AccessCode, pk=_int(request.POST.get("id")))
            code.is_active = not code.is_active
            code.save(update_fields=["is_active"])
            messages.success(request, "تم تفعيل الكود." if code.is_active else "تم إيقاف الكود.")
        elif action == "delete":
            get_object_or_404(AccessCode, pk=_int(request.POST.get("id"))).delete()
            messages.success(request, "تم حذف الكود.")
        return redirect("panel_codes")
    return render(request, "viewer/panel/codes.html", {"codes": AccessCode.objects.all()})


# ───────────────────────── لوحة الأدمن: الإعدادات ─────────────────────────

@staff_only
def panel_settings(request):
    form = SettingsForm(request.POST or None, instance=SiteSettings.load())
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "تم حفظ الإعدادات.")
        return redirect("panel_settings")
    return render(request, "viewer/panel/settings.html", {"form": form})
