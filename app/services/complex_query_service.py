from typing import Dict, Any, List, Optional, Set
from sqlalchemy import or_, and_, not_
from sqlalchemy.orm import Session, Query
from sqlalchemy.sql import func

from app.models.info_object import InfoObject, Tag
from app.schemas.complex_query import ComplexQuery, ComplexQueryGroup, ComplexQueryCondition


class ComplexQueryService:
    """Построитель SQLAlchemy запросов из структуры сложного запроса"""

    def __init__(self, db: Session):
        self.db = db

    def _build_condition(self, condition: ComplexQueryCondition) -> Any:
        """Построение одного условия"""
        field = condition.field
        operator = condition.operator
        value = condition.value.lower().strip()

        if not value:
            return None

        # Поле может быть в InfoObject или меткой
        if field == "tag":
            # Для меток используем exists подзапрос
            tag_subquery = (
                self.db.query(Tag)
                .join(InfoObject.tags)
                .filter(Tag.name.ilike(f"%{value}%"))
                .filter(InfoObject.id == InfoObject.id)
                .exists()
            )
            condition_expr = tag_subquery
        else:
            # Обычное поле InfoObject
            column = getattr(InfoObject, field, None)
            if column is None:
                return None

            if operator == "contains":
                condition_expr = column.ilike(f"%{value}%")
            elif operator == "equals":
                condition_expr = column.ilike(value)
            elif operator == "starts_with":
                condition_expr = column.ilike(f"{value}%")
            else:
                condition_expr = column.ilike(f"%{value}%")

        # Применяем НЕ если нужно
        if condition.negated:
            return not_(condition_expr)

        return condition_expr

    def _build_group(self, group: ComplexQueryGroup) -> Any:
        """Рекурсивное построение группы условий"""
        conditions = []

        # Обрабатываем прямые условия
        for cond in group.conditions:
            expr = self._build_condition(cond)
            if expr is not None:
                conditions.append(expr)

        # Обрабатываем вложенные группы
        for sub_group in group.groups:
            sub_expr = self._build_group(sub_group)
            if sub_expr is not None:
                conditions.append(sub_expr)

        if not conditions:
            return None

        # Применяем оператор группы
        if group.operator == "AND":
            return and_(*conditions)
        else:  # OR
            return or_(*conditions)

    def build_query(self, query: Query, complex_query: ComplexQuery) -> Query:
        """Применяет сложный запрос к существующему Query"""
        if not complex_query or not complex_query.root:
            return query

        expr = self._build_group(complex_query.root)
        if expr is not None:
            return query.filter(expr)

        return query