import argparse
import logging
import os
import sys
import time
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field

CURRENT_DIR = os.path.dirname(__file__)
BACKEND_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", "..", ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from fastapi import HTTPException
from sqlalchemy import event, text
from sqlalchemy.orm import Session, joinedload

from core.logging_config import setup_logging
from src.routes.categories import models
from src.models.attribute import Attribute
from src.models.category import Category
from src.models.category_attribute import CategoryAttribute
from src.models.db import db_manager

setup_logging()
logger = logging.getLogger("src.routes.categories.benchmark")


def summarize_attributes(attributes: list[dict], values_preview_limit: int = 5) -> list[dict]:
    return [
        {
            "id": attr["id"],
            "name": attr["name"],
            "value_count": len(attr.get("values", [])),
            "values_preview": [value["value"] for value in attr.get("values", [])[:values_preview_limit]],
        }
        for attr in attributes
    ]


def _count_category_nodes(category: models.CategoryData) -> int:
    return 1 + sum(_count_category_nodes(child) for child in category.children)


def summarize_category_node(category: models.CategoryData, depth: int = 0, max_depth: int = 1) -> dict:
    summary = {
        "id": category.id,
        "slug": category.slug,
        "name": category.name,
        "parent_id": category.parent_id,
        "children_count": len(category.children),
        "filterable_attribute_count": len(category.filterable_attributes),
        "filterable_attributes": summarize_attributes(
            [attr.model_dump() for attr in category.filterable_attributes]
        ),
    }

    if depth < max_depth and category.children:
        summary["children_preview"] = [
            summarize_category_node(child, depth=depth + 1, max_depth=max_depth)
            for child in category.children
        ]

    return summary


def summarize_category_result(categories: list[models.CategoryData]) -> dict:
    return {
        "top_level_count": len(categories),
        "total_nodes": sum(_count_category_nodes(category) for category in categories),
        "top_level_preview": [summarize_category_node(category) for category in categories[:3]],
    }


def log_function_return(name: str, payload) -> None:
    logger.info("%s return -> %s", name, payload)


@dataclass
class BenchmarkStats:
    label: str
    totals: dict[str, float] = field(default_factory=lambda: defaultdict(float))
    calls: dict[str, int] = field(default_factory=lambda: defaultdict(int))

    @contextmanager
    def timed(self, name: str):
        start = time.perf_counter()
        try:
            yield
        finally:
            elapsed = time.perf_counter() - start
            self.totals[name] += elapsed
            self.calls[name] += 1

    def print_summary(self):
        print(f"\n[{self.label}] Per-function timings")
        for name in sorted(self.totals.keys()):
            total_ms = self.totals[name] * 1000
            call_count = self.calls[name]
            avg_ms = total_ms / call_count if call_count else 0
            print(f"  - {name}: total={total_ms:.3f}ms calls={call_count} avg={avg_ms:.3f}ms")


class QueryCounter:
    def __init__(self, session: Session):
        self._engine = session.get_bind()
        self.count = 0

    def _before_cursor_execute(self, conn, cursor, statement, parameters, context, executemany):
        self.count += 1

    def __enter__(self):
        event.listen(self._engine, "before_cursor_execute", self._before_cursor_execute)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        event.remove(self._engine, "before_cursor_execute", self._before_cursor_execute)


def get_category_lineage_ids_old(db: Session, category_id: int, stats: BenchmarkStats) -> list[int]:
    with stats.timed("old.get_category_lineage_ids"):
        current_category = db.query(Category).filter(Category.id == category_id).first()
        if not current_category:
            log_function_return("old.get_category_lineage_ids", {"category_id": category_id, "lineage_ids": []})
            return []

        lineage_ids: list[int] = []
        visited_ids: set[int] = set()

        while current_category and current_category.id not in visited_ids:
            lineage_ids.append(current_category.id)
            visited_ids.add(current_category.id)

            if current_category.parent_id is None:
                break

            current_category = db.query(Category).filter(Category.id == current_category.parent_id).first()

        log_function_return(
            "old.get_category_lineage_ids",
            {"category_id": category_id, "lineage_ids": lineage_ids},
        )
        return lineage_ids


