import re
from typing import Optional, TYPE_CHECKING
from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from src.models.category import Category

COMMON_WORDS = {'s', 'and', 'or', 'the', 'a', 'an', 'of', 'for', 'in', 'on', 'at', 'to'}


def _extract_initials(name: str) -> str:
    words = re.split(r"[\s\-']+", name)
    result = ''
    for word in words:
        alpha_only = re.sub(r"[^a-zA-Z]", '', word)
        if not alpha_only:
            continue
        if alpha_only.lower() in COMMON_WORDS:
            continue
        if len(alpha_only) >= 3 and alpha_only == alpha_only.upper() and alpha_only.isalpha():
            result += alpha_only[:2]
        else:
            result += alpha_only[0].upper()
    return result or name[0].upper()


def _get_sku_parts(category: Optional["Category"]) -> tuple[str, str]:
    if not category:
        return "P", ""

    if category.parent:
        base_prefix = _extract_initials(category.parent.name)
        parent_alpha_words = set(
            re.sub(r"[^a-zA-Z]", '', w).lower()
            for w in re.split(r"[\s\-']+", category.parent.name)
        )
        child_words = re.split(r"[\s\-']+", category.name)
        unique_words = [
            w for w in child_words
            if re.sub(r"[^a-zA-Z]", '', w).lower() not in parent_alpha_words
            and re.sub(r"[^a-zA-Z]", '', w)
        ]
        modifier = _extract_initials(' '.join(unique_words)) if unique_words else ""
        return base_prefix, modifier

    return _extract_initials(category.name), ""


def generate_sku(db: Session, category: Optional["Category"]) -> str:
    from src.models.product import Product

    base_prefix, modifier = _get_sku_parts(category)

    existing_skus = db.query(Product.sku).filter(
        Product.sku.ilike(f"{base_prefix}%")
    ).all()

    max_num = 0
    pattern = re.compile(rf"^{re.escape(base_prefix)}(\d+)", re.IGNORECASE)
    for (sku,) in existing_skus:
        if sku:
            m = pattern.match(sku)
            if m:
                max_num = max(max_num, int(m.group(1)))

    next_num = max_num + 1
    return f"{base_prefix}{next_num:04d}{modifier}-001"
