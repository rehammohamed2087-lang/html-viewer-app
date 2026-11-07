"""منطق الصلاحيات: مين يقدر يفتح أنهي ملف."""
from .models import AccessCode


def get_session_code(request):
    """بيرجّع كود الدخول الصالح المخزّن في جلسة الزائر (أو None). بيتحقق في كل طلب عشان الإيقاف يسري فوراً."""
    if hasattr(request, "_session_code"):
        return request._session_code
    code = None
    code_id = request.session.get("code_id")
    if code_id:
        candidate = AccessCode.objects.filter(pk=code_id).first()
        if candidate and candidate.is_valid():
            code = candidate
    request._session_code = code
    return code


def is_unlocked(request):
    return request.user.is_staff or get_session_code(request) is not None


def has_access(request, page):
    return page.is_free or is_unlocked(request)