def get_attributes_for_category_old(db: Session, category_id: int, stats: BenchmarkStats) -> list[dict]:
    with stats.timed("old.get_attributes_for_category"):
        lineage_ids = get_category_lineage_ids_old(db, category_id, stats)
        if not lineage_ids:
            log_function_return(
                "old.get_attributes_for_category",
                {"category_id": category_id, "attributes": []},
            )
            return []

        attrs = (
            db.query(Attribute)
            .join(CategoryAttribute, CategoryAttribute.attribute_id == Attribute.id)
            .options(joinedload(Attribute.values))
            .filter(CategoryAttribute.category_id.in_(lineage_ids))
            .all()
        )

        attrs_by_id: dict[int, Attribute] = {}
        for attr in attrs:
            if attr.id not in attrs_by_id:
                attrs_by_id[attr.id] = attr

        result = [
            {
                "id": attr.id,
                "name": attr.name,
                "values": [
                    {"id": value.id, "value": value.value}
                    for value in attr.values
                    if value.category_id is None or value.category_id in lineage_ids
                ],
            }
            for attr in attrs_by_id.values()
        ]

        log_function_return(
            "old.get_attributes_for_category",
            {
                "category_id": category_id,
                "lineage_ids": lineage_ids,
                "attribute_count": len(result),
                "attributes": summarize_attributes(result),
            },
        )
        return result


def build_category_hierarchy_old(
    category: Category,
    db: Session,
    include_attributes: bool,
    stats: BenchmarkStats,
) -> models.CategoryData:
    with stats.timed("old.build_category_hierarchy"):
        children = [
            build_category_hierarchy_old(
                child,
                db=db,
                include_attributes=include_attributes,
                stats=stats,
            )
            for child in category.children
        ]

        filterable_attributes = []
        if include_attributes:
            filterable_attributes = get_attributes_for_category_old(db, category.id, stats)

        result = models.CategoryData(
            id=category.id,
            name=category.name,
            slug=category.slug,
            parent_id=category.parent_id,
            children=children,
            filterable_attributes=filterable_attributes,
        )

        log_function_return(
            "old.build_category_hierarchy",
            summarize_category_node(result),
        )
        return result


def get_categories_old(
    db: Session,
    slug: str | None,
    skip: int,
    limit: int,
    stats: BenchmarkStats,
) -> list[models.CategoryData]:
    with stats.timed("old.get_categories"):
        if slug:
            category = db.query(Category).filter(Category.slug == slug).first()
            if not category:
                raise HTTPException(status_code=404, detail="Category not found")

            tree = build_category_hierarchy_old(
                category,
                db=db,
                include_attributes=True,
                stats=stats,
            )
            result = tree.children
            log_function_return("old.get_categories", summarize_category_result(result))
            return result

        parents = (
            db.query(Category)
            .filter(Category.parent_id.is_(None))
            .offset(skip)
            .limit(limit)
            .all()
        )
        result = [
            build_category_hierarchy_old(
                category,
                db=db,
                include_attributes=True,
                stats=stats,
            )
            for category in parents
        ]
        log_function_return("old.get_categories", summarize_category_result(result))
        return result


def fetch_subtree_category_rows(
    db: Session,
    root_ids: list[int],
    stats: BenchmarkStats,
) -> list[dict]:
    with stats.timed("new.fetch_subtree_categories"):
        if not root_ids:
            return []

        query = text(
            """
            WITH RECURSIVE category_tree AS (
                SELECT id, name, slug, parent_id
                FROM categories
                WHERE id = ANY(:root_ids)
                UNION ALL
                SELECT child.id, child.name, child.slug, child.parent_id
                FROM categories child
                JOIN category_tree parent ON child.parent_id = parent.id
            )
            SELECT id, name, slug, parent_id
            FROM category_tree
            """
        )
        rows = db.execute(query, {"root_ids": root_ids}).mappings().all()
        result = [dict(row) for row in rows]
        log_function_return(
            "new.fetch_subtree_categories",
            {
                "root_ids": root_ids,
                "row_count": len(result),
                "rows_preview": result[:10],
            },
        )
        return result


