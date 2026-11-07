"""الهيكل الافتراضي: المرحلة ← الصفوف (المواد بيضيفها الأدمن)."""

ORDINALS = ["الأول", "الثاني", "الثالث", "الرابع", "الخامس", "السادس",
            "السابع", "الثامن", "التاسع", "العاشر", "الحادي عشر", "الثاني عشر"]

# (اسم المرحلة، كلمة بنتعرف بيها على مرحلة موجودة باسم مختلف، عدد الصفوف)
DEFAULT_STAGES = [
    ("المرحلة الابتدائية", "ابتدائ", 6),
    ("المرحلة الإعدادية", "إعداد", 3),
    ("المرحلة الثانوية", "ثانو", 3),
]


def _grade_sort_key(g):
    for idx, o in enumerate(ORDINALS):
        if g.name == f"الصف {o}":
            return (0, idx)
    return (1, g.order, g.id)


def ensure_default_structure(Stage, Grade):
    """بيكمّل الناقص فقط: مبيكررش مرحلة أو صف موجود، ومبيحذفش ولا يغيّر أسماء.
    بياخد الموديلات كمعاملات عشان يشتغل في الـ migration وفي الـ view.
    بيرجّع عدد الصفوف والمراحل اللي اتضافت."""
    added = 0
    default_stage_ids = []
    for position, (name, key, count) in enumerate(DEFAULT_STAGES, start=1):
        stage = Stage.objects.filter(name=name).first() or Stage.objects.filter(name__contains=key).first()
        if stage is None:
            stage = Stage.objects.create(name=name, order=position)
            added += 1
        default_stage_ids.append(stage.pk)

        existing = set(Grade.objects.filter(stage=stage).values_list("name", flat=True))
        for i in range(count):
            gname = f"الصف {ORDINALS[i]}"
            if gname not in existing:
                Grade.objects.create(stage=stage, name=gname, order=100 + i)
                added += 1

        # ترتيب الصفوف: الأول، الثاني ... ثم أي صف مخصص
        grades = sorted(Grade.objects.filter(stage=stage), key=_grade_sort_key)
        for n, g in enumerate(grades, start=1):
            if g.order != n:
                g.order = n
                g.save(update_fields=["order"])

    # ترتيب المراحل: الابتدائية ثم الإعدادية ثم الثانوية، وبعدهم أي مرحلة مضافة
    others = [s for s in Stage.objects.order_by("order", "id") if s.pk not in default_stage_ids]
    ordered = [Stage.objects.get(pk=pk) for pk in default_stage_ids] + others
    for n, s in enumerate(ordered, start=1):
        if s.order != n:
            s.order = n
            s.save(update_fields=["order"])
    return added
