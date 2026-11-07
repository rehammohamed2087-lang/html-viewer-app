from .access import get_session_code
from .models import SiteSettings


def site(request):
    code = get_session_code(request)
    return {
        "site": SiteSettings.load(),
        "has_code": code is not None,
        "unlocked": request.user.is_staff or code is not None,
    }