def build_lineage_map_from_rows(categories_by_id: dict[int, dict], stats: BenchmarkStats) -> dict[int, list[int]]:
    with stats.timed("new.build_lineage_map"):
        lineage_by_category: dict[int, list[int]] = {}

        for category_id in categories_by_id.keys():
            lineage: list[int] = []
            visited: set[int] = set()
            current_id = category_id

            while current_id is not None and current_id not in visited:
                lineage.append(current_id)
                visited.add(current_id)
                parent_id = categories_by_id[current_id]["parent_id"]
                current_id = parent_id if parent_id in categories_by_id else None

            lineage_by_category[category_id] = lineage

        log_function_return(
            "new.build_lineage_map",
            {
                "category_count": len(lineage_by_category),
                "lineage_preview": {k: lineage_by_category[k] for k in list(lineage_by_category.keys())[:10]},
            },
        )
        return lineage_by_category


def build_filterable_attributes_for_categories_new(
    db: Session,
    categories_by_id: dict[int, dict],
    stats: BenchmarkStats,
) -> dict[int, list[dict]]:
    with stats.timed("new.build_filterable_attributes"):
        category_ids = list(categories_by_id.keys())
        if not category_ids:
            log_function_return("new.build_filterable_attributes", {"categories": {}})
            return {}

        category_attribute_rows = (
            db.query(CategoryAttribute)
            .filter(CategoryAttribute.category_id.in_(category_ids))
            .all()
        )

        direct_attr_ids_by_category: dict[int, set[int]] = defaultdict(set)
        for row in category_attribute_rows:
            direct_attr_ids_by_category[row.category_id].add(row.attribute_id)

        lineage_by_category = build_lineage_map_from_rows(categories_by_id, stats)

        inherited_attr_ids_by_category: dict[int, set[int]] = {}
        all_attribute_ids: set[int] = set()

        for category_id, lineage in lineage_by_category.items():
            attribute_ids: set[int] = set()
            for ancestor_id in lineage:
                attribute_ids.update(direct_attr_ids_by_category.get(ancestor_id, set()))
            inherited_attr_ids_by_category[category_id] = attribute_ids
            all_attribute_ids.update(attribute_ids)

        if not all_attribute_ids:
            result = {category_id: [] for category_id in category_ids}
            log_function_return(
                "new.build_filterable_attributes",
                {
                    "category_count": len(result),
                    "attribute_count": 0,
                    "categories_preview": {category_id: [] for category_id in list(result.keys())[:10]},
                },
            )
            return result

        attributes = (
            db.query(Attribute)
            .options(joinedload(Attribute.values))
            .filter(Attribute.id.in_(all_attribute_ids))
            .all()
        )
        attributes_by_id = {attr.id: attr for attr in attributes}

        result: dict[int, list[dict]] = {}

        for category_id, attribute_ids in inherited_attr_ids_by_category.items():
            lineage_set = set(lineage_by_category[category_id])
            category_attributes: list[dict] = []

            for attribute_id in sorted(attribute_ids):
                attr = attributes_by_id.get(attribute_id)
                if not attr:
                    continue

                values: list[dict] = []
                seen_value_ids: set[int] = set()

                for value in attr.values:
                    if value.id in seen_value_ids:
                        continue
                    if value.category_id is None or value.category_id in lineage_set:
                        values.append({"id": value.id, "value": value.value})
                        seen_value_ids.add(value.id)

                category_attributes.append(
                    {
                        "id": attr.id,
                        "name": attr.name,
                        "values": values,
                    }
                )

            result[category_id] = category_attributes

        log_function_return(
            "new.build_filterable_attributes",
            {
                "category_count": len(result),
                "attribute_count": len(all_attribute_ids),
                "categories_preview": {
                    category_id: summarize_attributes(attributes)
                    for category_id, attributes in list(result.items())[:10]
                },
            },
        )
        return result


def build_category_hierarchy_new(
    category_id: int,
    categories_by_id: dict[int, dict],
    children_by_parent: dict[int | None, list[int]],
    attrs_by_category_id: dict[int, list[dict]],
    stats: BenchmarkStats,
) -> models.CategoryData:
    with stats.timed("new.build_category_hierarchy"):
        category = categories_by_id[category_id]
        children = [
            build_category_hierarchy_new(
                child_id,
                categories_by_id=categories_by_id,
                children_by_parent=children_by_parent,
                attrs_by_category_id=attrs_by_category_id,
                stats=stats,
            )
            for child_id in children_by_parent.get(category_id, [])
        ]

        result = models.CategoryData(
            id=category["id"],
            name=category["name"],
            slug=category["slug"],
            parent_id=category["parent_id"],
            children=children,
            filterable_attributes=attrs_by_category_id.get(category_id, []),
        )

        log_function_return(
            "new.build_category_hierarchy",
            summarize_category_node(result),
        )
        return result


def get_categories_new_batched(
    db: Session,
    slug: str | None,
    skip: int,
    limit: int,
    stats: BenchmarkStats,
) -> list[models.CategoryData]:
    with stats.timed("new.get_categories"):
        if slug:
            root = db.query(Category).filter(Category.slug == slug).first()
            if not root:
                raise HTTPException(status_code=404, detail="Category not found")
            root_ids = [root.id]
        else:
            roots = (
                db.query(Category)
                .filter(Category.parent_id.is_(None))
                .offset(skip)
                .limit(limit)
                .all()
            )
            root_ids = [category.id for category in roots]

        subtree_rows = fetch_subtree_category_rows(db, root_ids, stats)
        categories_by_id = {row["id"]: row for row in subtree_rows}

        children_by_parent: dict[int | None, list[int]] = defaultdict(list)
        for row in subtree_rows:
            children_by_parent[row["parent_id"]].append(row["id"])

        attrs_by_category_id = build_filterable_attributes_for_categories_new(
            db=db,
            categories_by_id=categories_by_id,
            stats=stats,
        )

        result = [
            build_category_hierarchy_new(
                category_id=root_id,
                categories_by_id=categories_by_id,
                children_by_parent=children_by_parent,
                attrs_by_category_id=attrs_by_category_id,
                stats=stats,
            )
            for root_id in root_ids
        ]

        if slug:
            slug_result = result[0].children if result else []
            log_function_return("new.get_categories", summarize_category_result(slug_result))
            return slug_result

        log_function_return("new.get_categories", summarize_category_result(result))
        return result


def count_nodes(categories: list[models.CategoryData]) -> int:
    total = 0
    for category in categories:
        total += 1
        total += count_nodes(category.children)
    return total


def run_test_case(
    name: str,
    fn,
    db: Session,
    slug: str | None,
    skip: int,
    limit: int,
):
    stats = BenchmarkStats(label=name)

    with QueryCounter(db) as query_counter:
        start = time.perf_counter()
        result = fn(db=db, slug=slug, skip=skip, limit=limit, stats=stats)
        elapsed = time.perf_counter() - start

    print(f"\n=== {name} ===")
    print(f"Total time: {elapsed * 1000:.3f}ms")
    print(f"SQL queries: {query_counter.count}")
    print(f"Category nodes in response: {count_nodes(result)}")
    stats.print_summary()

    logger.info(
        "%s metrics -> total_ms=%.3f query_count=%s category_nodes=%s",
        name,
        elapsed * 1000,
        query_counter.count,
        count_nodes(result),
    )

    return {
        "total_seconds": elapsed,
        "query_count": query_counter.count,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Benchmark old recursive category chain vs new batched chain"
    )
    parser.add_argument("--slug", type=str, default="fashion")
    parser.add_argument("--skip", type=int, default=0)
    parser.add_argument("--limit", type=int, default=100)
    return parser.parse_args()


def main():
    args = parse_args()
    logger.info("Benchmark run started with slug=%s skip=%s limit=%s", args.slug, args.skip, args.limit)

    session_factory = db_manager.session_factory
    db = session_factory()

    try:
        old_metrics = run_test_case(
            name="OLD_CHAIN",
            fn=get_categories_old,
            db=db,
            slug=args.slug,
            skip=args.skip,
            limit=args.limit,
        )

        new_metrics = run_test_case(
            name="NEW_BATCHED_CHAIN",
            fn=get_categories_new_batched,
            db=db,
            slug=args.slug,
            skip=args.skip,
            limit=args.limit,
        )

        print("\n=== COMPARISON ===")
        print(
            "Total time delta (old - new): "
            f"{(old_metrics['total_seconds'] - new_metrics['total_seconds']) * 1000:.3f}ms"
        )
        print(
            "SQL query delta (old - new): "
            f"{old_metrics['query_count'] - new_metrics['query_count']}"
        )
        logger.info(
            "Benchmark comparison -> time_delta_ms=%.3f query_delta=%s",
            (old_metrics["total_seconds"] - new_metrics["total_seconds"]) * 1000,
            old_metrics["query_count"] - new_metrics["query_count"],
        )

    finally:
        db.close()
        logger.info("Benchmark run finished")


if __name__ == "__main__":
    main()
